from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class EventoAuditoria(models.Model):
    ACCION_CHOICES = [
        ('CREATE', 'Alta'),
        ('UPDATE', 'Modificación'),
        ('DELETE', 'Eliminación'),
        ('LOGIN', 'Inicio de Sesión'),
        ('LOGOUT', 'Cierre de Sesión'),
        ('AJUSTE', 'Ajuste Manual'),
    ]

    # 1. Identificación
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    modulo = models.CharField(max_length=50) # Ej: inventario, sales

    # 2. Acción
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES)

    # 3. Entidad Afectada (Magia de Django para vincular cualquier modelo)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=50) # Char para soportar IDs no numéricos si hubiera
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # 4, 5, 6. Valores Auditados (JSON es perfecto para esto)
    estado_anterior = models.JSONField(null=True, blank=True)
    estado_nuevo = models.JSONField(null=True, blank=True)
    cambios = models.JSONField(null=True, blank=True) # Resumen de qué cambió
    
    # 11. Observaciones
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['content_type', 'object_id']), # Búsqueda rápida por entidad
            models.Index(fields=['usuario']),
            models.Index(fields=['accion']),
        ]

    def __str__(self):
        return f"[{self.fecha.strftime('%d/%m %H:%M')}] {self.usuario} - {self.accion} en {self.content_object}"