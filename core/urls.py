from django.urls import path
from . import views

urlpatterns = [
    # ========================================================================================
    # 🔐 AUTENTICACIÓN Y USUARIOS
    # ========================================================================================
    path('', views.custom_login, name='home'),
    path('login/', views.custom_login, name='login'),
    path('accounts/login/', views.custom_login, name='accounts_login'),
    path('logout/', views.custom_logout, name='logout'),

    # Perfil de usuario
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/editar/', views.perfil_editar, name='perfil_editar'),
    path('cuenta/eliminar/', views.cuenta_eliminar, name='cuenta_eliminar'),

    # ========================================================================================
    # 🏠 DASHBOARD Y PANELES PRINCIPALES
    # ========================================================================================
    path('inicio/', views.inicio, name='inicio'),
    path('panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('panel/asignar_roles/', views.asignar_roles, name='asignar_roles'),
    path('usuarios/notificar/<int:user_id>/', views.enviar_notificacion_usuario, name='enviar_notificacion_usuario'),
    path('seguimiento/mesas/', views.seguimiento_mesas, name='seguimiento_mesas'),
    path('panel/ventas/', views.admin_ventas, name='admin_ventas'),

    # ========================================================================================
    # 💰 CONTABILIDAD Y MOVIMIENTOS
    # ========================================================================================
    path('movimientos/', views.movimientos_contables, name='movimientos_contables'),

    # ========================================================================================
    # 📦 INVENTARIO Y PRODUCTOS
    # ========================================================================================
    path('inventario/', views.productos_listar, name='productos_listar'),
    path('productos/', views.productos_listar, name='productos_listar'),  # Alias
    path('inventario/crear/', views.producto_crear, name='producto_crear'),
    path('inventario/<int:pk>/editar/', views.producto_editar, name='producto_editar'),
    path('inventario/<int:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    path('inventario/ver/', views.productos_bartender, name='productos_bartender'),
    
    # Imágenes de productos
    path('inventario/<int:pk>/ver-imagen/', views.producto_ver_imagen, name='producto_ver_imagen'),
    path('api/producto/<int:pk>/info/', views.producto_info_api, name='producto_info_api'),

    # Recomendaciones de precios
    path('productos/recomendaciones/', views.recomendaciones_precio, name='recomendaciones_precio'),

    # ========================================================================================
    # 🏷️ CATEGORÍAS
    # ========================================================================================
    path('categorias/', views.categorias_listar, name='categorias_listar'),
    path('categorias/crear/', views.categoria_crear, name='categoria_crear'),
    path('categorias/editar/<int:pk>/', views.categoria_editar, name='categoria_editar'),
    path('categorias/eliminar/<int:pk>/', views.categoria_eliminar, name='categoria_eliminar'),

    # ========================================================================================
    # 🏓 MESAS Y SEGUIMIENTO
    # ========================================================================================
    path('mesas/', views.mesas_listar, name='mesas_listar'),
    path('mesas/<int:pk>/editar/', views.mesa_editar, name='mesa_editar'),
    path('mesas/<int:pk>/cambiar-estado/', views.mesa_cambiar_estado, name='mesa_cambiar_estado'),
    path('mesas/activas/', views.mesas_activas, name='mesas_activas'),

    # Funciones administrativas para el sistema de mesas
    path('admin/mesas/inicializar/', views.inicializar_mesas_sistema, name='inicializar_mesas_sistema'),
    path('admin/mesas/reset-numeracion/', views.reset_numeracion_mesas, name='reset_numeracion_mesas'),

    # APIs de mesas
    path('api/mesa/<int:pk>/info/', views.mesa_info_api, name='mesa_info_api'),
    path('admin/verificar-sistema-mesas/', views.verificar_sistema_mesas, name='verificar_sistema_mesas'),

    # ========================================================================================
    # 🛒 VENTAS Y FACTURACIÓN
    # ========================================================================================
    path('mesas/<int:mesa_id>/venta/', views.venta_mesa, name='venta_mesa'),
    path('ventas/detalle/<int:detalle_id>/eliminar/', views.eliminar_detalle, name='eliminar_detalle'),
    path('ventas/<int:venta_id>/finalizar/', views.finalizar_venta, name='finalizar_venta'),

    # Pagos compartidos y mixtos
    path('ventas/<int:venta_id>/pago-compartido/', views.pago_compartido, name='pago_compartido'),
    path('ventas/<int:venta_id>/pago-mixto/', views.pago_mixto, name='pago_mixto'),

    # ========================================================================================
    # 🎁 SISTEMA DE COMBOS
    # ========================================================================================
    path('combos/', views.combos_listar, name='combos_listar'),
    path('combos/crear/', views.combo_crear, name='combo_crear'),
    path('combos/<int:pk>/', views.combo_detalle, name='combo_detalle'),
    path('combos/<int:pk>/toggle/', views.combo_toggle_estado, name='combo_toggle_estado'),
    path('combos/<int:pk>/eliminar/', views.combo_eliminar, name='combo_eliminar'),
    path('combos/estadisticas/', views.combos_estadisticas, name='combos_estadisticas'),
    
    # Combos en ventas
    path('venta/mesa/<int:mesa_id>/agregar-combo/', views.venta_agregar_combo, name='venta_agregar_combo'),
    path('venta/combo/eliminar/<int:combo_venta_id>/', views.eliminar_combo_venta, name='eliminar_combo_venta'),
    # En core/urls.py
path('combos/asistente-precios/', views.combo_asistente_precios_api, name='combo_asistente_precios_api'),
    
    # API para combos
    path('api/combo/<int:pk>/info/', views.combo_info_api, name='combo_info_api'),

    # ========================================================================================
    # 💳 SISTEMA DE DEUDAS Y ABONOS
    # ========================================================================================
    path('deudas/', views.ver_deudores, name='ver_deudores'),
    path('deudas/marcar-pagada/<int:deuda_id>/', views.marcar_deuda_pagada, name='marcar_deuda_pagada'),
    path('deudas/registrar-abono/<int:deuda_id>/', views.registrar_abono_deuda, name='registrar_abono_deuda'),
    path('deudas/eliminar-abono/<int:abono_id>/', views.eliminar_abono, name='eliminar_abono'),
    path('deudas/reporte/', views.reporte_deudores, name='reporte_deudores'),
    path('deudores/corregir-duplicados/', views.corregir_duplicados_deudas, name='corregir_duplicados_deudas'),
    
    # APIs de deudas
    path('api/deudores/stats/', views.deudores_stats_api, name='deudores_stats_api'),

    # ========================================================================================
    # 🔔 NOTIFICACIONES
    # ========================================================================================
    path('notificar/<int:producto_id>/', views.notificar_admin, name='notificar_admin'),
    path('notificaciones/', views.ver_notificaciones, name='ver_notificaciones'),

    # ========================================================================================
    # 💰 CIERRE DE CAJA Y FACTURACIÓN
    # ========================================================================================
    path('cerrar-caja/', views.cerrar_caja_dia, name='cerrar_caja_dia'),
    path('caja/factura-html/', views.generar_factura_html, name='generar_factura_html'),
    
    # APIs optimizadas
    path('api/resumen-dia/', views.resumen_dia_ajax, name='resumen_dia_ajax'),
    path('api/comparacion-dias/', views.comparacion_dias, name='comparacion_dias'),

    # ========================================================================================
    # 📊 ESTADÍSTICAS Y REPORTES
    # ========================================================================================
    path('estadisticas/', views.estadisticas, name='estadisticas'),

    # ========================================================================================
    # 💸 GESTIÓN DE GASTOS Y PAGOS
    # ========================================================================================
    path('gastos/', views.gastos_dashboard, name='gastos_dashboard'),
    path('gastos/crear/', views.crear_gasto, name='crear_gasto'),
    path('gastos/eliminar/<int:gasto_id>/', views.eliminar_gasto, name='eliminar_gasto'),
    path('pagos-bartender/crear/', views.crear_pago_bartender, name='crear_pago_bartender'),
    path('pagos-bartender/eliminar/<int:pago_id>/', views.eliminar_pago_bartender, name='eliminar_pago_bartender'),

    # ========================================================================================
    # 🔄 SISTEMA DE DEVOLUCIONES
    # ========================================================================================
    path('devoluciones/solicitar/', views.solicitar_devolucion, name='solicitar_devolucion'),
    path('devoluciones/mis-solicitudes/', views.mis_devoluciones, name='mis_devoluciones'),
    path('panel/devoluciones/', views.gestionar_devoluciones, name='gestionar_devoluciones'),
    path('panel/devoluciones/autorizar/<int:devolucion_id>/', views.autorizar_devolucion, name='autorizar_devolucion'),
    path('panel/devoluciones/procesar/<int:devolucion_id>/', views.procesar_devolucion, name='procesar_devolucion'),
    path('panel/devoluciones/estadisticas/', views.estadisticas_devoluciones, name='estadisticas_devoluciones'),
    
    # Devoluciones mejoradas (sistema facturas integrado)
    path('solicitar-devolucion-mejorada/', views.solicitar_devolucion, name='solicitar_devolucion_mejorado'),
    path('gestionar-devoluciones-mejoradas/', views.gestionar_devoluciones, name='gestionar_devoluciones_mejorado'),
    path('devolver-proveedor/<int:detalle_factura_id>/', views.devolver_a_proveedor, name='devolver_a_proveedor'),
    
    # API devoluciones
    path('api/devoluciones/pendientes/', views.devoluciones_api_pendientes, name='devoluciones_api_pendientes'),
    
    # ========================================================================================
    # 🧾 SISTEMA DE FACTURAS COMPLETO
    # ========================================================================================
    
    # Dashboard de facturas
    path('facturas/', views.facturas_dashboard, name='facturas_dashboard'),
    
    # Gestión de proveedores
    path('proveedores/', views.proveedores_listar, name='proveedores_listar'),
    path('proveedores/crear/', views.proveedor_crear, name='proveedor_crear'),
    path('proveedores/<int:pk>/', views.proveedor_detalle, name='proveedor_detalle'),
    path('proveedores/<int:pk>/editar/', views.proveedor_editar, name='proveedor_editar'),
    path('proveedores/<int:pk>/eliminar/', views.proveedor_eliminar, name='proveedor_eliminar'),
    
    # Gestión de facturas
    path('facturas/listar/', views.facturas_listar, name='facturas_listar'),
    path('facturas/crear/', views.factura_crear, name='factura_crear'),
    path('facturas/<int:pk>/', views.factura_detalle, name='factura_detalle'),
    path('facturas/<int:pk>/editar/', views.factura_editar, name='factura_editar'),
    path('facturas/<int:pk>/cambiar-estado/', views.factura_cambiar_estado, name='factura_cambiar_estado'),
    path('facturas/<int:pk>/aplicar-inventario/', views.factura_aplicar_inventario, name='factura_aplicar_inventario'),
    path('facturas/<int:pk>/registrar-pago/', views.factura_registrar_pago, name='factura_registrar_pago'),
    
    # Gestión de detalles de factura
    path('facturas/<int:pk>/agregar-detalle/', views.factura_agregar_detalle, name='factura_agregar_detalle'),
    path('facturas/detalle/<int:detalle_id>/eliminar/', views.factura_eliminar_detalle, name='factura_eliminar_detalle'),
    path('facturas/detalle/<int:detalle_id>/enlazar/', views.enlazar_producto_factura, name='enlazar_producto_factura'),
    
    # Inventario por facturas (tracking)
    path('inventario-facturas/', views.inventario_por_facturas, name='inventario_por_facturas'),
    
    # Reportes de facturas
    path('facturas/reportes/', views.facturas_reportes, name='facturas_reportes'),
    path('reportes/ventas-facturas/', views.reporte_ventas_facturas, name='reporte_ventas_facturas'),
    path('reporte-devoluciones-proveedor/', views.reporte_devoluciones_por_proveedor, name='reporte_devoluciones_proveedor'),
    
    # APIs de facturas
    path('api/producto/<int:pk>/facturas/', views.producto_info_api_facturas, name='producto_info_api_facturas'),
    path('api/dashboard/stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    
    # ========================================================================================
    # 🛠️ ADMINISTRACIÓN Y UTILIDADES
    # ========================================================================================
    path('admin/limpiar-imagenes/', views.limpiar_imagenes_huerfanas, name='limpiar_imagenes_huerfanas'),
    path('api/estadisticas-imagenes/', views.estadisticas_imagenes, name='estadisticas_imagenes'),
    
    # Utilidades del sistema - LÍNEA CORREGIDA
    path('sistema/sincronizar/', views.sincronizar_sistema_completo, name='sincronizar_sistema'),
    path('sincronizar-sistema-completo/', views.sincronizar_sistema_completo, name='sincronizar_sistema_completo'),
    path('debug-sistema-facturas/', views.debug_sistema_facturas, name='debug_sistema_facturas'),
    path('debug-stock/', views.debug_stock, name='debug_stock'),
    # En core/urls.py, agregar esta línea
path('factura/devolver/<int:detalle_id>/', views.devolver_desde_factura, name='devolver_desde_factura'),
]