"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from inventario import views 
from auditoria import views as audit_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # 1. La Raíz es el Login
    path('', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),

    # 2. La ruta de Logout
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # 3. La pantalla principal del sistema (Dashboard)
    path('dashboard/', views.dashboard, name='dashboard'),
    # 4. La lista de productos
    path('productos/', views.producto_list, name='producto_list'),
    # 5. Crear nuevo producto
    path('productos/nuevo/', views.producto_crear, name='producto_crear'),
    # 6. Editar producto existente
    path('productos/editar/<int:pk>/', views.producto_editar, name='producto_editar'),
    # 7. Lista de clientes
    path('clientes/', views.cliente_lista, name='cliente_lista'),
    path('clientes/nuevo/', views.cliente_crear, name='cliente_crear'),
    path('clientes/editar/<int:pk>/', views.cliente_editar, name='cliente_editar'),
    # 8. Ventas
    path('ventas/', views.venta_list, name='venta_list'),
    path('ventas/nueva/', views.nueva_venta, name='nueva_venta'),
    path('ventas/ticket/<int:pk>/', views.ticket_venta, name='ticket_venta'),
    #8. Presupuestos
    path('presupuestos/nuevo/', views.nuevo_presupuesto, name='nuevo_presupuesto'),
    path('presupuestos/ver/<int:pk>/', views.ver_presupuesto, name='ver_presupuesto'),
    path('presupuestos/', views.presupuesto_list, name='presupuesto_list'),
    #9. Refundicion de cuentas
    path('contabilidad/libro-diario/', views.libro_diario, name='libro_diario'),
    path('contabilidad/cierre/', views.generar_cierre_contable, name='generar_cierre'),
    path('caja/gestion/', views.gestion_caja, name='gestion_caja'),
    path('caja/abrir/', views.abrir_caja, name='abrir_caja'),
    path('caja/cerrar/', views.cerrar_caja, name='cerrar_caja'),
    #Proveedores
    path('proveedores/', views.proveedor_list, name='proveedor_list'),
    path('proveedores/nuevo/', views.proveedor_crear, name='proveedor_crear'),
    path('proveedores/editar/<int:pk>/', views.proveedor_editar, name='proveedor_editar'),
    path('proveedores/eliminar/<int:pk>/', views.proveedor_eliminar, name='proveedor_eliminar'),
    path('compras/nueva/', views.nueva_compra, name='nueva_compra'),
    #auditorias
    path('auditoria/panel/', audit_views.ajuste_stock, name='auditoria_panel'),
]
