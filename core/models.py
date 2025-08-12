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

# ✅ PRODUCTO CON VALIDACIONES
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

    # 🔥 NUEVO MÉTODO: Validaciones del modelo
    def clean(self):
        from django.core.exceptions import ValidationError
        from decimal import Decimal
        
        errors = {}
        
        # Validar que el precio de venta sea mayor a 0
        if self.precio is not None and self.precio <= 0:
            errors['precio'] = 'El precio de venta debe ser mayor a cero ($0).'
        
        # Validar que precio_costo sea mayor o igual a 0
        if self.precio_costo is not None and self.precio_costo < 0:
            errors['precio_costo'] = 'El precio de costo no puede ser negativo.'
        
        # Validar que precio_costo < precio_venta (cuando ambos están definidos)
        if (self.precio_costo is not None and self.precio is not None and 
            self.precio_costo > 0 and self.precio > 0):
            
            if self.precio_costo >= self.precio:
                errors['precio_costo'] = f'El precio de costo (${self.precio_costo:,.0f}) debe ser menor al precio de venta (${self.precio:,.0f}).'
                errors['precio'] = 'El precio de venta debe ser mayor al precio de costo para generar ganancia.'
        
        # Validar cantidad no negativa (aunque sea PositiveIntegerField, doble validación)
        if self.cantidad is not None and self.cantidad < 0:
            errors['cantidad'] = 'La cantidad no puede ser negativa.'
        
        # Validar que el nombre no esté vacío
        if not self.nombre or self.nombre.strip() == '':
            errors['nombre'] = 'El nombre del producto es obligatorio.'
        
        if errors:
            raise ValidationError(errors)

    # 🔥 NUEVO MÉTODO: Detectar stock bajo
    def stock_bajo(self):
        """
        Retorna True si el stock está bajo (cantidad <= 5)
        Útil para alertas de inventario
        """
        return self.cantidad <= 5

    # 🔥 NUEVO MÉTODO: Estado del stock como texto
    def estado_stock(self):
        """
        Retorna el estado del stock como texto descriptivo
        """
        if self.cantidad == 0:
            return "Sin stock"
        elif self.stock_bajo():
            return "Stock bajo"
        elif self.cantidad <= 10:
            return "Stock moderado"
        else:
            return "Stock disponible"

    # 🔥 NUEVO MÉTODO: Clase CSS para alertas en templates
    def clase_stock_css(self):
        """
        Retorna clase CSS para colorear según el stock
        """
        if self.cantidad == 0:
            return "text-danger fw-bold"  # Rojo fuerte
        elif self.stock_bajo():
            return "text-warning fw-bold"  # Amarillo/naranja
        elif self.cantidad <= 10:
            return "text-info"  # Azul claro
        else:
            return "text-success"  # Verde

    # 🔥 NUEVO MÉTODO: Validar antes de guardar
    def save(self, *args, **kwargs):
        # Ejecutar validaciones antes de guardar
        self.clean()
        super().save(*args, **kwargs)

    # 🔥 MÉTODO MEJORADO: __str__ con información de stock
    def __str__(self):
        stock_info = f" (Stock: {self.cantidad})"
        if self.stock_bajo():
            stock_info += " ⚠️"
        elif self.cantidad == 0:
            stock_info += " ❌"
        
        return f"{self.nombre}{stock_info}"

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

