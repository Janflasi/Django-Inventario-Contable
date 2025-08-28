from datetime import timezone
import decimal
from django.db import models
from PIL import Image
from django.contrib.auth.models import User
from django.utils import timezone
import os

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
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField()
    
    # 🔥 CAMPO: Imagen del producto (OPCIONAL)
    imagen = models.ImageField(
        upload_to='productos/',
        null=True,
        blank=True,
        help_text="Imagen del producto (opcional). Tamaño recomendado: 800x600px"
    )
    
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def ganancia_unitaria(self):
        return self.precio - self.precio_costo

    def porcentaje_ganancia(self):
        if self.precio_costo > 0:
            return ((self.precio - self.precio_costo) / self.precio_costo) * 100
        return 0

    # 🔥 MÉTODO: Validar imagen
    def clean(self):
        from django.core.exceptions import ValidationError
        from decimal import Decimal
        
        errors = {}
        
        # Validaciones existentes...
        if self.precio is not None and self.precio <= 0:
            errors['precio'] = 'El precio de venta debe ser mayor a cero ($0).'
        
        if self.precio_costo is not None and self.precio_costo < 0:
            errors['precio_costo'] = 'El precio de costo no puede ser negativo.'
        
        if (self.precio_costo is not None and self.precio is not None and 
            self.precio_costo > 0 and self.precio > 0):
            
            if self.precio_costo >= self.precio:
                errors['precio_costo'] = f'El precio de costo (${self.precio_costo:,.0f}) debe ser menor al precio de venta (${self.precio:,.0f}).'
                errors['precio'] = 'El precio de venta debe ser mayor al precio de costo para generar ganancia.'
        
        if self.cantidad is not None and self.cantidad < 0:
            errors['cantidad'] = 'La cantidad no puede ser negativa.'
        
        if not self.nombre or self.nombre.strip() == '':
            errors['nombre'] = 'El nombre del producto es obligatorio.'
        
        # 🔥 VALIDACIÓN: Imagen (OPCIONAL)
        if self.imagen:
            # Validar tamaño del archivo (máximo 5MB)
            if self.imagen.size > 5 * 1024 * 1024:
                errors['imagen'] = 'La imagen es demasiado grande. Máximo permitido: 5MB.'
            
            # Validar extensión
            extensiones_validas = ['.jpg', '.jpeg', '.png', '.webp']
            extension = os.path.splitext(self.imagen.name)[1].lower()
            
            if extension not in extensiones_validas:
                errors['imagen'] = f'Formato de imagen no válido. Permitidos: {", ".join(extensiones_validas)}'
        
        if errors:
            raise ValidationError(errors)

    # 🔥 MÉTODO: Redimensionar imagen automáticamente
    def save(self, *args, **kwargs):
        # Ejecutar validaciones antes de guardar
        self.clean()
        
        # Guardar primero para obtener la ruta del archivo
        super().save(*args, **kwargs)
        
        # 🔥 REDIMENSIONAR IMAGEN SI EXISTE
        if self.imagen:
            self.redimensionar_imagen()

    def redimensionar_imagen(self):
        """
        Redimensiona la imagen automáticamente para optimizar espacio
        Tamaño objetivo: máximo 800x600px manteniendo proporción
        """
        try:
            from PIL import Image
            import os
            
            # Abrir la imagen
            img_path = self.imagen.path
            
            if os.path.exists(img_path):
                with Image.open(img_path) as img:
                    # Convertir a RGB si es necesario (para JPEGs)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    # Redimensionar manteniendo proporción
                    max_size = (800, 600)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Guardar la imagen redimensionada
                    img.save(img_path, 'JPEG', quality=85, optimize=True)
                    
        except Exception as e:
            print(f"Error redimensionando imagen para producto {self.id}: {e}")
            # No lanzar excepción para no interrumpir el guardado

    # 🔥 MÉTODO: URL de imagen o placeholder
    def get_imagen_url(self):
        """
        Retorna la URL de la imagen o un placeholder si no tiene imagen
        """
        if self.imagen:
            return self.imagen.url
        else:
            # Placeholder por defecto (puedes cambiar esta URL)
            return '/static/images/producto-placeholder.jpg'
    
    # 🔥 MÉTODO: Verificar si tiene imagen
    def tiene_imagen(self):
        """
        Retorna True si el producto tiene imagen
        """
        return bool(self.imagen)
    
    # 🔥 MÉTODO: Eliminar imagen anterior al actualizar
    def delete_old_image(self, old_image_path):
        """
        Elimina la imagen anterior cuando se actualiza el producto
        """
        try:
            if old_image_path and os.path.exists(old_image_path):
                os.remove(old_image_path)
        except Exception as e:
            print(f"Error eliminando imagen anterior: {e}")

    # 🔥 MÉTODO ACTUALIZADO: __str__ con indicador de imagen
    def __str__(self):
        stock_info = f" (Stock: {self.cantidad})"
        if self.stock_bajo():
            stock_info += " ⚠️"
        elif self.cantidad == 0:
            stock_info += " ❌"
        
        # Agregar indicador de imagen
        if self.tiene_imagen():
            stock_info += " 📷"
        
        return f"{self.nombre}{stock_info}"

    # Métodos existentes...
    def stock_bajo(self):
        return self.cantidad <= 5

    def estado_stock(self):
        if self.cantidad == 0:
            return "Sin stock"
        elif self.stock_bajo():
            return "Stock bajo"
        elif self.cantidad <= 10:
            return "Stock moderado"
        else:
            return "Stock disponible"

    def clase_stock_css(self):
        if self.cantidad == 0:
            return "text-danger fw-bold"
        elif self.stock_bajo():
            return "text-warning fw-bold"
        elif self.cantidad <= 10:
            return "text-info"
        else:
            return "text-success"

