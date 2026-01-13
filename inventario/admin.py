from django.contrib import admin
from .models import Categoria, Producto

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # Esto define las columnas que verás en la lista de productos
    list_display = ('nombre', 'precio', 'stock_actual', 'codigo_barras', 'fecha_actualizacion')
    list_filter = ('categorias', 'fecha_creacion') # Filtros laterales
    search_fields = ('nombre', 'codigo_barras') # Barra de búsqueda