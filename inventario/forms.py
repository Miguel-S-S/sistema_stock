from django import forms
# IMPORTANTE: Esta línea arregla el primer error
from django.forms import inlineformset_factory 
# IMPORTANTE: Asegúrate de importar Venta y DetalleVenta aquí
from .models import Producto, Cliente, Venta, DetalleVenta

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
            #configuracion para el escaner de codigo de barras
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
        fields = ['cliente']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'cliente': 'Cliente (Dejar vacío para Consumidor Final)'
        }

# Primero definir este formulario...
class DetalleVentaForm(forms.ModelForm):
    class Meta:
        model = DetalleVenta
        fields = ['producto', 'cantidad']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '1'}),
        }

# ...y LUEGO creamos la fábrica (FormSet) que lo utiliza.
# Si pones esto arriba de la clase DetalleVentaForm, Python dará error.
DetalleVentaFormSet = inlineformset_factory(
    Venta, 
    DetalleVenta, 
    form=DetalleVentaForm,
    extra=1,
    can_delete=True
)