# ✅ MOVIMIENTO CONTABLE - ACTUALIZADO CON TIPO 'COSTO'
class MovimientoContable(models.Model):
    TIPO = [
        ('ingreso', 'Ingreso'),
        ('gasto', 'Gasto'),
        ('costo', 'Costo/Inversión'),  # 🔥 NUEVO TIPO AGREGADO
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

# ✅ DEUDA (COMPLETAMENTE CORREGIDA - SIN DUPLICADOS)
class Deuda(models.Model):
    """
    💳 Modelo de deudas de clientes - CORREGIDO sin duplicar movimientos contables
    
    IMPORTANTE: Los movimientos contables ahora se manejan EXCLUSIVAMENTE 
    desde las vistas de abonos, NO desde este modelo.
    """
    venta = models.OneToOneField('Venta', on_delete=models.CASCADE, related_name='deuda')
    nombre_cliente = models.CharField(max_length=255, verbose_name='Nombre del Cliente')
    telefono_cliente = models.CharField(max_length=20, verbose_name='Teléfono del Cliente')
    monto_adeudado = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name='Monto Adeudado'
    )
    pagado = models.BooleanField(default=False, verbose_name='¿Está Pagado?')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')
    
    # 🔥 NUEVO CAMPO: Para tracking de abonos
    total_abonado = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name='Total Abonado',
        help_text='Se actualiza automáticamente con los abonos'
    )

    class Meta:
        verbose_name = 'Deuda'
        verbose_name_plural = 'Deudas'
        ordering = ['-fecha_registro']

    def save(self, *args, **kwargs):
        """
        🔥 MÉTODO SAVE COMPLETAMENTE CORREGIDO
        
        ELIMINADO: La lógica automática de MovimientoContable que causaba duplicados
        AGREGADO: Solo actualización del campo total_abonado
        """
        
        # 🔄 ACTUALIZAR TOTAL ABONADO AUTOMÁTICAMENTE
        if self.pk:
            try:
                # Calcular total de abonos reales
                from django.db.models import Sum
                total_abonos = self.abonos.aggregate(total=Sum('monto'))['total']
                self.total_abonado = total_abonos or 0
                
                # 🔄 AUTO-MARCAR COMO PAGADA SI LOS ABONOS CUBREN LA DEUDA
                if self.total_abonado >= self.monto_adeudado and not self.pagado:
                    self.pagado = True
                    
            except Exception as e:
                print(f"Error actualizando total_abonado para deuda {self.pk}: {e}")
                # No interrumpir el guardado por este error
                pass
        
        # 🔥 GUARDAR SIN LÓGICA DE MOVIMIENTOS CONTABLES
        # Los movimientos se crean SOLO desde las vistas de abonos
        super().save(*args, **kwargs)

    def __str__(self):
        estado = "✅ Pagado" if self.pagado else "⏳ Pendiente"
        return f"Deuda de {self.nombre_cliente} - ${self.monto_adeudado:,.0f} - {estado}"

    # 🔥 MÉTODOS AUXILIARES MEJORADOS
    
    @property
    def saldo_pendiente(self):
        """
        💰 Calcula el saldo pendiente de pago
        """
        try:
            from django.db.models import Sum
            total_abonos = self.abonos.aggregate(total=Sum('monto'))['total'] or 0
            saldo = self.monto_adeudado - total_abonos
            return max(saldo, 0)  # No puede ser negativo
        except:
            return self.monto_adeudado

    @property
    def porcentaje_pagado(self):
        """
        📈 Calcula qué porcentaje se ha pagado
        """
        if self.monto_adeudado > 0:
            try:
                from django.db.models import Sum
                total_abonos = self.abonos.aggregate(total=Sum('monto'))['total'] or 0
                return min((total_abonos / self.monto_adeudado) * 100, 100)
            except:
                return 0
        return 0

    @property
    def cantidad_abonos(self):
        """
        📊 Cuenta la cantidad de abonos realizados
        """
        try:
            return self.abonos.count()
        except:
            return 0

    @property
    def ultimo_abono(self):
        """
        🕐 Obtiene el último abono realizado
        """
        try:
            return self.abonos.order_by('-fecha_abono').first()
        except:
            return None

    @property
    def dias_sin_pagar(self):
        """
        📅 Calcula cuántos días han pasado sin pagar
        """
        from django.utils import timezone
        if not self.pagado:
            delta = timezone.now() - self.fecha_registro
            return delta.days
        return 0

    @property
    def estado_display(self):
        """
        🎨 Estado con formato bonito para templates
        """
        if self.pagado:
            return "✅ Pagado Completamente"
        elif self.saldo_pendiente < self.monto_adeudado:
            return f"💰 Abonado (${self.total_abonado:,.0f})"
        else:
            return "⏳ Sin Pagos"

    @property
    def clase_css_estado(self):
        """
        🎨 Clase CSS según el estado de la deuda
        """
        if self.pagado:
            return "success"
        elif self.saldo_pendiente < self.monto_adeudado:
            return "warning"
        elif self.dias_sin_pagar > 30:
            return "danger"
        else:
            return "info"

    def get_monto_formateado(self):
        """
        💰 Monto adeudado en formato colombiano
        """
        try:
            return f"${int(self.monto_adeudado):,}".replace(',', '.')
        except:
            return "$0"

    def get_saldo_formateado(self):
        """
        💰 Saldo pendiente en formato colombiano
        """
        try:
            return f"${int(self.saldo_pendiente):,}".replace(',', '.')
        except:
            return "$0"

    def get_total_abonado_formateado(self):
        """
        💰 Total abonado en formato colombiano
        """
        try:
            return f"${int(self.total_abonado):,}".replace(',', '.')
        except:
            return "$0"

    def puede_abonar(self, monto):
        """
        ✅ Verifica si se puede realizar un abono de cierto monto
        """
        from decimal import Decimal
        try:
            monto_decimal = Decimal(str(monto))
            return monto_decimal > 0 and monto_decimal <= self.saldo_pendiente
        except:
            return False

    def marcar_como_pagada_completa(self, usuario=None):
        """
        ✅ Marca la deuda como pagada y crea el abono faltante si es necesario
        
        IMPORTANTE: Este método NO crea MovimientoContable automáticamente.
        Eso se debe hacer desde la vista que llama este método.
        """
        if not self.pagado and self.saldo_pendiente > 0:
            try:
                # Crear abono por el saldo restante
                from .models import AbonoDeuda
                AbonoDeuda.objects.create(
                    deuda=self,
                    monto=self.saldo_pendiente,
                    metodo_pago='efectivo',
                    observaciones='Pago final - marcado como pagado por administrador',
                    registrado_por=usuario
                )
                
                # Marcar como pagada
                self.pagado = True
                self.save()
                
                return True
            except Exception as e:
                print(f"Error marcando deuda {self.id} como pagada: {e}")
                return False
        return False

    def clean(self):
        """
        🔧 Validaciones del modelo
        """
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # Validar monto adeudado
        if self.monto_adeudado is not None and self.monto_adeudado <= 0:
            errors['monto_adeudado'] = 'El monto adeudado debe ser mayor a cero.'
        
        # Validar nombre del cliente
        if not self.nombre_cliente or self.nombre_cliente.strip() == '':
            errors['nombre_cliente'] = 'El nombre del cliente es obligatorio.'
        
        # Validar teléfono (básico)
        if not self.telefono_cliente or self.telefono_cliente.strip() == '':
            errors['telefono_cliente'] = 'El teléfono del cliente es obligatorio.'
        
        if errors:
            raise ValidationError(errors)

    # 🔥 MÉTODO PARA DEBUGGING
    def debug_info(self):
        """
        🐛 Información de debugging para esta deuda
        """
        try:
            from django.db.models import Sum
            abonos = list(self.abonos.values('id', 'monto', 'fecha_abono', 'metodo_pago'))
            total_abonos_db = self.abonos.aggregate(total=Sum('monto'))['total'] or 0
            
            return {
                'id': self.id,
                'cliente': self.nombre_cliente,
                'monto_adeudado': float(self.monto_adeudado),
                'total_abonado_campo': float(self.total_abonado),
                'total_abonos_calculado': float(total_abonos_db),
                'saldo_pendiente': float(self.saldo_pendiente),
                'pagado': self.pagado,
                'cantidad_abonos': len(abonos),
                'abonos': abonos,
                'dias_sin_pagar': self.dias_sin_pagar,
                'estado': self.estado_display
            }
        except Exception as e:
            return {'error': str(e)}

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

