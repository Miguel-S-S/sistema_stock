from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# Mantenemos Categoría casi igual, es muy útil para separar 
# cosas de "Librería" (cuadernos) de "Mercería" (hilos, agujas).
class Categoria(models.Model):
    nombre = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    # Identificación básica
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Producto")
    marca = models.CharField(max_length=50, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    codigo_barras = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Código de Barras / SKU")
    
    # Precios y Stock (Lo más importante para tu negocio)
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio de Venta")
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Costo de Compra")
    costo = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Costo de Compra")
    stock_actual = models.IntegerField(default=0, verbose_name="Stock Disponible")
    
    # Descripción y Multimedia
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True, verbose_name="Imagen del Producto")

    # Relaciones
    # Aquí cumplimos el requisito: Un producto puede ser de librería Y mercería a la vez si fuera necesario
    categorias = models.ManyToManyField(Categoria, related_name="productos")
    
    # Auditoría (Cuándo se creó o modificó el producto)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Opcional: Usuario que creó el producto (si tienes empleados)
    usuario_creador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="productos_creados")

    class Meta:
        ordering = ['nombre'] # Ordenar alfabéticamente
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.nombre} (${self.precio})"
    
    def __str__(self):
        return f"{self.nombre} ({self.marca})" if self.marca else self.nombre
    
class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    # Campos opcionales (blank=True, null=True)
    dni = models.CharField(max_length=20, blank=True, null=True, verbose_name="DNI / CUIT")
    fecha_nacimiento = models.DateField(blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.apellido}, {self.nombre}"
    
class Venta(models.Model):
    # Cliente ya permite nulos (blank=True, null=True), así que soporta anónimo
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # NUEVOS CAMPOS DE PAGO
    monto_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_mercadopago = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_transferencia = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vuelto = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Venta #{self.id} - {self.cliente or 'Consumidor Final'}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT) # No permitir borrar productos si ya se vendieron
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        # Calculamos subtotal automáticamente antes de guardar
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

class Presupuesto(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    # Nuevo campo para descuento (en porcentaje, ej: 10 para 10%)
    descuento = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Descuento (%)")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Presupuesto #{self.id} - {self.cliente}"

class DetallePresupuesto(models.Model):
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)  

class Cuenta(models.Model):
    TIPO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('PASIVO', 'Pasivo'),
        ('PN', 'Patrimonio Neto'),
        ('INGRESO', 'Ingreso (Resultado Positivo)'),
        ('EGRESO', 'Egreso (Resultado Negativo)'),
    ]
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class Asiento(models.Model):
    TIPO_ASIENTO = [
        ('APERTURA', 'Apertura / Saldos Iniciales'),
        ('NORMAL', 'Movimiento Normal'),
        ('REFUNDICION', 'Refundición de Resultados'),
        ('CIERRE', 'Cierre Patrimonial'),
    ]
    fecha = models.DateField()
    descripcion = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_ASIENTO, default='NORMAL')
    creado_at = models.DateTimeField(auto_now_add=True)

    def total_debe(self):
        return sum(item.debe for item in self.items.all())

    def total_haber(self):
        return sum(item.haber for item in self.items.all())

    def esta_balanceado(self):
        return self.total_debe() == self.total_haber()

class ItemAsiento(models.Model):
    asiento = models.ForeignKey(Asiento, related_name='items', on_delete=models.CASCADE)
    cuenta = models.ForeignKey(Cuenta, on_delete=models.PROTECT)
    debe = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    haber = models.DecimalField(max_digits=15, decimal_places=2, default=0)

class CajaDiaria(models.Model):
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_final = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    estado = models.BooleanField(default=True) # True = Abierta, False = Cerrada
    # Opcional: Usuario que abrió la caja
    # usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        estado_str = "ABIERTA" if self.estado else "CERRADA"
        return f"Caja {self.id} - {self.fecha_apertura.strftime('%d/%m/%Y')} ({estado_str})"