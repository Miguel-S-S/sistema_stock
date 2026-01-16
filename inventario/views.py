# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import (Producto, Categoria, Cliente, Venta, DetalleVenta, DetallePresupuesto, 
                        Presupuesto, Cuenta, Asiento, ItemAsiento, CajaDiaria) 
from .forms import (ProductoForm, ClienteForm, VentaForm, 
                    DetalleVentaFormSet, PresupuestoForm, DetallePresupuestoFormSet, AperturaCajaForm, CierreCajaForm)
from django.db import transaction
from decimal import Decimal
from django.db.models import Sum
from datetime import date, timedelta
from django.utils.dateparse import parse_date
from django.utils import timezone
import json

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
    if not CajaDiaria.objects.filter(estado=True).exists():
        messages.error(request, "⚠️ DEBES ABRIR LA CAJA ANTES DE VENDER")
        return redirect('gestion_caja')
    # Crear un diccionario de precios para JS: { 'ID_PRODUCTO': PRECIO, ... }
    # Usamos float() para que sea serializable a JSON
    lista_precios = {p.id: float(p.precio) for p in Producto.objects.all()}
    precios_json = json.dumps(lista_precios)
    if request.method == 'POST':
        form = VentaForm(request.POST)
        formset = DetalleVentaFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic(): # Si algo falla, no se guarda nada (seguridad)
                    venta = form.save(commit=False)
                    # Calcular el vuelto en el backend también por seguridad
                    total_pagado = (venta.monto_efectivo or 0) + (venta.monto_mercadopago or 0) + (venta.monto_transferencia or 0)
                    venta.total = 0 # Se calculará con los detalles
                    venta.save() # Guardamos la cabecera primero para tener ID

                    total_venta = Decimal(0)
                    total_costo = Decimal(0) # acumulador para el asiento del costo
                    detalles = formset.save(commit=False) # guardar los detalles y actualizar stock

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
                        #calcula costo total del item
                        costo_unitario = producto.precio_costo if producto.precio_costo is not None else Decimal(0)
                        total_costo += (costo_unitario * detalle.cantidad)

                    # 4. Actualizar total de la venta
                    venta.total = total_venta
                    venta.vuelto = total_pagado - total_venta # Guardamos el vuelto
                    venta.save()

                    # ==========================================
                    # 3. GENERACIÓN AUTOMÁTICA DE ASIENTOS (NUEVO)
                    # ==========================================
                    
                    # A) Asiento de Venta (Ingreso de Dinero)
                    # ----------------------------------------
                    asiento_venta = Asiento.objects.create(
                        fecha=date.today(),
                        descripcion=f"Venta #{venta.id} - {venta.cliente or 'Consumidor Final'}",
                        tipo='NORMAL'
                    )

                    # DEBE: Caja (Entra dinero)
                    cuenta_caja = Cuenta.objects.get(codigo='1.01') # Asegúrate que este código coincida con el script anterior
                    ItemAsiento.objects.create(
                        asiento=asiento_venta, 
                        cuenta=cuenta_caja, 
                        debe=total_venta, 
                        haber=0
                    )

                    # HABER: Ventas (Resultado Positivo)
                    cuenta_ventas = Cuenta.objects.get(codigo='4.01')
                    ItemAsiento.objects.create(
                        asiento=asiento_venta, 
                        cuenta=cuenta_ventas, 
                        debe=0, 
                        haber=total_venta
                    )

                    # B) Asiento de Costo (Salida de Mercadería)
                    # ----------------------------------------
                    # Si el producto tiene costo cargado, hacemos el asiento
                    if total_costo > 0:
                        asiento_costo = Asiento.objects.create(
                            fecha=date.today(),
                            descripcion=f"Costo por Venta #{venta.id}",
                            tipo='NORMAL'
                        )

                        # DEBE: Costo de Mercadería Vendida (Pérdida/Egreso)
                        cuenta_cmv = Cuenta.objects.get(codigo='5.01')
                        ItemAsiento.objects.create(
                            asiento=asiento_costo,
                            cuenta=cuenta_cmv,
                            debe=total_costo,
                            haber=0
                        )

                        # HABER: Mercaderías (Activo que disminuye)
                        cuenta_mercaderias = Cuenta.objects.get(codigo='1.02')
                        ItemAsiento.objects.create(
                            asiento=asiento_costo,
                            cuenta=cuenta_mercaderias,
                            debe=0,
                            haber=total_costo
                        )

                    messages.success(request, '¡Venta registrada exitosamente!')
                    return redirect('ticket_venta', pk=venta.id) # Redirigir al Ticket
                
            except Cuenta.DoesNotExist:
                    # Error específico si no ejecutaste el script de cuentas
                    messages.error(request, "Error Contable: Faltan configurar las Cuentas (Caja, Ventas, etc). Ejecuta el script de inicialización.")
            except Exception as e:
                    messages.error(request, str(e))
        else:
            messages.error(request, 'Error en el formulario. Verifique los datos.')
    else:
        form = VentaForm()
        formset = DetalleVentaFormSet()

    return render(request, 'sales/nueva_venta.html', {
        'form': form, 
        'formset': formset, 
        'precios_json': precios_json
    })

