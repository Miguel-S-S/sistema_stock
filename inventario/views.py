# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Producto, Categoria, Cliente, Venta, DetalleVenta, DetallePresupuesto, Presupuesto # Asumiendo que tienes estos modelos
from .forms import ProductoForm, ClienteForm, VentaForm, DetalleVentaFormSet, PresupuestoForm, DetallePresupuestoFormSet
from django.db import transaction
from decimal import Decimal

# 1. EL MENÚ PRINCIPAL (GRIDS)
@login_required
def dashboard(request):
    # Esta vista solo renderiza los botones, no necesita cargar productos pesados
    return render(request, 'dashboard.html')

# 2. LA LISTA DE PRODUCTOS (Lo que antes tenías en dashboard)
@login_required
def producto_list(request):
    productos = Producto.objects.prefetch_related('categorias').all()
    context = {'productos': productos}
    # OJO: Aquí usamos un template nuevo específico para la lista
    return render(request, 'inventario/producto_list.html', context)

@login_required
def producto_crear(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Producto guardado exitosamente!')
            return redirect('producto_list')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = ProductoForm()
    return render(request, 'inventario/producto_form.html', {'form': form, 'titulo': 'Nuevo Producto'})

@login_required
def producto_editar(request, pk):
    # Buscamos el producto por su ID (pk). Si no existe, da error 404
    producto = get_object_or_404(Producto, pk=pk)

    if request.method == 'POST':
        # Pasamos 'instance=producto' para que Django sepa que estamos ACTUALIZANDO, no creando
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Producto actualizado correctamente!')
            return redirect('producto_list')
    else:
        # Pre-llenamos el formulario con los datos actuales
        form = ProductoForm(instance=producto)

    return render(request, 'inventario/producto_form.html', {
        'form': form, 
        'titulo': f'Editar {producto.nombre}' 
    })

@login_required
def cliente_lista(request):
    clientes = Cliente.objects.all()
    return render(request, 'partners/cliente_list.html', {'clientes': clientes})

@login_required
def cliente_crear(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Cliente registrado correctamente!')
            return redirect('cliente_lista')
    else:
        form = ClienteForm()
    
    return render(request, 'partners/cliente_form.html', {'form': form, 'titulo': 'Nuevo Cliente'})

@login_required
def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Cliente actualizado correctamente!')
            return redirect('cliente_lista')
    else:
        form = ClienteForm(instance=cliente)
    
    return render(request, 'partners/cliente_form.html', {'form': form, 'titulo': f'Editar {cliente.nombre}'})

@login_required
def nueva_venta(request):
    if request.method == 'POST':
        form = VentaForm(request.POST)
        formset = DetalleVentaFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic(): # Si algo falla, no se guarda nada (seguridad)
                    venta = form.save(commit=False)
                    venta.total = 0 # Se calculará con los detalles
                    venta.save() # Guardamos la cabecera primero para tener ID

                    total_venta = 0
                    detalles = formset.save(commit=False)

                    for detalle in detalles:
                        producto = detalle.producto
                        
                        # 1. Validar Stock
                        if producto.stock_actual < detalle.cantidad:
                            raise Exception(f"No hay suficiente stock de {producto.nombre}")

                        # 2. Restar Stock
                        producto.stock_actual -= detalle.cantidad
                        producto.save()

                        # 3. Guardar precio histórico y subtotal
                        detalle.venta = venta
                        detalle.precio_unitario = producto.precio # Precio al momento de la venta
                        detalle.subtotal = detalle.cantidad * detalle.precio_unitario
                        detalle.save()

                        total_venta += detalle.subtotal

                    # 4. Actualizar total de la venta
                    venta.total = total_venta
                    venta.save()

                    messages.success(request, '¡Venta registrada exitosamente!')
                    return redirect('ticket_venta', pk=venta.id) # Redirigir al Ticket

            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Error en el formulario. Verifique los datos.')
    else:
        form = VentaForm()
        formset = DetalleVentaFormSet()

    return render(request, 'sales/nueva_venta.html', {
        'form': form, 
        'formset': formset
    })

@login_required
def ticket_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    return render(request, 'sales/ticket.html', {'venta': venta})

@login_required
def nuevo_presupuesto(request):
    if request.method == 'POST':
        form = PresupuestoForm(request.POST)
        formset = DetallePresupuestoFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    presupuesto = form.save(commit=False)
                    presupuesto.total = 0 
                    presupuesto.save()

                    subtotal_acumulado = Decimal(0) # Inicializamos como Decimal
                    detalles = formset.save(commit=False)

                    for detalle in detalles:
                        producto = detalle.producto
                        detalle.presupuesto = presupuesto
                        
                        # CORRECCIÓN 1: No usamos float(). Multiplicamos directo.
                        # (Entero * Decimal = Decimal, así que funciona perfecto)
                        detalle.precio_unitario = producto.precio 
                        detalle.subtotal = detalle.cantidad * producto.precio
                        
                        detalle.save()
                        subtotal_acumulado += detalle.subtotal

                    # CORRECCIÓN 2: Cálculo del descuento usando Decimal
                    # Convertimos el 100 a Decimal para que la división sea segura
                    descuento = presupuesto.descuento # Ya viene como Decimal desde el modelo
                    monto_descuento = subtotal_acumulado * (descuento / Decimal(100))
                    
                    presupuesto.total = subtotal_acumulado - monto_descuento
                    presupuesto.save()

                    messages.success(request, '¡Presupuesto generado exitosamente!')
                    return redirect('ver_presupuesto', pk=presupuesto.id)

            except Exception as e:
                messages.error(request, str(e))
    else:
        form = PresupuestoForm()
        formset = DetallePresupuestoFormSet()

    return render(request, 'sales/presupuesto_form.html', {
        'form': form, 
        'formset': formset
})

@login_required
def ver_presupuesto(request, pk):
    presupuesto = get_object_or_404(Presupuesto, pk=pk)
    # Apuntamos al nuevo template de detalle
    return render(request, 'sales/presupuesto_detail.html', {'presupuesto': presupuesto})

@login_required
def presupuesto_list(request):
    # Traemos todos, ordenados por fecha descendente (lo último primero)
    presupuestos = Presupuesto.objects.all().order_by('-fecha')
    return render(request, 'sales/presupuesto_list.html', {'presupuestos': presupuestos})