import decimal
from django.db import models
from django.contrib.auth.models import User

# ✅ CATEGORÍA DE PRODUCTOS
class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre

# ✅ PERFIL DE USUARIO
class Perfil(models.Model):
    ROL_CHOICES = (
        ('admin', 'Administrador'),
        ('bartender', 'Bartender'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=15)
    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='bartender')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.rol}"

# ✅ MESA
class Mesa(models.Model):
    numero = models.PositiveIntegerField(unique=True)
    ubicacion = models.CharField(max_length=100, blank=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"Mesa {self.numero}"

# ✅ PRODUCTO
class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='productos')
    descripcion = models.TextField(blank=True)
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # NUEVO
    precio = models.DecimalField(max_digits=10, decimal_places=2)  # Este es el precio de venta
    cantidad = models.PositiveIntegerField()
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def ganancia_unitaria(self):  # NUEVO MÉTODO
        return self.precio - self.precio_costo

    def porcentaje_ganancia(self):  # NUEVO MÉTODO
        if self.precio_costo > 0:
            return ((self.precio - self.precio_costo) / self.precio_costo) * 100
        return 0

    def __str__(self):
        return self.nombre
# ✅ MOVIMIENTO CONTABLE - MOVIDO ANTES DE VENTA
class MovimientoContable(models.Model):
    TIPO = [
        ('ingreso', 'Ingreso'),
        ('gasto', 'Gasto'),
    ]
    tipo = models.CharField(max_length=10, choices=TIPO)
    concepto = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # CAMPO para relacionar con ventas
    venta_relacionada = models.OneToOneField('Venta', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.tipo.upper()} - {self.concepto} - {self.monto}"

class Venta(models.Model):
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('credito', 'Crédito/Fiado'),
        ('mixto', 'Pago Mixto'),
        ('compartido', 'Pago Compartido'),
    ]

    mesa = models.ForeignKey(Mesa, on_delete=models.SET_NULL, null=True, related_name='ventas')
    mesero = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ventas')
    fecha = models.DateTimeField(auto_now_add=True)
    # 🔥 CAMPO CORREGIDO - Más restrictivo con decimales
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    cerrada = models.BooleanField(default=False)
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='efectivo')
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vuelto = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # 🔥 MÉTODO PERSONALIZADO PARA OBTENER TOTAL SEGURO
    def get_total_seguro(self):
        """Obtiene el total de forma segura, manejando errores de decimal"""
        try:
            if self.total is None:
                return 0.00
            return float(self.total)
        except (decimal.InvalidOperation, ValueError, TypeError):
            return 0.00

    def save(self, *args, **kwargs):
        # 🔥 VALIDAR Y LIMPIAR EL TOTAL ANTES DE GUARDAR
        try:
            if self.total is None:
                self.total = 0.00
            else:
                # Convertir a Decimal de forma segura
                from decimal import Decimal, InvalidOperation
                if isinstance(self.total, str):
                    self.total = Decimal(self.total)
                elif isinstance(self.total, (int, float)):
                    self.total = Decimal(str(self.total))
        except (InvalidOperation, ValueError, TypeError):
            self.total = 0.00

        # Verificar si la venta se está cerrando (de False a True)
        es_nueva_venta_cerrada = False
        if self.pk:
            try:
                venta_anterior = Venta.objects.get(pk=self.pk)
                if not venta_anterior.cerrada and self.cerrada:
                    es_nueva_venta_cerrada = True
            except Venta.DoesNotExist:
                pass
        elif self.cerrada:
            es_nueva_venta_cerrada = True

        super().save(*args, **kwargs)

        # Solo crear movimiento contable si se está cerrando la venta y no es crédito
        if es_nueva_venta_cerrada and self.metodo_pago != 'credito':
            MovimientoContable.objects.get_or_create(
                venta_relacionada=self,
                defaults={
                    'tipo': 'ingreso',
                    'concepto': f'Venta Mesa {self.mesa.numero if self.mesa else "N/A"}',
                    'monto': self.total,
                    'usuario': self.mesero
                }
            )

    def __str__(self):
        mesa_str = f"Mesa {self.mesa.numero}" if self.mesa else "Mesa N/A"
        return f"Venta #{self.id} - {mesa_str}"
    
# ✅ DETALLE DE VENTA
class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

# ✅ FACTURA
class Factura(models.Model):
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name='factura')
    numero = models.CharField(max_length=50, unique=True)
    cliente = models.CharField(max_length=255, blank=True, null=True)
    fecha_emision = models.DateField(auto_now_add=True)
    notas = models.TextField(blank=True)

    def __str__(self):
        return f"Factura {self.numero}"

# ✅ NOTIFICACIÓN (CORREGIDA)
class Notificacion(models.Model):
    # CAMBIO: Permitir producto NULL para notificaciones generales
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True)
    mensaje = models.TextField()
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    leido = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.producto:
            return f"{self.producto.nombre} - {self.mensaje[:30]}"
        else:
            return f"Notificación general - {self.mensaje[:30]}"