# 🔥 MODELO VENTA CON CORRECCIONES CRÍTICAS
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
    
    # 🔥 CORRECCIÓN 1: Campo total más estable (max_digits=10)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    cerrada = models.BooleanField(default=False)
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='efectivo')
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    vuelto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # 🔥 NUEVO CAMPO: Flag para evitar duplicar movimientos contables
    movimiento_contable_creado = models.BooleanField(default=False)

    # 🔥 CORRECCIÓN 2: Método para obtener total seguro
    def get_total_seguro(self):
        """Obtiene el total de forma segura, manejando errores de decimal"""
        try:
            if self.total is None:
                return 0.00
            return float(self.total)
        except (decimal.InvalidOperation, ValueError, TypeError):
            return 0.00

    # 🔥 CORRECCIÓN 3: Método para formato colombiano
    def get_total_formateado(self):
        """Retorna el total en formato peso colombiano: $1.234.567"""
        try:
            total_safe = self.get_total_seguro()
            if total_safe == 0:
                return "$0"
            
            # Convertir a entero para formato colombiano
            total_entero = int(total_safe)
            
            # Formatear con separadores de miles usando puntos
            formatted = f"{total_entero:,}".replace(',', '.')
            return f"${formatted}"
            
        except (ValueError, TypeError):
            return "$0"

    # 🔥 MÉTODO ADICIONAL: Total como entero para templates
    def get_total_entero(self):
        """Retorna el total como entero para usar en templates con filtros"""
        try:
            return int(self.get_total_seguro())
        except (ValueError, TypeError):
            return 0

    # 🔥 CORRECCIÓN 4: Método save mejorado con mejor manejo de Decimal
    def save(self, *args, **kwargs):
        from decimal import Decimal, InvalidOperation
        
        # 🔥 MEJORAR VALIDACIÓN Y CONVERSIÓN DEL TOTAL
        try:
            if self.total is None:
                self.total = Decimal('0.00')
            else:
                # Manejo más robusto de conversiones
                if isinstance(self.total, str):
                    # Limpiar string: remover espacios, comas, y caracteres no numéricos excepto punto
                    total_clean = str(self.total).strip().replace(',', '').replace(' ', '')
                    if not total_clean or total_clean == '':
                        total_clean = '0.00'
                    self.total = Decimal(total_clean)
                elif isinstance(self.total, (int, float)):
                    # Convertir números a string primero para evitar problemas de precisión
                    self.total = Decimal(str(float(self.total)))
                elif not isinstance(self.total, Decimal):
                    # Fallback para otros tipos
                    self.total = Decimal(str(self.total))
                
                # Asegurar que no sea negativo
                if self.total < 0:
                    self.total = Decimal('0.00')
                    
        except (InvalidOperation, ValueError, TypeError) as e:
            print(f"Error convirtiendo total a Decimal: {e}")
            self.total = Decimal('0.00')

        # 🔥 VERIFICAR SI ES NUEVA VENTA CERRADA (sin duplicar movimientos)
        es_nueva_venta_cerrada = False
        if self.pk:
            try:
                venta_anterior = Venta.objects.get(pk=self.pk)
                # Solo si: no estaba cerrada antes, se está cerrando ahora, y no se ha creado el movimiento
                if (not venta_anterior.cerrada and 
                    self.cerrada and 
                    not self.movimiento_contable_creado):
                    es_nueva_venta_cerrada = True
            except Venta.DoesNotExist:
                pass
        elif self.cerrada and not self.movimiento_contable_creado:
            # Nueva venta que se crea ya cerrada
            es_nueva_venta_cerrada = True

        # Guardar primero
        super().save(*args, **kwargs)

        # 🔥 CORRECCIÓN 5: Crear movimiento contable SIN DUPLICAR
        if es_nueva_venta_cerrada and self.metodo_pago != 'credito':
            try:
                # Verificar que no exista ya un movimiento para esta venta
                if not MovimientoContable.objects.filter(venta_relacionada=self).exists():
                    MovimientoContable.objects.create(
                        venta_relacionada=self,
                        tipo='ingreso',
                        concepto=f'Venta Mesa {self.mesa.numero if self.mesa else "N/A"}',
                        monto=self.total,
                        usuario=self.mesero
                    )
                    
                    # Marcar que ya se creó el movimiento
                    self.movimiento_contable_creado = True
                    # Guardar sin disparar save() de nuevo
                    super().save(update_fields=['movimiento_contable_creado'])
                    
            except Exception as e:
                print(f"Error creando MovimientoContable para venta {self.id}: {e}")

    def __str__(self):
        mesa_str = f"Mesa {self.mesa.numero}" if self.mesa else "Mesa N/A"
        return f"Venta #{self.id} - {mesa_str} - {self.get_total_formateado()}"

