from django import forms
from inventario.models import Producto

class AjusteStockForm(forms.Form):
    producto = forms.ModelChoiceField(queryset=Producto.objects.all(), widget=forms.Select(attrs={'class': 'form-select select2'}))
    cantidad_ajuste = forms.IntegerField(label="Cantidad a Ajustar (+/-)", widget=forms.NumberInput(attrs={'class': 'form-control'}))
    motivo = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=True)