# 🔥 1. MODELO DEVOLUCION - CORREGIDO CON RELACIÓN A FACTURAS
class Devolucion(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('autorizada', 'Autorizada'),
        ('rechazada', 'Rechazada'),
        ('procesada', 'Procesada'),
    ]
    
    TIPO_CHOICES = [
        ('cliente', 'Devolución de Cliente'),          # Cliente devuelve producto vendido
        ('inventario', 'Devolución de Inventario'),    # Producto malo del proveedor/dañado
        ('proveedor', 'Devolución a Proveedor'),       # 🔥 NUEVO: Devolver al proveedor
    ]
    
    RAZON_CHOICES = [
        # Para devoluciones de cliente
        ('defectuoso', 'Producto defectuoso'),
        ('no_conforme', 'Cliente no conforme'),
        ('vencido', 'Producto vencido'),
        ('equivocado', 'Producto equivocado'),
        
        # Para devoluciones de inventario
        ('llegada_malo', 'Llegó dañado del proveedor'),
        ('caducado', 'Producto caducado en inventario'),
        ('roto_almacen', 'Se rompió en almacén'),
        ('calidad_baja', 'Calidad no aceptable'),
        
        # 🔥 NUEVO: Para devoluciones a proveedor
        ('defecto_fabricacion', 'Defecto de fabricación'),
        ('fecha_vencida', 'Producto llegó vencido'),
        ('cantidad_incorrecta', 'Cantidad incorrecta en factura'),
        ('producto_incorrecto', 'Producto incorrecto enviado'),
        ('otro', 'Otro motivo'),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='cliente')
    razon = models.CharField(max_length=30, choices=RAZON_CHOICES, default='defectuoso')
    
    observaciones = models.TextField()
    solicitada_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devoluciones_solicitadas')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    autorizada_por = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='devoluciones_autorizadas')
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    fecha_procesamiento = models.DateTimeField(null=True, blank=True)
    comentario_admin = models.TextField(blank=True)
    
    # 🔥 CORREGIDO: Múltiples orígenes posibles
    venta_origen = models.ForeignKey('Venta', on_delete=models.SET_NULL, null=True, blank=True, 
                                   help_text="Venta de donde proviene el producto (devoluciones de cliente)")
    factura_origen = models.ForeignKey('FacturaCompra', on_delete=models.SET_NULL, null=True, blank=True,
                                     help_text="Factura de donde proviene el producto (devoluciones de inventario/proveedor)")
    
    # 🔥 NUEVO: Para tracking financiero
    valor_recuperado = models.DecimalField(max_digits=10, decimal_places=2, default=0, 
                                         help_text="Valor que se recupera al inventario")
    reembolso_cliente = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                          help_text="Dinero devuelto al cliente")
    nota_credito_proveedor = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                               help_text="Nota de crédito del proveedor")
    
    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = 'Devolución'
        verbose_name_plural = 'Devoluciones'

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        
        # Validar que tenga al menos un origen
        if not self.venta_origen and not self.factura_origen:
            errors['__all__'] = 'Debe especificar el origen de la devolución (venta o factura).'
        
        # Validar tipo vs origen
        if self.tipo == 'cliente' and not self.venta_origen:
            errors['venta_origen'] = 'Las devoluciones de cliente deben tener venta de origen.'
            
        if self.tipo in ['inventario', 'proveedor'] and not self.factura_origen:
            errors['factura_origen'] = 'Las devoluciones de inventario/proveedor deben tener factura de origen.'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.clean()
        
        # 🔥 PROCESAMIENTO AUTOMÁTICO MEJORADO
        if self.estado == 'procesada' and self.pk:
            devolucion_anterior = Devolucion.objects.filter(pk=self.pk).first()
            if devolucion_anterior and devolucion_anterior.estado != 'procesada':
                self._procesar_devolucion_mejorada()
        
        super().save(*args, **kwargs)

    def _procesar_devolucion_mejorada(self):
        """Procesa la devolución según su tipo con integración completa"""
        from django.utils import timezone
        
        self.fecha_procesamiento = timezone.now()
        
        if self.tipo == 'cliente':
            # DEVOLUCIÓN DE CLIENTE: Sumar al stock + registrar pérdida
            self.producto.cantidad += self.cantidad
            self.producto.save()
            
            # Calcular valores
            self.reembolso_cliente = self.producto.precio * self.cantidad
            self.valor_recuperado = self.producto.precio_costo * self.cantidad
            
            # Registrar movimientos contables
            MovimientoContable.objects.create(
                tipo='gasto',
                concepto=f'Reembolso cliente - {self.producto.nombre} (x{self.cantidad})',
                monto=self.reembolso_cliente,
                usuario=self.autorizada_por,
                fecha=timezone.now().date()
            )
            
            MovimientoContable.objects.create(
                tipo='ingreso',
                concepto=f'Recuperación inventario - {self.producto.nombre} (x{self.cantidad})',
                monto=self.valor_recuperado,
                usuario=self.autorizada_por,
                fecha=timezone.now().date()
            )
            
        elif self.tipo == 'inventario':
            # PÉRDIDA DE INVENTARIO: Solo registrar pérdida
            self.valor_recuperado = 0
            valor_perdido = self.producto.precio_costo * self.cantidad
            
            MovimientoContable.objects.create(
                tipo='gasto',
                concepto=f'Pérdida inventario - {self.producto.nombre} (x{self.cantidad}) - {self.get_razon_display()}',
                monto=valor_perdido,
                usuario=self.autorizada_por,
                fecha=timezone.now().date()
            )
            
        elif self.tipo == 'proveedor':
            # 🔥 NUEVO: DEVOLUCIÓN A PROVEEDOR
            # Restar del inventario actual
            if self.producto.cantidad >= self.cantidad:
                self.producto.cantidad -= self.cantidad
                self.producto.save()
                
                # Calcular nota de crédito esperada del proveedor
                if self.factura_origen:
                    # Buscar el precio en la factura original
                    detalle_factura = DetalleFacturaCompra.objects.filter(
                        factura=self.factura_origen,
                        producto=self.producto
                    ).first()
                    
                    if detalle_factura:
                        self.nota_credito_proveedor = detalle_factura.precio_unitario * self.cantidad
                    else:
                        self.nota_credito_proveedor = self.producto.precio_costo * self.cantidad
                else:
                    self.nota_credito_proveedor = self.producto.precio_costo * self.cantidad
                
                # Registrar como activo por cobrar al proveedor
                MovimientoContable.objects.create(
                    tipo='ingreso',
                    concepto=f'Nota crédito proveedor - {self.producto.nombre} (x{self.cantidad})',
                    monto=self.nota_credito_proveedor,
                    usuario=self.autorizada_por,
                    fecha=timezone.now().date()
                )

    @property
    def origen_display(self):
        """Muestra el origen de la devolución de forma amigable"""
        if self.venta_origen:
            return f"Venta Mesa {self.venta_origen.mesa.numero if self.venta_origen.mesa else 'N/A'} - {self.venta_origen.fecha.strftime('%d/%m/%Y')}"
        elif self.factura_origen:
            return f"Factura {self.factura_origen.numero_factura} - {self.factura_origen.proveedor.nombre}"
        return "Sin origen definido"

    @property
    def puede_procesar_a_proveedor(self):
        """Verifica si se puede devolver al proveedor"""
        if self.tipo != 'proveedor' or not self.factura_origen:
            return False
        
        # Verificar que la factura no sea muy antigua (ej: 30 días)
        from datetime import timedelta
        from django.utils import timezone
        
        limite_dias = timezone.now().date() - timedelta(days=30)
        return self.factura_origen.fecha_factura >= limite_dias

    def __str__(self):
        return f'Devolución {self.get_tipo_display()}: {self.producto.nombre} ({self.cantidad}) - {self.origen_display[:50]}'