@login_required
def ticket_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    return render(request, 'sales/ticket.html', {'venta': venta})

@login_required
def venta_list(request):
    #1. obtener los filtros de la url si existen
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    filtro_rapido = request.GET.get('filtro') # 'hoy', 'ayer', 'ultimos_7', 'ultimos_30'
    #2. query base todas las ventas ordenadas por fecha descendente
    ventas = Venta.objects.all().order_by('-fecha')
    #3. aplicar filtros si existen
    hoy = date.today()
    if filtro_rapido == 'hoy':
        ventas = ventas.filter(fecha=hoy)
        fecha_inicio = hoy
        fecha_fin = hoy
    elif filtro_rapido == 'semana':
        inicio_semana = hoy - timedelta(days=7)
        ventas = ventas.filter(fecha__date__range=[inicio_semana, hoy])
        fecha_inicio = inicio_semana
        fecha_fin = hoy
    elif filtro_rapido == 'mes':
        inicio_mes = hoy - timedelta(days=30)
        ventas = ventas.filter(fecha__date__range=[inicio_mes, hoy])
        fecha_inicio = inicio_mes
        fecha_fin = hoy
    elif fecha_inicio and fecha_fin:
        #este es el filtro personalizado de rango de fechas elegidas
        ventas = ventas.filter(fecha__date__range=[fecha_inicio, fecha_fin])
    total_periodo = sum(v.total for v in ventas)

    context = {
        'ventas': ventas,
        'total_periodo': total_periodo, 
        'fecha_inicio': str(fecha_inicio) if fecha_inicio else '',
        'fecha_fin': str(fecha_fin) if fecha_fin else '',
    }
    return render(request, 'sales/venta_list.html', context)
    

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
#GESTION CONTABLE
@login_required
def gestion_caja(request):
    # Buscamos si hay una caja abierta
    caja_abierta = CajaDiaria.objects.filter(estado=True).last()
    
    if caja_abierta:
        # SI ESTÁ ABIERTA: Mostramos opción de cerrar
        return render(request, 'sales/caja_status.html', {'caja': caja_abierta, 'estado': 'abierta'})
    else:
        # SI ESTÁ CERRADA: Mostramos opción de abrir
        return render(request, 'sales/caja_status.html', {'estado': 'cerrada'})

@login_required
def abrir_caja(request):
    # Validar que no haya una ya abierta
    if CajaDiaria.objects.filter(estado=True).exists():
        messages.warning(request, "Ya existe una caja abierta.")
        return redirect('gestion_caja')

    if request.method == 'POST':
        form = AperturaCajaForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                caja = form.save()
                
                # ASIENTO CONTABLE: Saldo Inicial
                # (Entra a Caja, sale de "Aporte" o "Resultados Acumulados" momentáneamente)
                if caja.saldo_inicial > 0:
                    asiento = Asiento.objects.create(
                        fecha=date.today(),
                        descripcion=f"Apertura de Caja #{caja.id}",
                        tipo='APERTURA'
                    )
                    cuenta_caja = Cuenta.objects.get(codigo='1.01')
                    cuenta_capital = Cuenta.objects.get(codigo='3.01') # O la cuenta que uses para ajustar
                    
                    ItemAsiento.objects.create(asiento=asiento, cuenta=cuenta_caja, debe=caja.saldo_inicial, haber=0)
                    ItemAsiento.objects.create(asiento=asiento, cuenta=cuenta_capital, debe=0, haber=caja.saldo_inicial)

            messages.success(request, f"Caja abierta con ${caja.saldo_inicial}")
            return redirect('dashboard')
    else:
        form = AperturaCajaForm()
    
    return render(request, 'sales/caja_apertura.html', {'form': form})

@login_required
def cerrar_caja(request):
    caja = CajaDiaria.objects.filter(estado=True).last()
    if not caja:
        return redirect('gestion_caja')

    # CALCULAR SALDO ESPERADO (Saldo Inicial + Ventas del día - Gastos del día)
    # Por simplicidad, sumamos el Debe de la cuenta Caja desde la hora de apertura
    cuenta_caja = Cuenta.objects.get(codigo='1.01')
    
    # Movimientos desde que se abrió esta caja específica
    movimientos = ItemAsiento.objects.filter(
        cuenta=cuenta_caja,
        asiento__creado_at__gte=caja.fecha_apertura
    ).aggregate(total_debe=Sum('debe'), total_haber=Sum('haber'))
    
    total_ingresos = movimientos['total_debe'] or 0
    total_egresos = movimientos['total_haber'] or 0
    # Nota: El saldo inicial ya se sumó como "total_debe" en el asiento de apertura
    saldo_sistema = total_ingresos - total_egresos

    if request.method == 'POST':
        form = CierreCajaForm(request.POST)
        if form.is_valid():
            monto_real = form.cleaned_data['monto_real']
            diferencia = monto_real - saldo_sistema
            
            caja.saldo_final = monto_real
            caja.fecha_cierre = timezone.now()
            caja.estado = False # Cerramos
            caja.save()
            
            # Opcional: Registrar la diferencia (sobrante o faltante de caja)
            if diferencia != 0:
                messages.warning(request, f"Caja cerrada con una diferencia de ${diferencia}")
            else:
                messages.success(request, "Caja cerrada perfectamente.")
                
            return redirect('dashboard')
    else:
        form = CierreCajaForm()

    return render(request, 'sales/caja_cierre.html', {
        'form': form, 
        'caja': caja,
        'saldo_sistema': saldo_sistema
    })