# ✅ DEUDA (CON MOVIMIENTOS AUTOMÁTICOS AL PAGAR)
class Deuda(models.Model):
    venta = models.OneToOneField('Venta', on_delete=models.CASCADE, related_name='deuda')
    nombre_cliente = models.CharField(max_length=255)
    telefono_cliente = models.CharField(max_length=20)
    monto_adeudado = models.DecimalField(max_digits=10, decimal_places=2)
    pagado = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Si se marca como pagada, crear movimiento de ingreso
        if self.pk:
            try:
                deuda_anterior = Deuda.objects.get(pk=self.pk)
                if not deuda_anterior.pagado and self.pagado:
                    super().save(*args, **kwargs)
                    MovimientoContable.objects.create(
                        tipo='ingreso',
                        concepto=f'Pago deuda: {self.nombre_cliente}',
                        monto=self.monto_adeudado,
                        usuario=None
                    )
                    return
            except Deuda.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Deuda de {self.nombre_cliente} - ${self.monto_adeudado}"

# ✅ GASTO (YA FUNCIONABA)
class Gasto(models.Model):
    concepto = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        MovimientoContable.objects.create(
            tipo='gasto',
            concepto=f"Gasto: {self.concepto}",
            monto=self.monto,
            usuario=self.registrado_por
        )

    def __str__(self):
        return f"Gasto: {self.concepto} - ${self.monto}"

# ✅ PAGO BARTENDER (YA FUNCIONABA)
class PagoBartender(models.Model):
    bartender = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'perfil__rol': 'bartender'})
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateField(auto_now_add=True)
    observacion = models.TextField(blank=True)
    pagado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='pagos_realizados')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        MovimientoContable.objects.create(
            tipo='gasto',
            concepto=f"Pago a bartender: {self.bartender.username}",
            monto=self.monto,
            usuario=self.pagado_por
        )

    def __str__(self):
        return f"Pago a {self.bartender.username} - ${self.monto}"

# ✅ PAGOS COMPARTIDOS Y MIXTOS
class PagoCompartido(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='pagos_compartidos')
    nombre_cliente = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=Venta.METODO_PAGO_CHOICES[:2])  # Solo efectivo y transferencia
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_cliente} - ${self.monto}"

class PagoMixto(models.Model):
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name='pago_mixto')
    monto_efectivo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_transferencia = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vuelto = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def total_pagado(self):
        return self.monto_efectivo + self.monto_transferencia

    def __str__(self):
        return f"Pago mixto - Efectivo: ${self.monto_efectivo}, Transferencia: ${self.monto_transferencia}"
    
    # Agregar al final de tu models.py

# ✅ SISTEMA DE DEVOLUCIONES
class Devolucion(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Autorización'),
        ('autorizada', 'Autorizada'),
        ('rechazada', 'Rechazada'),
        ('procesada', 'Procesada'),
    ]
    
    # Información básica
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    observaciones = models.TextField()
    
    # Control de estados
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    
    # Usuarios involucrados
    solicitada_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devoluciones_solicitadas')
    autorizada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='devoluciones_autorizadas')
    
    # Fechas de seguimiento
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    fecha_procesamiento = models.DateTimeField(null=True, blank=True)
    
    # Comentarios del administrador
    comentario_admin = models.TextField(blank=True, null=True)
    
    # Movimiento contable relacionado (para revertir si es necesario)
    movimiento_reversion = models.OneToOneField(MovimientoContable, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        from django.utils import timezone
        
        # Si se está autorizando o rechazando, guardar la fecha
        if self.pk:
            try:
                devolucion_anterior = Devolucion.objects.get(pk=self.pk)
                if devolucion_anterior.estado == 'pendiente' and self.estado in ['autorizada', 'rechazada']:
                    self.fecha_autorizacion = timezone.now()
                elif devolucion_anterior.estado == 'autorizada' and self.estado == 'procesada':
                    self.fecha_procesamiento = timezone.now()
                    # Procesar la devolución: devolver al inventario
                    self.producto.cantidad += self.cantidad
                    self.producto.save()
                    
                    # Crear movimiento contable de ajuste (gasto por devolución)
                    MovimientoContable.objects.create(
                        tipo='gasto',
                        concepto=f'Devolución: {self.producto.nombre} (x{self.cantidad})',
                        monto=self.producto.precio * self.cantidad,
                        usuario=self.autorizada_por
                    )
            except Devolucion.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)

    def valor_total(self):
        """Calcula el valor total de la devolución"""
        return self.producto.precio * self.cantidad

    def puede_ser_procesada(self):
        """Verifica si la devolución puede ser procesada"""
        return self.estado == 'autorizada'

    def __str__(self):
        return f"Devolución #{self.id} - {self.producto.nombre} (x{self.cantidad}) - {self.estado}"

    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = 'Devolución'
        verbose_name_plural = 'Devoluciones'