# ========================================================================================
# 🧾 NUEVOS MODELOS DEL MÓDULO DE FACTURAS
# ========================================================================================

# 🏪 MODELO PROVEEDOR (DEBE IR PRIMERO)
class Proveedor(models.Model):
    """
    🏪 Proveedores para el sistema de facturas
    """
    nombre = models.CharField(max_length=200)
    nit = models.CharField(max_length=20, unique=True, help_text="NIT del proveedor")
    telefono = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    
    # Información adicional
    contacto_principal = models.CharField(max_length=100, blank=True)
    forma_pago_preferida = models.CharField(
        max_length=20,
        choices=[
            ('contado', 'Contado'),
            ('credito_15', 'Crédito 15 días'),
            ('credito_30', 'Crédito 30 días'),
            ('credito_45', 'Crédito 45 días'),
            ('credito_60', 'Crédito 60 días'),
        ],
        default='contado'
    )
    
    # Fechas
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} - {self.nit}"

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validar NIT
        if self.nit:
            # Limpiar NIT (solo números y guiones)
            self.nit = ''.join(c for c in self.nit if c.isdigit() or c == '-')
            
            if len(self.nit) < 8:
                raise ValidationError({'nit': 'El NIT debe tener al menos 8 caracteres.'})


# 🧾 MODELO FACTURA DE COMPRA (VA DESPUÉS DE PROVEEDOR)
class FacturaCompra(models.Model):
    """
    🧾 Facturas de compra a proveedores
    """
    ESTADO_CHOICES = [
        ('pendiente', '⏳ Pendiente'),
        ('recibida', '📦 Recibida'),
        ('pagada', '✅ Pagada'),
        ('anulada', '❌ Anulada'),
    ]
    
    TIPO_FACTURA_CHOICES = [
        ('compra', '🛒 Compra de Inventario'),
        ('servicio', '🔧 Servicio'),
        ('gasto', '💸 Gasto Operativo'),
    ]
    
    # Información básica
    numero_factura = models.CharField(max_length=50, unique=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
    tipo_factura = models.CharField(max_length=20, choices=TIPO_FACTURA_CHOICES, default='compra')
    
    # Fechas importantes
    fecha_factura = models.DateTimeField(help_text="Fecha y hora que aparece en la factura")
    fecha_vencimiento = models.DateField(help_text="Fecha límite de pago")
    fecha_registro = models.DateTimeField(auto_now_add=True, help_text="Cuándo se registró en el sistema")
    fecha_recepcion = models.DateTimeField(null=True, blank=True, help_text="Cuándo se recibió la mercancía")
    fecha_pago = models.DateTimeField(null=True, blank=True, help_text="Cuándo se pagó")
    
    # Valores monetarios
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Estado y control
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True)
    
    # Archivos
    archivo_factura = models.FileField(
        upload_to='facturas/compras/',
        blank=True,
        null=True,
        help_text="PDF o imagen de la factura"
    )
    
    # Control interno
    registrada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='facturas_registradas')
    recibida_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='facturas_recibidas')
    pagada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='facturas_pagadas')
    
    # Campo para tracking de inventario
    inventario_actualizado = models.BooleanField(default=False, help_text="Si ya se sumó al inventario")
    movimiento_contable_creado = models.BooleanField(default=False, help_text="Si ya se registró en contabilidad")
    
    class Meta:
        verbose_name = 'Factura de Compra'
        verbose_name_plural = 'Facturas de Compra'
        ordering = ['-fecha_factura', '-fecha_registro']
        
    def __str__(self):
        return f"Factura {self.numero_factura} - {self.proveedor.nombre} - ${self.total:,.0f}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from decimal import Decimal
        
        errors = {}
        
        # 🔧 CORRECCIÓN: Validar fechas manejando diferentes tipos
        if self.fecha_vencimiento and self.fecha_factura:
            # Convertir fecha_factura (DateTimeField) a fecha (DateField) para comparar
            if hasattr(self.fecha_factura, 'date'):
                fecha_factura_date = self.fecha_factura.date()
            else:
                fecha_factura_date = self.fecha_factura
                
            # fecha_vencimiento ya es DateField, pero por seguridad:
            if hasattr(self.fecha_vencimiento, 'date'):
                fecha_vencimiento_date = self.fecha_vencimiento.date()
            else:
                fecha_vencimiento_date = self.fecha_vencimiento
            
            # Ahora sí podemos comparar
            if fecha_vencimiento_date < fecha_factura_date:
                errors['fecha_vencimiento'] = 'La fecha de vencimiento no puede ser anterior a la fecha de factura.'
        
        # Validar valores monetarios
        if self.total and self.total <= 0:
            errors['total'] = 'El total debe ser mayor a cero.'
        
        if self.iva and self.iva < 0:
            errors['iva'] = 'El IVA no puede ser negativo.'
        
        if self.descuento and self.descuento < 0:
            errors['descuento'] = 'El descuento no puede ser negativo.'
        
        # Validar que el total sea coherente
        if all([self.subtotal, self.iva, self.descuento, self.total]):
            total_calculado = self.subtotal + self.iva - self.descuento
            if abs(total_calculado - self.total) > Decimal('0.01'):
                errors['total'] = f'El total no coincide. Calculado: ${total_calculado:,.2f}'
        
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Ejecutar validaciones
        self.clean()
        
        # Generar número de factura automático si no existe
        if not self.numero_factura:
            from datetime import datetime
            año_actual = datetime.now().year
            último_número = FacturaCompra.objects.filter(
                numero_factura__startswith=f'FC{año_actual}'
            ).count() + 1
            self.numero_factura = f'FC{año_actual}-{último_número:04d}'
        
        # Calcular fecha de vencimiento automática si no se especifica
        if not self.fecha_vencimiento and self.fecha_factura and self.proveedor:
            from datetime import timedelta
            dias_credito = {
                'contado': 0,
                'credito_15': 15,
                'credito_30': 30,
                'credito_45': 45,
                'credito_60': 60,
            }
            dias = dias_credito.get(self.proveedor.forma_pago_preferida, 0)
            self.fecha_vencimiento = self.fecha_factura + timedelta(days=dias)
        
        # Marcar fechas de cambio de estado
        if self.pk:
            try:
                factura_anterior = FacturaCompra.objects.get(pk=self.pk)
                
                # Si cambió a recibida
                if factura_anterior.estado != 'recibida' and self.estado == 'recibida':
                    if not self.fecha_recepcion:
                        self.fecha_recepcion = timezone.now()
                
                # Si cambió a pagada
                if factura_anterior.estado != 'pagada' and self.estado == 'pagada':
                    if not self.fecha_pago:
                        self.fecha_pago = timezone.now()
                        
            except FacturaCompra.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
        
        # Procesos automáticos post-guardado
        self._procesar_estados()

    def _procesar_estados(self):
        """
        Procesa automáticamente los cambios de estado
        """
        try:
            # Si la factura está recibida y es de compra, actualizar inventario
            if (self.estado == 'recibida' and 
                self.tipo_factura == 'compra' and 
                not self.inventario_actualizado):
                self._actualizar_inventario()
            
            # Si la factura está pagada, crear movimiento contable
            if (self.estado == 'pagada' and 
                not self.movimiento_contable_creado):
                self._crear_movimiento_contable()
                
        except Exception as e:
            print(f"Error procesando estados de factura {self.id}: {e}")

    def _actualizar_inventario(self):
        """
        Actualiza el inventario basado en los detalles de la factura
        """
        try:
            for detalle in self.detalles.all():
                if detalle.producto:
                    # Sumar al inventario
                    detalle.producto.cantidad += detalle.cantidad
                    detalle.producto.save()
            
            # Marcar como actualizado
            self.inventario_actualizado = True
            super().save(update_fields=['inventario_actualizado'])
            
        except Exception as e:
            print(f"Error actualizando inventario para factura {self.id}: {e}")

    def _crear_movimiento_contable(self):
        """
        Crea el movimiento contable correspondiente
        """
        try:
            # Determinar tipo de movimiento según tipo de factura
            if self.tipo_factura == 'compra':
                tipo_movimiento = 'costo'  # Inversión en inventario
                concepto = f'Compra de inventario - Factura {self.numero_factura} - {self.proveedor.nombre}'
            elif self.tipo_factura == 'gasto':
                tipo_movimiento = 'gasto'  # Gasto operativo
                concepto = f'Gasto operativo - Factura {self.numero_factura} - {self.proveedor.nombre}'
            else:  # servicio
                tipo_movimiento = 'gasto'  # Servicios como gastos
                concepto = f'Servicio - Factura {self.numero_factura} - {self.proveedor.nombre}'
            
            # Crear movimiento contable
            MovimientoContable.objects.create(
                tipo=tipo_movimiento,
                concepto=concepto,
                monto=self.total,
                usuario=self.pagada_por,
                fecha=self.fecha_pago.date() if self.fecha_pago else timezone.now().date()
            )
            
            # Marcar como creado
            self.movimiento_contable_creado = True
            super().save(update_fields=['movimiento_contable_creado'])
            
        except Exception as e:
            print(f"Error creando movimiento contable para factura {self.id}: {e}")

    # Métodos utilitarios
    def get_total_formateado(self):
        """Retorna el total en formato colombiano"""
        try:
            return f"${int(self.total):,}".replace(',', '.')
        except:
            return "$0"

    def dias_vencimiento(self):
        """Calcula días hasta vencimiento (negativo si ya venció)"""
        from datetime import date
        if self.fecha_vencimiento:
            delta = self.fecha_vencimiento - date.today()
            return delta.days
        return 0

    def esta_vencida(self):
        """Retorna True si la factura está vencida"""
        return self.dias_vencimiento() < 0 and self.estado not in ['pagada', 'anulada']

    def get_color_estado(self):
        """Retorna color CSS según estado"""
        colores = {
            'pendiente': 'warning',
            'recibida': 'info',
            'pagada': 'success',
            'anulada': 'danger',
        }
        return colores.get(self.estado, 'secondary')

    def _recalcular_totales(self):
        """
        Recalcula los totales de la factura basándose en sus detalles
        """
        from django.db.models import Sum
        from decimal import Decimal
        total_detalles = self.detalles.aggregate(
            subtotal=Sum('subtotal')
        )['subtotal'] or Decimal('0.00')
        
        self.subtotal = total_detalles
        self.total = self.subtotal + self.iva - self.descuento
        self.save(update_fields=['subtotal', 'total'])


