from django import forms

from django.forms import inlineformset_factory 

from .models import Producto, Cliente, Venta, DetalleVenta, Presupuesto, DetallePresupuesto, CajaDiaria, Proveedor, Compra, DetalleCompra

# --- PRODUCTOS ---
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo_barras',
            'nombre', 
            'marca', 
            'categorias', 
            'precio_costo', 
            'precio', 
            'stock_actual', 
            'descripcion'
        ]
        widgets = {
            'codigo_barras': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Escanear código de barras', 'autofocus': 'autofocus'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Resma A4'}),
            'marca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Ledesma, Bic...'}),
            'categorias': forms.SelectMultiple(attrs={'class': 'form-select', 'style': 'height: 100px;'}),
            'precio_costo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'codigo_barras': 'Código de Barras / SKU',
            'precio': 'Precio de Venta (Público)',
            'precio_costo': 'Precio de Costo (Proveedor)',
            'categorias': 'Categorías (Ctrl + Click para varias)'
        }

# --- CLIENTES ---
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'apellido', 'dni', 'fecha_nacimiento', 'email', 'telefono', 'direccion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'dni': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
        }

# --- VENTAS ---

class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['cliente', 'monto_efectivo', 'monto_mercadopago', 'monto_transferencia']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'monto_efectivo': forms.NumberInput(attrs={'class': 'form-control payment-input', 'value': 0}),
            'monto_mercadopago': forms.NumberInput(attrs={'class': 'form-control payment-input', 'value': 0}),
            'monto_transferencia': forms.NumberInput(attrs={'class': 'form-control payment-input', 'value': 0}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].required = False # Asegura que sea opcional
        self.fields['cliente'].label = "Cliente (Dejar vacío para Consumidor Final)"

# Primero definir este formulario...
class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = DetalleVenta
        fields = ['producto', 'cantidad']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '1'}),
        }

DetalleVentaFormSet = inlineformset_factory(
    Venta, 
    DetalleVenta, 
    form=DetalleVentaForm,
    extra=1,
    can_delete=True
)

class PresupuestoForm(forms.ModelForm):
    class Meta:
        model = Presupuesto
        fields = ['cliente', 'descuento']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'descuento': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
        }
        labels = {
            'cliente': 'Cliente (Opcional)',
            'descuento': 'Descuento Global (%)'
        }

class DetallePresupuestoForm(forms.ModelForm):
    class Meta:
        model = DetallePresupuesto
        fields = ['producto', 'cantidad']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '1'}),
        }

DetallePresupuestoFormSet = inlineformset_factory(
    Presupuesto, 
    DetallePresupuesto, 
    form=DetallePresupuestoForm,
    extra=1,
    can_delete=True
)

class AperturaCajaForm(forms.ModelForm):
    class Meta:
        model = CajaDiaria
        fields = ['saldo_inicial']
        widgets = {
            'saldo_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Monto de cambio inicial'}),
        }
        labels = {'saldo_inicial': 'Saldo Inicial (Cambio en Caja)'}

class CierreCajaForm(forms.ModelForm):
    # Campo extra para que el usuario diga cuánto dinero contó físicamente
    monto_real = forms.DecimalField(
        max_digits=12, decimal_places=2, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label="Dinero contado en Caja (Real)"
    )
    class Meta:
        model = CajaDiaria
        fields = [] # No editamos campos del modelo directamente aquí

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['razon_social', 'cuit', 'condicion_iva', 'telefono', 'email', 'direccion']
        widgets = {
            'razon_social': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Distribuidora Norte S.A.'}),
            'cuit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 20-12345678-9'}),
            'condicion_iva': forms.Select(attrs={'class': 'form-select'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['proveedor', 'comprobante', 'observaciones']
        widgets = {
            'proveedor': forms.Select(attrs={'class': 'form-select'}),
            'comprobante': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: A-0001-12345678'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class DetalleCompraForm(forms.ModelForm):
    class Meta:
        model = DetalleCompra
        fields = ['producto', 'cantidad', 'precio_costo']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'precio_costo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

DetalleCompraFormSet = inlineformset_factory(
    Compra,
    DetalleCompra,
    form=DetalleCompraForm,
    extra=1,
    can_delete=True
)