# ✅ DETALLE DE VENTA CON VALIDACIONES
class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.precio_unitario * self.cantidad

    # 🔥 NUEVO MÉTODO: Subtotal con formato colombiano
    def subtotal_formateado(self):
        """
        Retorna el subtotal en formato peso colombiano: $1.234.567
        """
        try:
            subtotal_valor = float(self.subtotal())
            if subtotal_valor == 0:
                return "$0"
            
            # Convertir a entero para formato colombiano
            subtotal_entero = int(subtotal_valor)
            
            # Formatear con separadores de miles usando puntos
            formatted = f"{subtotal_entero:,}".replace(',', '.')
            return f"${formatted}"
            
        except (ValueError, TypeError):
            return "$0"

    # 🔥 NUEVO MÉTODO: Subtotal como entero para templates
    def subtotal_entero(self):
        """
        Retorna el subtotal como entero para usar en templates con filtros
        """
        try:
            return int(float(self.subtotal()))
        except (ValueError, TypeError):
            return 0

    # 🔥 NUEVO MÉTODO: Validaciones del modelo
    def clean(self):
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # Validar que el producto exista
        if not self.producto:
            errors['producto'] = 'Debe seleccionar un producto válido.'
        
        # Validar cantidad positiva
        if self.cantidad is not None and self.cantidad <= 0:
            errors['cantidad'] = 'La cantidad debe ser mayor a cero.'
        
        # Validar precio unitario positivo
        if self.precio_unitario is not None and self.precio_unitario <= 0:
            errors['precio_unitario'] = 'El precio unitario debe ser mayor a cero.'
        
        # 🔥 VALIDACIÓN CRÍTICA: Control de stock disponible
        if self.producto and self.cantidad:
            # Si es un detalle nuevo (no tiene ID)
            if not self.pk:
                stock_disponible = self.producto.cantidad
                
                if self.cantidad > stock_disponible:
                    errors['cantidad'] = (
                        f'Stock insuficiente. Disponible: {stock_disponible} unidades. '
                        f'Solicitado: {self.cantidad} unidades.'
                    )
            
            # Si es un detalle existente que se está modificando
            else:
                try:
                    detalle_anterior = DetalleVenta.objects.get(pk=self.pk)
                    # Calcular cuánto stock se liberaría del cambio
                    diferencia_cantidad = self.cantidad - detalle_anterior.cantidad
                    
                    # Si se está aumentando la cantidad, verificar stock
                    if diferencia_cantidad > 0:
                        stock_disponible = self.producto.cantidad
                        
                        if diferencia_cantidad > stock_disponible:
                            errors['cantidad'] = (
                                f'Stock insuficiente para el aumento. '
                                f'Disponible: {stock_disponible} unidades. '
                                f'Aumento solicitado: {diferencia_cantidad} unidades.'
                            )
                except DetalleVenta.DoesNotExist:
                    # Si no existe el detalle anterior, tratar como nuevo
                    if self.cantidad > self.producto.cantidad:
                        errors['cantidad'] = (
                            f'Stock insuficiente. Disponible: {self.producto.cantidad} unidades.'
                        )
        
        # 🔥 VALIDACIÓN ADICIONAL: Verificar que la venta no esté cerrada
        if self.venta and self.venta.cerrada:
            errors['venta'] = 'No se pueden modificar los detalles de una venta cerrada.'
        
        if errors:
            raise ValidationError(errors)

    # 🔥 NUEVO MÉTODO: Información del stock después de la venta
    def stock_resultante(self):
        """
        Retorna el stock que quedaría después de esta venta
        """
        if self.producto:
            return max(0, self.producto.cantidad - self.cantidad)
        return 0

    # 🔥 NUEVO MÉTODO: Verificar si generará stock bajo
    def generara_stock_bajo(self):
        """
        Retorna True si esta venta dejará el producto con stock bajo
        """
        return self.stock_resultante() <= 5

    # 🔥 MÉTODO MEJORADO: Validar antes de guardar
    def save(self, *args, **kwargs):
        # Ejecutar validaciones antes de guardar
        self.clean()
        super().save(*args, **kwargs)

    # 🔥 MÉTODO MEJORADO: __str__ con información detallada
    def __str__(self):
        if self.producto:
            subtotal_str = self.subtotal_formateado()
            return f"{self.cantidad} x {self.producto.nombre} = {subtotal_str}"
        else:
            return f"{self.cantidad} x Producto eliminado"

    class Meta:
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Venta'

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