# 📋 MODELO DETALLE FACTURA (VA DESPUÉS DE FACTURA)
class DetalleFacturaCompra(models.Model):
    """
    📋 Detalles de productos en facturas de compra - MEJORADO
    """
    factura = models.ForeignKey(FacturaCompra, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Información del producto (preservada aunque se elimine el producto)
    nombre_producto = models.CharField(max_length=200)
    codigo_producto = models.CharField(max_length=50, blank=True, help_text="SKU o código del proveedor")
    
    # Cantidades y precios
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    # 🔥 NUEVO: Control de aplicación al inventario
    aplicado_inventario = models.BooleanField(default=False)
    fecha_aplicacion = models.DateTimeField(null=True, blank=True)
    cantidad_devuelta = models.PositiveIntegerField(default=0, help_text="Cantidad devuelta al proveedor")
    
    # Información adicional
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Detalle de Factura'
        verbose_name_plural = 'Detalles de Factura'
    
    def aplicar_a_inventario(self, usuario=None):
        """
        Aplica este detalle al inventario y crea el registro de tracking
        """
        if self.aplicado_inventario:
            return False, "Ya fue aplicado al inventario"
        
        try:
            from django.utils import timezone
            
            if self.producto:
                # Actualizar producto existente
                cantidad_anterior = self.producto.cantidad
                self.producto.cantidad += self.cantidad
                
                # Actualizar precio costo con promedio ponderado
                if self.producto.precio_costo > 0 and cantidad_anterior > 0:
                    nuevo_costo = ((self.producto.precio_costo * cantidad_anterior) + 
                                 (self.precio_unitario * self.cantidad)) / self.producto.cantidad
                    self.producto.precio_costo = nuevo_costo
                else:
                    self.producto.precio_costo = self.precio_unitario
                
                self.producto.save()
                
                # Crear registro de tracking
                InventarioFactura.objects.create(
                    producto=self.producto,
                    factura=self.factura,
                    cantidad_recibida=self.cantidad,
                    cantidad_actual=self.cantidad,
                    precio_costo_unitario=self.precio_unitario
                )
                
            else:
                # Crear producto nuevo
                nuevo_producto = Producto.objects.create(
                    nombre=self.nombre_producto,
                    precio_costo=self.precio_unitario,
                    precio=self.precio_unitario * Decimal('1.6'),  # Margen 60%
                    cantidad=self.cantidad,
                    categoria=None
                )
                
                # Vincular producto con el detalle
                self.producto = nuevo_producto
                
                # Crear registro de tracking
                InventarioFactura.objects.create(
                    producto=nuevo_producto,
                    factura=self.factura,
                    cantidad_recibida=self.cantidad,
                    cantidad_actual=self.cantidad,
                    precio_costo_unitario=self.precio_unitario
                )
            
            # Marcar como aplicado
            self.aplicado_inventario = True
            self.fecha_aplicacion = timezone.now()
            self.save()
            
            # Registrar movimiento contable
            MovimientoContable.objects.create(
                tipo='costo',
                concepto=f'Inventario - {self.nombre_producto} (Factura {self.factura.numero_factura})',
                monto=self.subtotal,
                usuario=usuario
            )
            
            return True, "Aplicado correctamente al inventario"
            
        except Exception as e:
            return False, f"Error: {str(e)}"

    @property
    def puede_devolver_proveedor(self):
        """Verifica si se puede devolver parte de este producto al proveedor"""
        return (self.aplicado_inventario and 
                self.producto and 
                self.producto.cantidad > 0 and
                self.cantidad_devuelta < self.cantidad)

    @property
    def cantidad_disponible_devolucion(self):
        """Cantidad máxima que se puede devolver de este detalle"""
        if not self.puede_devolver_proveedor:
            return 0
        
        # La menor cantidad entre: lo que queda por devolver y el stock actual
        max_por_devolver = self.cantidad - self.cantidad_devuelta
        stock_actual = self.producto.cantidad if self.producto else 0
        
        return min(max_por_devolver, stock_actual)

    def __str__(self):
        aplicado = "✅" if self.aplicado_inventario else "⏳"
        return f"{aplicado} {self.cantidad} x {self.nombre_producto} = ${self.subtotal:,.0f}"


# 💰 MODELO PAGO FACTURA (VA AL FINAL)
class PagoFactura(models.Model):
    """
    💰 Pagos realizados a facturas (para pagos parciales)
    """
    factura = models.ForeignKey(FacturaCompra, on_delete=models.CASCADE, related_name='pagos')
    fecha_pago = models.DateTimeField(default=timezone.now)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(
        max_length=20,
        choices=[
            ('efectivo', 'Efectivo'),
            ('transferencia', 'Transferencia'),
            ('cheque', 'Cheque'),
            ('tarjeta', 'Tarjeta'),
        ],
        default='transferencia'
    )
    referencia = models.CharField(max_length=100, blank=True, help_text="Número de cheque, referencia de transferencia, etc.")
    observaciones = models.TextField(blank=True)
    registrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'Pago de Factura'
        verbose_name_plural = 'Pagos de Facturas'
        ordering = ['-fecha_pago']
    
    def __str__(self):
        return f"Pago ${self.monto:,.0f} - Factura {self.factura.numero_factura}"

    def get_monto_formateado(self):
        """Retorna el monto en formato colombiano"""
        try:
            return f"${int(self.monto):,}".replace(',', '.')
        except:
            return "$0"
        

        
        # ========================================================================================
# 💰 MODELO PARA ABONOS DE DEUDAS - Agregar al final de tu models.py
# ========================================================================================

class AbonoDeuda(models.Model):
    """
    💰 Modelo para registrar abonos parciales a las deudas
    
    Features:
    - Múltiples abonos por deuda
    - Diferentes métodos de pago
    - Tracking de quien registra cada abono
    - Observaciones para cada pago
    """
    
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('tarjeta', 'Tarjeta'),
    ]
    
    deuda = models.ForeignKey(
        'Deuda', 
        on_delete=models.CASCADE, 
        related_name='abonos',
        verbose_name='Deuda'
    )
    monto = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name='Monto del Abono'
    )
    metodo_pago = models.CharField(
        max_length=20, 
        choices=METODO_PAGO_CHOICES,
        default='efectivo',
        verbose_name='Método de Pago'
    )
    observaciones = models.TextField(
        blank=True, 
        null=True,
        verbose_name='Observaciones'
    )
    fecha_abono = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha del Abono'
    )
    registrado_por = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        verbose_name='Registrado por'
    )
    
    class Meta:
        verbose_name = 'Abono de Deuda'
        verbose_name_plural = 'Abonos de Deudas'
        ordering = ['-fecha_abono']
    
    def __str__(self):
        return f"Abono ${self.monto} - {self.deuda.nombre_cliente} ({self.fecha_abono.strftime('%d/%m/%Y')})"
    
    def save(self, *args, **kwargs):
        """
        🔧 Override del save para validaciones automáticas
        """
        from decimal import Decimal
        
        # ✅ VALIDAR QUE EL MONTO SEA POSITIVO
        if self.monto <= 0:
            raise ValueError("El monto del abono debe ser mayor a cero")
        
        # ✅ VALIDAR QUE NO SUPERE LA DEUDA
        abonos_previos = AbonoDeuda.objects.filter(deuda=self.deuda).aggregate(
            total=models.Sum('monto')
        )['total'] or Decimal('0.00')
        
        # Si es una actualización, excluir el abono actual
        if self.pk:
            abonos_previos -= AbonoDeuda.objects.get(pk=self.pk).monto
        
        if (abonos_previos + self.monto) > self.deuda.monto_adeudado:
            raise ValueError("El abono supera el monto adeudado")
        
        super().save(*args, **kwargs)
    
    @property
    def porcentaje_del_total(self):
        """
        📈 Qué porcentaje representa este abono del total de la deuda
        """
        if self.deuda.monto_adeudado > 0:
            return (self.monto / self.deuda.monto_adeudado) * 100
        return 0
    
    def get_metodo_pago_display_emoji(self):
        """
        😊 Método de pago con emoji
        """
        emojis = {
            'efectivo': '💵 Efectivo',
            'transferencia': '🏦 Transferencia',
            'tarjeta': '💳 Tarjeta',
        }
        return emojis.get(self.metodo_pago, self.get_metodo_pago_display())
    # ========================================================================================
