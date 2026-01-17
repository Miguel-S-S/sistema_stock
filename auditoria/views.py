from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from .forms import AjusteStockForm
from .models import EventoAuditoria
from inventario.models import Producto

@login_required
def ajuste_stock(request):
    if request.method == 'POST':
        form = AjusteStockForm(request.POST)
        if form.is_valid():
            producto = form.cleaned_data['producto']
            cantidad = form.cleaned_data['cantidad_ajuste']
            motivo = form.cleaned_data['motivo']

            # Guardamos estado anterior para la auditoría manual
            estado_anterior = {'stock_actual': float(producto.stock_actual)}
            
            # --- REGLA DE ORO: EL STOCK SE MUEVE ---
            producto.stock_actual += cantidad
            producto.save()
            
            estado_nuevo = {'stock_actual': float(producto.stock_actual)}

            # Creamos el evento de auditoría específico (AJUSTE)
            EventoAuditoria.objects.create(
                usuario=request.user,
                # ip_origen se obtendrá si usamos el middleware, o lo pasamos aquí si es crítico
                modulo='inventario',
                accion='AJUSTE',
                content_type=ContentType.objects.get_for_model(producto),
                object_id=str(producto.pk),
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                cambios={'stock': {'delta': cantidad, 'motivo': motivo}},
                observacion=f"AJUSTE MANUAL: {motivo}"
            )

            messages.success(request, f"Stock ajustado. Nuevo saldo: {producto.stock_actual}")
            return redirect('auditoria_panel') 
    else:
        form = AjusteStockForm()

    # --- LISTA DE AUDITORÍA (CONSULTA Y REPORTES) ---
    eventos = EventoAuditoria.objects.all()[:50] # Últimos 50 eventos
    
    return render(request, 'auditoria/panel_control.html', {'form': form, 'eventos': eventos})