from django.contrib import admin

# Register your models here.
# AGREGAR AL ARCHIVO core/admin.py

from django.contrib import admin
from .models import (
    Producto, Categoria, Mesa, Venta, DetalleVenta, 
    Notificacion, Deuda, PagoCompartido, PagoMixto, 
    MovimientoContable, Gasto, PagoBartender, Perfil,
    Devolucion  # 🔥 AGREGAR ESTE IMPORT
)

# ... otros registros de admin existentes ...

# 🔥 REGISTRO COMPLETO PARA DEVOLUCIONES
@admin.register(Devolucion)
class DevolucionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'producto', 
        'cantidad', 
        'tipo',
        'estado', 
        'solicitada_por', 
        'fecha_solicitud',
        'autorizada_por',
        'valor_total_display'
    ]
    
    list_filter = [
        'estado', 
        'tipo', 
        'razon',
        'fecha_solicitud', 
        'fecha_autorizacion'
    ]
    
    search_fields = [
        'producto__nombre', 
        'solicitada_por__username', 
        'autorizada_por__username',
        'observaciones'
    ]
    
    readonly_fields = [
        'fecha_solicitud', 
        'fecha_autorizacion', 
        'fecha_procesamiento',
        'valor_total_display',
        'puede_ser_procesada_display'
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'producto', 
                'cantidad', 
                'tipo', 
                'razon'
            )
        }),
        ('Detalles', {
            'fields': (
                'observaciones',
                'venta_origen'
            )
        }),
        ('Gestión', {
            'fields': (
                'estado', 
                'comentario_admin'
            )
        }),
        ('Seguimiento', {
            'fields': (
                'solicitada_por',
                'fecha_solicitud',
                'autorizada_por', 
                'fecha_autorizacion',
                'fecha_procesamiento'
            ),
            'classes': ('collapse',)
        }),
        ('Información Calculada', {
            'fields': (
                'valor_total_display',
                'puede_ser_procesada_display'
            ),
            'classes': ('collapse',)
        })
    )
    
    def valor_total_display(self, obj):
        """Mostrar valor total formateado"""
        try:
            return f"${obj.valor_total:,.0f} COP"
        except:
            return "Error en cálculo"
    valor_total_display.short_description = "Valor Total"
    
    def puede_ser_procesada_display(self, obj):
        """Mostrar si puede ser procesada"""
        return "Sí" if obj.puede_ser_procesada else "No"
    puede_ser_procesada_display.short_description = "¿Puede procesarse?"
    puede_ser_procesada_display.boolean = True
    
    def save_model(self, request, obj, form, change):
        """Override para manejar cambios de estado"""
        if change:  # Si es una edición
            # Obtener el objeto original
            original = Devolucion.objects.get(pk=obj.pk)
            
            # Si se está autorizando o rechazando
            if original.estado == 'pendiente' and obj.estado in ['autorizada', 'rechazada']:
                obj.autorizada_por = request.user
                from django.utils import timezone
                obj.fecha_autorizacion = timezone.now()
        
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        """Optimizar consultas"""
        return super().get_queryset(request).select_related(
            'producto', 'solicitada_por', 'autorizada_por', 'venta_origen'
        )

# 🔥 SI NO TIENES OTROS MODELOS REGISTRADOS, AGREGAR ESTOS TAMBIÉN:

# Solo agregar si no están ya registrados
if not admin.site.is_registered(Producto):
    @admin.register(Producto)
    class ProductoAdmin(admin.ModelAdmin):
        list_display = ['nombre', 'categoria', 'precio', 'precio_costo', 'cantidad']
        list_filter = ['categoria']
        search_fields = ['nombre']

if not admin.site.is_registered(Categoria):
    @admin.register(Categoria)
    class CategoriaAdmin(admin.ModelAdmin):
        list_display = ['nombre', 'descripcion']
        search_fields = ['nombre']

if not admin.site.is_registered(Venta):
    @admin.register(Venta)
    class VentaAdmin(admin.ModelAdmin):
        list_display = ['id', 'mesa', 'mesero', 'total', 'fecha', 'cerrada']
        list_filter = ['cerrada', 'metodo_pago', 'fecha']
        search_fields = ['mesa__numero', 'mesero__username']