# 🎁 SISTEMA DE PRODUCTOS COMBINADOS/PROMOS PARA BAR
# ========================================================================================
# Agregar estos modelos al final de tu models.py existente

class ProductoCombinado(models.Model):
    """
    🎁 Productos combinados/promociones para bar
    
    Ejemplos:
    - "Promo 2x1 Cervezas"
    - "Combo Whisky + Hielo + Mezclador"
    - "Pack 6 Cervezas con descuento"
    """
    
    TIPO_COMBO_CHOICES = [
        ('combo', '🎁 Combo Fijo'),           # Productos específicos juntos
        ('promocion', '🏷️ Promoción'),        # Descuentos especiales
        ('pack', '📦 Pack Cantidad'),         # Múltiples unidades del mismo producto
    ]
    
    nombre = models.CharField(
        max_length=150, 
        help_text="Ej: 'Promo 2x1 Cervezas', 'Combo Whisky Completo'"
    )
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción detallada de la promoción"
    )
    tipo_combo = models.CharField(
        max_length=20, 
        choices=TIPO_COMBO_CHOICES, 
        default='combo'
    )
    precio_combo = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Precio especial del combo"
    )
    imagen = models.ImageField(
        upload_to='combos/',
        blank=True,
        null=True,
        help_text="Imagen promocional del combo"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Si está disponible para venta"
    )
    
    # Información de promoción
    descuento_porcentaje = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        help_text="Porcentaje de descuento (0-100)"
    )
    fecha_inicio = models.DateField(
        null=True, 
        blank=True,
        help_text="Fecha de inicio de la promoción"
    )
    fecha_fin = models.DateField(
        null=True, 
        blank=True,
        help_text="Fecha de fin de la promoción"
    )
    
    # Control interno
    creado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='combos_creados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Producto Combinado'
        verbose_name_plural = 'Productos Combinados'
        ordering = ['-activo', '-fecha_creacion']
    
    def __str__(self):
        estado = "✅" if self.activo else "❌"
        imagen_indicator = " 📷" if self.tiene_imagen() else ""
        return f"{estado} {self.nombre} - ${self.precio_combo:,.0f}{imagen_indicator}"
    
    @property
    def precio_individual_total(self):
        """
        💰 Suma de precios individuales de todos los componentes
        """
        from decimal import Decimal
        total = Decimal('0.00')
        
        for componente in self.componentes.all():
            total += (componente.producto.precio * componente.cantidad)
        
        return total
    
    @property
    def descuento_absoluto(self):
        """
        💵 Descuento en pesos que ofrece el combo
        """
        return self.precio_individual_total - self.precio_combo
    
    @property
    def porcentaje_descuento_real(self):
        """
        📊 Porcentaje real de descuento calculado
        """
        if self.precio_individual_total > 0:
            return ((self.precio_individual_total - self.precio_combo) / self.precio_individual_total) * 100
        return 0
    
    @property
    def tiene_stock_disponible(self):
        """
        📦 Verifica si todos los componentes tienen stock suficiente
        """
        for componente in self.componentes.all():
            if componente.producto.cantidad < componente.cantidad:
                return False
        return True
    
    @property
    def stock_limitante(self):
        """
        🚨 Producto que limita el stock del combo
        """
        stock_minimo = float('inf')
        producto_limitante = None
        
        for componente in self.componentes.all():
            stock_posible = componente.producto.cantidad // componente.cantidad
            if stock_posible < stock_minimo:
                stock_minimo = stock_posible
                producto_limitante = componente.producto
        
        return {
            'producto': producto_limitante,
            'cantidad_maxima_combos': int(stock_minimo) if stock_minimo != float('inf') else 0
        }
    
    @property
    def esta_vigente(self):
        """
        📅 Verifica si la promoción está vigente por fechas
        """
        from django.utils import timezone
        hoy = timezone.now().date()
        
        if self.fecha_inicio and hoy < self.fecha_inicio:
            return False
        if self.fecha_fin and hoy > self.fecha_fin:
            return False
        return True
    
    @property
    def componentes_info(self):
        """
        📋 Información resumida de componentes para templates
        """
        componentes = []
        for comp in self.componentes.all():
            componentes.append({
                'producto': comp.producto,
                'cantidad': comp.cantidad,
                'subtotal': comp.producto.precio * comp.cantidad,
                'tiene_stock': comp.producto.cantidad >= comp.cantidad
            })
        return componentes
    
    def get_precio_formateado(self):
        """
        💰 Precio del combo en formato colombiano
        """
        try:
            return f"${int(self.precio_combo):,}".replace(',', '.')
        except:
            return "$0"
    
    def get_descuento_formateado(self):
        """
        💵 Descuento en formato colombiano
        """
        try:
            descuento = self.descuento_absoluto
            return f"${int(descuento):,}".replace(',', '.')
        except:
            return "$0"
    
    def get_imagen_url(self):
        """
        🖼️ URL de imagen o placeholder
        """
        if self.imagen:
            return self.imagen.url
        else:
            return '/static/images/combo-placeholder.jpg'
    
    def tiene_imagen(self):
        """
        📷 Verificar si tiene imagen
        """
        return bool(self.imagen)
    
    def redimensionar_imagen(self):
        """
        Redimensiona la imagen automáticamente para optimizar espacio
        Tamaño objetivo: máximo 800x600px manteniendo proporción
        """
        try:
            from PIL import Image
            import os
            
            # Abrir la imagen
            img_path = self.imagen.path
            
            if os.path.exists(img_path):
                with Image.open(img_path) as img:
                    # Convertir a RGB si es necesario (para JPEGs)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    # Redimensionar manteniendo proporción
                    max_size = (800, 600)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    # Guardar la imagen redimensionada
                    img.save(img_path, 'JPEG', quality=85, optimize=True)
                    
        except Exception as e:
            print(f"Error redimensionando imagen para combo {self.id}: {e}")
            # No lanzar excepción para no interrumpir el guardado
    
    def delete_old_image(self, old_image_path):
        """
        Elimina la imagen anterior cuando se actualiza el combo
        """
        try:
            if old_image_path and os.path.exists(old_image_path):
                os.remove(old_image_path)
        except Exception as e:
            print(f"Error eliminando imagen anterior: {e}")
    
    def clean(self):
        """
        🔧 Validaciones del modelo incluyendo imagen
        """
        from django.core.exceptions import ValidationError
        import os
        
        errors = {}
        
        # Validar precio
        if self.precio_combo <= 0:
            errors['precio_combo'] = 'El precio del combo debe ser mayor a cero.'
        
        # Validar fechas
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin < self.fecha_inicio:
                errors['fecha_fin'] = 'La fecha de fin no puede ser anterior a la fecha de inicio.'
        
        # Validar descuento porcentaje
        if self.descuento_porcentaje < 0 or self.descuento_porcentaje > 100:
            errors['descuento_porcentaje'] = 'El descuento debe estar entre 0 y 100%.'
        
        # Validación de imagen
        if self.imagen:
            # Validar tamaño del archivo (máximo 5MB)
            if self.imagen.size > 5 * 1024 * 1024:
                errors['imagen'] = 'La imagen es demasiado grande. Máximo permitido: 5MB.'
            
            # Validar extensión
            extensiones_validas = ['.jpg', '.jpeg', '.png', '.webp']
            extension = os.path.splitext(self.imagen.name)[1].lower()
            
            if extension not in extensiones_validas:
                errors['imagen'] = f'Formato de imagen no válido. Permitidos: {", ".join(extensiones_validas)}'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        # Guardar imagen anterior para poder eliminarla si se cambia
        old_image_path = None
        if self.pk:
            try:
                old_combo = ProductoCombinado.objects.get(pk=self.pk)
                if old_combo.imagen and old_combo.imagen != self.imagen:
                    old_image_path = old_combo.imagen.path
            except ProductoCombinado.DoesNotExist:
                pass
        
        # Ejecutar validaciones
        self.clean()
        
        # Guardar primero para obtener la ruta del archivo
        super().save(*args, **kwargs)
        
        # Redimensionar imagen si existe
        if self.imagen:
            self.redimensionar_imagen()
        
        # Eliminar imagen anterior si cambió
        if old_image_path and self.imagen and old_image_path != self.imagen.path:
            self.delete_old_image(old_image_path)
            