@login_required
def libro_diario(request):
    asientos = Asiento.objects.all().order_by('-fecha', '-id')
    return render(request, 'accounting/libro_diario.html', {'asientos': asientos})

@login_required
def nuevo_asiento_manual(request):
    # Por simplicidad, aquí renderizaríamos un formset similar a Ventas
    # pero eligiendo Cuenta, Debe y Haber. 
    # (Te paso el template básico abajo, la lógica es igual a ventas)
    pass 

@login_required
def generar_cierre_contable(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                fecha_cierre = date.today()

                # --- PASO 1: REFUNDICIÓN DE RESULTADOS ---
                # Cancelamos Ingresos y Egresos contra "Resultado del Ejercicio"
                
                cuentas_ingreso = Cuenta.objects.filter(tipo='INGRESO')
                cuentas_egreso = Cuenta.objects.filter(tipo='EGRESO')
                
                asiento_refundicion = Asiento.objects.create(
                    fecha=fecha_cierre,
                    descripcion="Refundición de Cuentas de Resultado",
                    tipo='REFUNDICION'
                )

                total_ingresos = 0
                total_egresos = 0

                # Debitamos los ingresos para dejarlos en 0
                for c in cuentas_ingreso:
                    saldo = ItemAsiento.objects.filter(cuenta=c).aggregate(
                        d=Sum('debe'), h=Sum('haber')
                    )
                    saldo_neto = (saldo['h'] or 0) - (saldo['d'] or 0) # Saldo acreedor
                    if saldo_neto > 0:
                        ItemAsiento.objects.create(asiento=asiento_refundicion, cuenta=c, debe=saldo_neto, haber=0)
                        total_ingresos += saldo_neto

                # Acreditamos los egresos para dejarlos en 0
                for c in cuentas_egreso:
                    saldo = ItemAsiento.objects.filter(cuenta=c).aggregate(
                        d=Sum('debe'), h=Sum('haber')
                    )
                    saldo_neto = (saldo['d'] or 0) - (saldo['h'] or 0) # Saldo deudor
                    if saldo_neto > 0:
                        ItemAsiento.objects.create(asiento=asiento_refundicion, cuenta=c, debe=0, haber=saldo_neto)
                        total_egresos += saldo_neto

                # La diferencia va a Resultado del Ejercicio
                resultado = total_ingresos - total_egresos
                cuenta_resultado = Cuenta.objects.get(nombre='Resultado del Ejercicio')
                
                if resultado > 0: # Ganancia (Acreditar PN)
                    ItemAsiento.objects.create(asiento=asiento_refundicion, cuenta=cuenta_resultado, debe=0, haber=resultado)
                else: # Pérdida (Debitar PN)
                    ItemAsiento.objects.create(asiento=asiento_refundicion, cuenta=cuenta_resultado, debe=abs(resultado), haber=0)


                # --- PASO 2: PASAJE A RESULTADOS ACUMULADOS ---
                # Movemos el Resultado del Ejercicio a Resultados Acumulados para iniciar el nuevo periodo limpio
                
                asiento_traslado = Asiento.objects.create(
                    fecha=fecha_cierre,
                    descripcion="Traslado a Resultados Acumulados",
                    tipo='NORMAL'
                )
                
                cuenta_acumulados = Cuenta.objects.get(nombre='Resultados Acumulados')
                
                if resultado > 0:
                    # Debito el ejercicio (para cancelarlo) y Acredito Acumulados
                    ItemAsiento.objects.create(asiento=asiento_traslado, cuenta=cuenta_resultado, debe=resultado, haber=0)
                    ItemAsiento.objects.create(asiento=asiento_traslado, cuenta=cuenta_acumulados, debe=0, haber=resultado)
                else:
                    # Inverso
                    ItemAsiento.objects.create(asiento=asiento_traslado, cuenta=cuenta_resultado, debe=0, haber=abs(resultado))
                    ItemAsiento.objects.create(asiento=asiento_traslado, cuenta=cuenta_acumulados, debe=abs(resultado), haber=0)

                messages.success(request, '¡Cierre de ejercicio y refundición generados correctamente!')
        
        except Exception as e:
            messages.error(request, f"Error en el cierre: {str(e)}")
            
    return redirect('libro_diario')

