from django.urls import path
from . import views
from .views import seguimiento_mesas, generar_factura_html

urlpatterns = [
    # Autenticación
    path('', views.custom_login),
    path('registro/', views.registro, name='registro'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),

    # Perfil de usuario
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/editar/', views.perfil_editar, name='perfil_editar'),
    path('cuenta/eliminar/', views.cuenta_eliminar, name='cuenta_eliminar'),

    # Dashboard y roles
    path('panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('panel/asignar_roles/', views.asignar_roles, name='asignar_roles'),
    path('usuarios/notificar/<int:user_id>/', views.enviar_notificacion_usuario, name='enviar_notificacion_usuario'),
    path('seguimiento/mesas/', views.seguimiento_mesas, name='seguimiento_mesas'),
    path('panel/ventas/', views.admin_ventas, name='admin_ventas'),

    path('inicio/', views.inicio, name='inicio'),

    # Movimiento contable
    path('movimientos/', views.movimientos_contables, name='movimientos_contables'),

    # Productos
    path('productos/', views.productos_listar, name='productos_listar'),
    path('productos/crear/', views.producto_crear, name='producto_crear'),
    path('productos/<int:pk>/editar/', views.producto_editar, name='producto_editar'),
    path('productos/<int:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    path('productos/ver/', views.productos_bartender, name='productos_bartender'),

    # Categorías
    path('categorias/', views.categorias_listar, name='categorias_listar'),
    path('categorias/crear/', views.categoria_crear, name='categoria_crear'),
    path('categorias/editar/<int:pk>/', views.categoria_editar, name='categoria_editar'),
    path('categorias/eliminar/<int:pk>/', views.categoria_eliminar, name='categoria_eliminar'),

    # Mesas
    path('mesas/', views.mesas_listar, name='mesas_listar'),
    path('mesas/crear/', views.mesa_crear, name='mesa_crear'),
    path('mesas/<int:pk>/editar/', views.mesa_editar, name='mesa_editar'),
    path('mesas/<int:pk>/eliminar/', views.mesa_eliminar, name='mesa_eliminar'),
    path('mesas/activas/', views.mesas_activas, name='mesas_activas'),

    # Ventas por mesa
    path('mesas/<int:mesa_id>/venta/', views.venta_mesa, name='venta_mesa'),
    path('ventas/detalle/<int:detalle_id>/eliminar/', views.eliminar_detalle, name='eliminar_detalle'),
    path('ventas/<int:venta_id>/finalizar/', views.finalizar_venta, name='finalizar_venta'),

    # NUEVAS RUTAS PARA PAGOS COMPARTIDOS Y MIXTOS
    path('ventas/<int:venta_id>/pago-compartido/', views.pago_compartido, name='pago_compartido'),
    path('ventas/<int:venta_id>/pago-mixto/', views.pago_mixto, name='pago_mixto'),

    # Notificaciones
    path('notificar/<int:producto_id>/', views.notificar_admin, name='notificar_admin'),
    path('notificaciones/', views.ver_notificaciones, name='ver_notificaciones'),

    # 🔥 CIERRE DE CAJA Y FACTURAS
    path('cerrar-caja/', views.cerrar_caja_dia, name='cerrar_caja_dia'),
    path('caja/factura-html/', generar_factura_html, name='generar_factura_html'),
    
    # 🔥 NUEVAS APIs OPTIMIZADAS
    path('api/resumen-dia/', views.resumen_dia_ajax, name='resumen_dia_ajax'),
    path('api/comparacion-dias/', views.comparacion_dias, name='comparacion_dias'),
    
    # Deudores
    path('panel/deudores/', views.ver_deudores, name='ver_deudores'),
    path('panel/deudores/marcar/<int:deuda_id>/', views.marcar_deuda_pagada, name='marcar_deuda_pagada'),
    
    # Estadísticas
    path('estadisticas/', views.estadisticas, name='estadisticas'),

    # Recomendaciones de precios
    path('productos/recomendaciones/', views.recomendaciones_precio, name='recomendaciones_precio'),

    # Gestión de gastos
    path('gastos/', views.gastos_dashboard, name='gastos_dashboard'),
    path('gastos/crear/', views.crear_gasto, name='crear_gasto'),
    path('gastos/eliminar/<int:gasto_id>/', views.eliminar_gasto, name='eliminar_gasto'),
    path('pagos-bartender/crear/', views.crear_pago_bartender, name='crear_pago_bartender'),
    path('pagos-bartender/eliminar/<int:pago_id>/', views.eliminar_pago_bartender, name='eliminar_pago_bartender'),

    # Sistema de devoluciones
    path('devoluciones/solicitar/', views.solicitar_devolucion, name='solicitar_devolucion'),
    path('devoluciones/mis-solicitudes/', views.mis_devoluciones, name='mis_devoluciones'),
    path('panel/devoluciones/', views.gestionar_devoluciones, name='gestionar_devoluciones'),
    path('panel/devoluciones/autorizar/<int:devolucion_id>/', views.autorizar_devolucion, name='autorizar_devolucion'),
    path('panel/devoluciones/procesar/<int:devolucion_id>/', views.procesar_devolucion, name='procesar_devolucion'),
    path('api/devoluciones/pendientes/', views.devoluciones_api_pendientes, name='devoluciones_api_pendientes'),
]