class ComponenteCombo(models.Model):
    """
    📋 Componentes que forman un producto combinado
    
    Ejemplo: Para "Combo Whisky Completo"
    - Whisky Jack Daniels x1
    - Hielo x1  
    - Coca Cola x1
    """
    
    combo = models.ForeignKey(
        ProductoCombinado, 
        on_delete=models.CASCADE, 
        related_name='componentes'
    )
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE,
        help_text="Producto que forma parte del combo"
    )
    cantidad = models.PositiveIntegerField(
        default=1,
        help_text="Cantidad de este producto en el combo"
    )
    
    # Información adicional
    es_opcional = models.BooleanField(
        default=False,
        help_text="Si el cliente puede omitir este componente"
    )
    observaciones = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Notas especiales del componente"
    )
    
    class Meta:
        verbose_name = 'Componente de Combo'
        verbose_name_plural = 'Componentes de Combo'
        unique_together = ['combo', 'producto']  # Un producto solo una vez por combo
    
    def __str__(self):
        opcional = " (Opcional)" if self.es_opcional else ""
        return f"{self.cantidad}x {self.producto.nombre}{opcional}"
    
    @property
    def subtotal(self):
        """
        💰 Subtotal del componente (precio x cantidad)
        """
        return self.producto.precio * self.cantidad
    
    @property
    def tiene_stock_suficiente(self):
        """
        📦 Verifica si hay stock suficiente para este componente
        """
        return self.producto.cantidad >= self.cantidad
    
    @property
    def stock_disponible_combos(self):
        """
        📊 Cuántos combos se pueden hacer con el stock de este producto
        """
        return self.producto.cantidad // self.cantidad if self.cantidad > 0 else 0
    
    def get_subtotal_formateado(self):
        """
        💰 Subtotal en formato colombiano
        """
        try:
            return f"${int(self.subtotal):,}".replace(',', '.')
        except:
            return "$0"
    
    def clean(self):
        """
        🔧 Validaciones del modelo
        """
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # Validar cantidad
        if self.cantidad <= 0:
            errors['cantidad'] = 'La cantidad debe ser mayor a cero.'
        
        # Validar que no se agregue el mismo producto dos veces
        if self.combo_id and self.producto_id:
            componentes_existentes = ComponenteCombo.objects.filter(
                combo=self.combo,
                producto=self.producto
            )
            
            # Si es edición, excluir el actual
            if self.pk:
                componentes_existentes = componentes_existentes.exclude(pk=self.pk)
            
            if componentes_existentes.exists():
                errors['producto'] = 'Este producto ya está en el combo. Edita la cantidad en lugar de agregarlo nuevamente.'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class VentaCombo(models.Model):
    """
    🛒 Registro de ventas de combos (para tracking y estadísticas)
    """
    venta = models.ForeignKey(
        'Venta', 
        on_delete=models.CASCADE, 
        related_name='combos_vendidos'
    )
    combo = models.ForeignKey(
        ProductoCombinado, 
        on_delete=models.CASCADE,
        related_name='ventas_realizadas'
    )
    cantidad_vendida = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Precio al que se vendió (puede diferir del precio actual)"
    )
    
    class Meta:
        verbose_name = 'Venta de Combo'
        verbose_name_plural = 'Ventas de Combos'
    
    def __str__(self):
        return f"Venta: {self.cantidad_vendida}x {self.combo.nombre}"
    
    @property
    def subtotal(self):
        """
        💰 Subtotal de esta venta de combo
        """
        return self.cantidad_vendida * self.precio_unitario
    
    def get_subtotal_formateado(self):
        """
        💰 Subtotal en formato colombiano
        """
        try:
            return f"${int(self.subtotal):,}".replace(',', '.')
        except:
            return "$0"
        
        # 🔥 2. MODELO AUXILIAR PARA TRACKING DE INVENTARIO POR FACTURA
