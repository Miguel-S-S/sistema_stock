from django.db import models # <--- ### NUEVO: Importar models base
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields.files import FieldFile 

# Importamos modelos que queremos auditar
from inventario.models import Producto, Venta, Compra, Asiento, CajaDiaria, Proveedor, Cliente
from .models import EventoAuditoria
from .middleware import get_current_user, get_current_ip
import json
from decimal import Decimal
from datetime import date, datetime

# Modelos a auditar
MODELOS_AUDITADOS = [Producto, Venta, Compra, Asiento, CajaDiaria, Proveedor, Cliente]

# Helper para serializar CUALQUIER COSA a JSON
class AuditEncoder(json.JSONEncoder):
    def default(self, obj):
        # 1. Decimales (dinero)
        if isinstance(obj, Decimal):
            return float(obj)
        # 2. Fechas
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        # 3. Imágenes/Archivos
        if isinstance(obj, FieldFile):
            return obj.name if obj else None
        # 4. ### NUEVO: Modelos relacionados (Categoria, Marca, etc)
        if isinstance(obj, models.Model):
            return str(obj) # Devuelve el nombre (ej: "Bebidas") en lugar del objeto error
        # ---------------------------------------------------------
        return super().default(obj)

@receiver(pre_save)
def auditar_pre_save(sender, instance, **kwargs):
    if sender in MODELOS_AUDITADOS and instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_state = model_to_dict(old_instance)
        except sender.DoesNotExist:
            instance._old_state = {}
    else:
        instance._old_state = {}

@receiver(post_save)
def auditar_post_save(sender, instance, created, **kwargs):
    if sender not in MODELOS_AUDITADOS:
        return

    usuario = get_current_user()
    ip = get_current_ip()
    new_state = model_to_dict(instance)
    
    accion = 'CREATE' if created else 'UPDATE'
    cambios = {}

    if not created and hasattr(instance, '_old_state'):
        for key, value in new_state.items():
            old_value = instance._old_state.get(key)
            
            # Comparación robusta (maneja archivos y modelos)
            val_comp = value.name if isinstance(value, FieldFile) else str(value) if isinstance(value, models.Model) else value
            old_comp = old_value.name if isinstance(old_value, FieldFile) else str(old_value) if isinstance(old_value, models.Model) else old_value

            if val_comp != old_comp:
                cambios[key] = {'antes': old_value, 'despues': value}
        
        if not cambios:
            return
            
    # Usamos el encoder superpoderoso
    old_json = json.loads(json.dumps(instance._old_state, cls=AuditEncoder)) if not created else None
    new_json = json.loads(json.dumps(new_state, cls=AuditEncoder))
    cambios_json = json.loads(json.dumps(cambios, cls=AuditEncoder)) if cambios else None

    EventoAuditoria.objects.create(
        usuario=usuario,
        ip_origen=ip,
        modulo=sender._meta.app_label,
        accion=accion,
        content_type=ContentType.objects.get_for_model(instance),
        object_id=str(instance.pk),
        estado_anterior=old_json,
        estado_nuevo=new_json,
        cambios=cambios_json,
        observacion=f"Movimiento automático en {sender.__name__}"
    )

@receiver(post_delete)
def auditar_delete(sender, instance, **kwargs):
    if sender not in MODELOS_AUDITADOS:
        return

    usuario = get_current_user()
    ip = get_current_ip()
    old_state = model_to_dict(instance)
    
    old_json = json.loads(json.dumps(old_state, cls=AuditEncoder))

    EventoAuditoria.objects.create(
        usuario=usuario,
        ip_origen=ip,
        modulo=sender._meta.app_label,
        accion='DELETE',
        content_type=ContentType.objects.get_for_model(instance),
        object_id=str(instance.pk),
        estado_anterior=old_json,
        observacion=f"Registro eliminado: {str(instance)}"
    )