class InventarioFactura(models.Model):
    """
    Tracking de qué productos vinieron de qué facturas
    Para mejor control de devoluciones y análisis de costos
    """
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='historiales_factura')
    factura = models.ForeignKey(FacturaCompra, on_delete=models.CASCADE, related_name='inventarios_generados')
    cantidad_recibida = models.PositiveIntegerField(help_text="Cantidad que se agregó al inventario")
    cantidad_actual = models.PositiveIntegerField(help_text="Cantidad que queda de esta factura")
    precio_costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    
    # Control de devoluciones
    cantidad_devuelta_cliente = models.PositiveIntegerField(default=0)
    cantidad_devuelta_proveedor = models.PositiveIntegerField(default=0)
    cantidad_perdida = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Inventario por Factura'
        verbose_name_plural = 'Inventarios por Factura'
        ordering = ['-fecha_ingreso']
    
    def __str__(self):
        return f"{self.producto.nombre} - Factura {self.factura.numero_factura} ({self.cantidad_actual}/{self.cantidad_recibida})"

    @property
    def porcentaje_usado(self):
        """Porcentaje del lote que ya se ha usado/vendido"""
        if self.cantidad_recibida > 0:
            usado = self.cantidad_recibida - self.cantidad_actual
            return (usado / self.cantidad_recibida) * 100
        return 0

    @property
    def valor_inventario_actual(self):
        """Valor del inventario restante de esta factura"""
        return self.cantidad_actual * self.precio_costo_unitario

