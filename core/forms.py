# 🔥 FORMS.PY SIN REGISTRO PÚBLICO - Solo admin puede crear usuarios

from datetime import timezone
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
import re
# Al inicio de forms.py, agregar:
from datetime import timedelta
from django.utils import timezone

# 🔥 IMPORTS DE MODELOS - AGREGAR LOS QUE FALTEN
from .models import (
    Gasto, 
    PagoBartender, 
    Devolucion, 
    Producto, 
    Categoria, 
    Mesa,
    Venta,  # 🔥 ESTE ES EL QUE FALTA
    # Agregar otros modelos que uses en forms.py
)
# ========================================================================================
# FORMULARIO DE PRODUCTOS (Con validaciones críticas)
# ========================================================================================

class ProductoForm(forms.ModelForm):
    # 🔥 NUEVO CAMPO: Previsualización de imagen actual
    imagen_actual = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    # 🔥 NUEVO CAMPO: Checkbox para eliminar imagen
    eliminar_imagen = forms.BooleanField(
        required=False,
        label="Eliminar imagen actual",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'descripcion', 'precio_costo', 'precio', 'cantidad', 'imagen']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del producto'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3, 
                'placeholder': 'Descripción opcional'
            }),
            'precio_costo': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01', 
                'placeholder': '0.00',
                'min': '0'
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01', 
                'placeholder': '0.00',
                'min': '0.01'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cantidad inicial',
                'min': '0'
            }),
            # 🔥 NUEVO WIDGET: Input de imagen con atributos personalizados
            'imagen': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'id': 'id_imagen',
                'onchange': 'previewImage(this)'
            })
        }
        labels = {
            'precio_costo': 'Precio de Costo (COP)',
            'precio': 'Precio de Venta (COP)',
            'cantidad': 'Cantidad en Stock',
            'imagen': 'Imagen del Producto'
        }
        help_texts = {
            'imagen': 'Formatos permitidos: JPG, JPEG, PNG, WEBP. Tamaño máximo: 5MB. Se redimensionará automáticamente.'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 🔥 CONFIGURAR CAMPO DE ELIMINACIÓN SOLO PARA EDICIÓN
        if self.instance and self.instance.pk and self.instance.imagen:
            self.fields['eliminar_imagen'].widget.attrs.update({
                'id': 'id_eliminar_imagen',
                'onchange': 'toggleImageInput(this)'
            })
        else:
            # Si no hay imagen actual, ocultar el checkbox
            self.fields['eliminar_imagen'].widget = forms.HiddenInput()

    # 🔥 NUEVA VALIDACIÓN: Imagen
    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        eliminar_imagen = self.cleaned_data.get('eliminar_imagen', False)
        
        # Si se marcó eliminar imagen, no validar la nueva imagen
        if eliminar_imagen:
            return None
        
        if imagen:
            # Validar tamaño (5MB máximo)
            if imagen.size > 5 * 1024 * 1024:
                raise ValidationError('La imagen es demasiado grande. Máximo permitido: 5MB.')
            
            # Validar tipo de archivo
            import os
            from PIL import Image
            
            # Verificar extensión
            extensiones_validas = ['.jpg', '.jpeg', '.png', '.webp']
            nombre_archivo = imagen.name.lower()
            extension = os.path.splitext(nombre_archivo)[1]
            
            if extension not in extensiones_validas:
                raise ValidationError(
                    f'Formato de imagen no válido. Formatos permitidos: {", ".join(extensiones_validas)}'
                )
            
            # 🔥 VALIDACIÓN AVANZADA: Verificar que realmente sea una imagen
            try:
                # Intentar abrir la imagen con PIL
                img = Image.open(imagen)
                img.verify()  # Verificar que no esté corrupta
                
                # Verificar dimensiones mínimas
                if img.width < 50 or img.height < 50:
                    raise ValidationError('La imagen es demasiado pequeña. Dimensiones mínimas: 50x50px.')
                
                # Verificar dimensiones máximas (antes de redimensionar)
                if img.width > 4000 or img.height > 4000:
                    raise ValidationError('La imagen es demasiado grande. Dimensiones máximas: 4000x4000px.')
                
            except Exception as e:
                raise ValidationError('El archivo no es una imagen válida o está corrupto.')
            
            # Resetear el puntero del archivo después de verify()
            imagen.seek(0)
        
        return imagen

    # Validaciones existentes...
    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        
        if precio is None:
            raise ValidationError('El precio de venta es obligatorio.')
        
        try:
            precio = Decimal(str(precio))
        except (InvalidOperation, ValueError):
            raise ValidationError('El precio de venta debe ser un número válido.')
        
        if precio <= 0:
            raise ValidationError('El precio de venta debe ser mayor a cero.')
        
        if precio > 99999999:
            raise ValidationError('El precio de venta es demasiado alto.')
        
        return precio

    def clean_precio_costo(self):
        precio_costo = self.cleaned_data.get('precio_costo')
        
        if precio_costo is None:
            return Decimal('0.00')
        
        try:
            precio_costo = Decimal(str(precio_costo))
        except (InvalidOperation, ValueError):
            raise ValidationError('El precio de costo debe ser un número válido.')
        
        if precio_costo < 0:
            raise ValidationError('El precio de costo no puede ser negativo.')
        
        return precio_costo

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        
        if cantidad is None:
            raise ValidationError('La cantidad es obligatoria.')
        
        if cantidad < 0:
            raise ValidationError('La cantidad no puede ser negativa.')
        
        if cantidad > 999999:
            raise ValidationError('La cantidad es demasiado alta (máximo: 999.999).')
        
        return cantidad

    def clean(self):
        cleaned_data = super().clean()
        precio_costo = cleaned_data.get('precio_costo')
        precio_venta = cleaned_data.get('precio')
        eliminar_imagen = cleaned_data.get('eliminar_imagen', False)
        
        # Validaciones de precios existentes
        if precio_costo and precio_venta:
            if precio_costo > 0 and precio_venta > 0:
                if precio_costo >= precio_venta:
                    raise ValidationError({
                        'precio_costo': 'El precio de costo debe ser menor al precio de venta.',
                        'precio': 'El precio de venta debe ser mayor al precio de costo.'
                    })
                
                margen = ((precio_venta - precio_costo) / precio_costo) * 100
                if margen < 5:
                    raise ValidationError({
                        'precio': f'El margen de ganancia es muy bajo ({margen:.1f}%). Se recomienda al menos 5%.'
                    })
        
        # 🔥 MANEJO ESPECIAL: Si se marcó eliminar imagen
        if eliminar_imagen:
            cleaned_data['imagen'] = None
        
        return cleaned_data

    # 🔥 NUEVO MÉTODO: Guardar con manejo especial de imagen
    def save(self, commit=True):
        instance = super().save(commit=False)
        eliminar_imagen = self.cleaned_data.get('eliminar_imagen', False)
        
        # 🔥 ELIMINAR IMAGEN SI SE MARCÓ LA OPCIÓN
        if eliminar_imagen and instance.imagen:
            # Guardar ruta de imagen anterior para eliminarla
            imagen_anterior = instance.imagen.path if instance.imagen else None
            
            # Limpiar el campo imagen
            instance.imagen.delete(save=False)
            instance.imagen = None
            
            if commit:
                instance.save()
                # Eliminar archivo físico
                if imagen_anterior:
                    instance.delete_old_image(imagen_anterior)
        
        elif commit:
            # 🔥 MANEJO DE IMAGEN NUEVA
            if self.cleaned_data.get('imagen') and instance.pk:
                # Si hay una imagen nueva y el producto ya existe, eliminar la anterior
                try:
                    producto_anterior = Producto.objects.get(pk=instance.pk)
                    if producto_anterior.imagen and producto_anterior.imagen != instance.imagen:
                        imagen_anterior_path = producto_anterior.imagen.path
                        instance.save()  # Guardar primero la nueva imagen
                        # Eliminar la imagen anterior después de guardar
                        instance.delete_old_image(imagen_anterior_path)
                    else:
                        instance.save()
                except Producto.DoesNotExist:
                    instance.save()
            else:
                instance.save()
        
        return instance


# ========================================================================================
# FORMULARIO DE CATEGORÍAS
# ========================================================================================

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombre de la categoría'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción opcional de la categoría...'
            })
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        
        if not nombre:
            raise ValidationError('El nombre de la categoría es obligatorio.')
        
        nombre = nombre.strip()
        
        if len(nombre) < 2:
            raise ValidationError('El nombre debe tener al menos 2 caracteres.')
        
        queryset = Categoria.objects.filter(nombre__iexact=nombre)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError(f'Ya existe una categoría con el nombre "{nombre}".')
        
        return nombre


# ========================================================================================
# FORMULARIO DE MESAS
# ========================================================================================

class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero', 'ubicacion', 'activa']
        widgets = {
            'numero': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Ej: 1, 2, 3...'
            }),
            'ubicacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Terraza, Interior, VIP...'
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_numero(self):
        numero = self.cleaned_data.get('numero')
        
        if numero is None:
            raise ValidationError('El número de mesa es obligatorio.')
        
        if numero <= 0:
            raise ValidationError('El número de mesa debe ser mayor a cero.')
        
        if numero > 9999:
            raise ValidationError('El número de mesa es demasiado alto (máximo: 9999).')
        
        queryset = Mesa.objects.filter(numero=numero)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError(f'Ya existe una mesa con el número {numero}.')
        
        return numero


# ========================================================================================
# FORMULARIO DE GASTOS
# ========================================================================================

class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ['concepto', 'monto']
        widgets = {
            'concepto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Arriendo del local, Servicios públicos...'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01'
            })
        }

    def clean_concepto(self):
        concepto = self.cleaned_data.get('concepto')
        
        if not concepto:
            raise ValidationError('El concepto del gasto es obligatorio.')
        
        concepto = concepto.strip()
        
        if len(concepto) < 3:
            raise ValidationError('El concepto debe tener al menos 3 caracteres.')
        
        return concepto

    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        
        if monto is None:
            raise ValidationError('El monto es obligatorio.')
        
        try:
            monto = Decimal(str(monto))
        except (InvalidOperation, ValueError):
            raise ValidationError('El monto debe ser un número válido.')
        
        if monto <= 0:
            raise ValidationError('El monto debe ser mayor a cero.')
        
        if monto > 99999999:
            raise ValidationError('El monto es demasiado alto (máximo: $99.999.999).')
        
        return monto


# ========================================================================================
# FORMULARIO DE PAGOS A BARTENDER
# ========================================================================================

class PagoBartenderForm(forms.ModelForm):
    class Meta:
        model = PagoBartender
        fields = ['bartender', 'monto', 'observacion']
        widgets = {
            'bartender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01'
            }),
            'observacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales (opcional)'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bartender'].queryset = User.objects.filter(
            perfil__rol='bartender',
            is_active=True
        ).order_by('username')

    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        
        if monto is None:
            raise ValidationError('El monto es obligatorio.')
        
        try:
            monto = Decimal(str(monto))
        except (InvalidOperation, ValueError):
            raise ValidationError('El monto debe ser un número válido.')
        
        if monto <= 0:
            raise ValidationError('El monto debe ser mayor a cero.')
        
        if monto > 9999999:
            raise ValidationError('El monto es demasiado alto (máximo: $9.999.999).')
        
        return monto


# ========================================================================================
# FORMULARIO DE DEVOLUCIONES
# ========================================================================================

class DevolucionForm(forms.ModelForm):
    class Meta:
        model = Devolucion
        fields = ['producto', 'cantidad', 'tipo', 'razon', 'observaciones', 'venta_origen']
        widgets = {
            'producto': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'required': True
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
                'id': 'id_tipo',
                'onchange': 'updateFormByType()'
            }),
            'razon': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
                'id': 'id_razon'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe detalladamente el motivo de la devolución...',
                'required': True
            }),
            'venta_origen': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_venta_origen'
            })
        }
        labels = {
            'producto': 'Producto a devolver',
            'cantidad': 'Cantidad',
            'tipo': 'Tipo de devolución',
            'razon': 'Razón específica',
            'observaciones': 'Observaciones detalladas',
            'venta_origen': 'Venta de origen (opcional)'
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 🔥 FILTRAR PRODUCTOS DISPONIBLES (todos los productos)
        self.fields['producto'].queryset = Producto.objects.all().order_by('nombre')
        
        # 🔥 FILTRAR VENTAS RECIENTES CON MANEJO SEGURO DE TOTALES
        venta_choices = [('', 'Seleccionar venta (opcional)')]
        
        if user:
            try:
                # Ventas de los últimos 30 días
                hace_30_dias = timezone.now() - timedelta(days=30)
                
                # 🔥 USAR VALUES() PARA EVITAR PROBLEMAS DE CONVERSIÓN
                ventas_raw = Venta.objects.filter(
                    cerrada=True,
                    fecha__gte=hace_30_dias,
                    mesero=user
                ).values(
                    'id', 'total', 'fecha', 'mesa__numero'
                ).order_by('-fecha')[:20]
                
                # Procesar ventas de forma segura
                for venta_data in ventas_raw:
                    try:
                        # 🔥 CONVERSIÓN SEGURA DEL TOTAL
                        total_seguro = "0"
                        total_raw = venta_data.get('total')
                        
                        if total_raw is not None:
                            try:
                                if isinstance(total_raw, (int, float)):
                                    total_seguro = f"{int(total_raw):,}".replace(',', '.')
                                elif isinstance(total_raw, Decimal):
                                    total_seguro = f"{int(total_raw):,}".replace(',', '.')
                                elif isinstance(total_raw, str):
                                    # Limpiar string y convertir
                                    total_clean = ''.join(c for c in total_raw if c.isdigit() or c in '.-')
                                    if total_clean and total_clean not in ['-', '.', '-.']:
                                        total_num = float(total_clean)
                                        total_seguro = f"{int(total_num):,}".replace(',', '.')
                                else:
                                    total_seguro = f"{int(float(str(total_raw))):,}".replace(',', '.')
                            except (ValueError, TypeError, InvalidOperation, OverflowError):
                                total_seguro = "Error"
                        
                        # 🔥 FORMATEO SEGURO DE FECHA
                        fecha_str = "N/A"
                        try:
                            fecha = venta_data.get('fecha')
                            if fecha:
                                fecha_str = fecha.strftime("%d/%m/%Y %H:%M")
                        except:
                            fecha_str = "N/A"
                        
                        # 🔥 CREAR CHOICE SEGURO
                        mesa_numero = venta_data.get('mesa__numero', 'N/A')
                        choice_text = f'Mesa {mesa_numero} - {fecha_str} - ${total_seguro}'
                        
                        venta_choices.append((
                            venta_data['id'], 
                            choice_text
                        ))
                        
                    except Exception as e:
                        print(f"Error procesando venta {venta_data.get('id', 'N/A')}: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error general obteniendo ventas: {e}")
                # Si hay error, usar choices básico
                venta_choices = [('', 'No hay ventas disponibles')]
        
        # 🔥 ASIGNAR CHOICES DE FORMA SEGURA
        self.fields['venta_origen'].choices = venta_choices

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        razon = cleaned_data.get('razon')
        producto = cleaned_data.get('producto')
        cantidad = cleaned_data.get('cantidad')
        venta_origen = cleaned_data.get('venta_origen')
        
        if not tipo or not producto or not cantidad:
            return cleaned_data

        # 🔥 VALIDACIONES ESPECÍFICAS POR TIPO - CORREGIDAS
        if tipo == 'cliente':
            # Para devoluciones de cliente, verificar razones válidas
            razones_cliente = ['defectuoso', 'no_conforme', 'vencido', 'equivocado']
            if razon not in razones_cliente:
                raise forms.ValidationError("Razón no válida para devolución de cliente")
            
            # Si hay venta origen, verificar que el producto esté en esa venta
            if venta_origen:
                from .models import DetalleVenta
                detalle_venta = DetalleVenta.objects.filter(
                    venta=venta_origen,
                    producto=producto
                ).first()
                
                if not detalle_venta:
                    raise forms.ValidationError(
                        f"El producto '{producto.nombre}' no está en la venta seleccionada."
                    )
                
                if cantidad > detalle_venta.cantidad:
                    raise forms.ValidationError(
                        f"No se pueden devolver {cantidad} unidades. "
                        f"En esa venta solo se vendieron {detalle_venta.cantidad} unidades."
                    )
                
        elif tipo == 'inventario':
            # Para devoluciones de inventario, verificar razones válidas
            razones_inventario = ['llegada_malo', 'caducado', 'roto_almacen', 'calidad_baja', 'otro']
            if razon not in razones_inventario:
                raise forms.ValidationError("Razón no válida para devolución de inventario")
            
            # 🔥 CORREGIDO: Para inventario, permitir cualquier cantidad razonable
            # No validar contra stock actual porque es producto perdido/dañado
            if cantidad > 200:  # Límite de seguridad
                raise forms.ValidationError(
                    "Por seguridad, no se pueden devolver más de 200 unidades de una vez. "
                    "Para cantidades mayores, contacta al administrador."
                )
        
        # Validaciones generales
        if cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a 0.")
            
        return cleaned_data

    def get_razones_por_tipo(self):
        """Retorna las razones agrupadas por tipo para JavaScript"""
        return {
            'cliente': [
                ('defectuoso', 'Producto defectuoso'),
                ('no_conforme', 'Cliente no conforme'),
                ('vencido', 'Producto vencido'),
                ('equivocado', 'Producto equivocado'),
            ],
            'inventario': [
                ('llegada_malo', 'Llegó dañado del proveedor'),
                ('caducado', 'Producto caducado en inventario'),
                ('roto_almacen', 'Se rompió en almacén'),
                ('calidad_baja', 'Calidad no aceptable'),
                ('otro', 'Otro motivo'),
            ]
        }


# ========================================================================================
# FORMULARIOS ADICIONALES ÚTILES
# ========================================================================================

class BusquedaProductosForm(forms.Form):
    """Formulario para búsqueda y filtros de productos"""
    buscar = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar productos...',
            'autocomplete': 'off'
        })
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        required=False,
        empty_label="Todas las categorías",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    stock_bajo = forms.BooleanField(
        required=False,
        label="Solo stock bajo",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    def clean_buscar(self):
        buscar = self.cleaned_data.get('buscar')
        
        if buscar:
            buscar = buscar.strip()
            if len(buscar) < 2:
                raise ValidationError('El término de búsqueda debe tener al menos 2 caracteres.')
        
        return buscar


class FiltroVentasForm(forms.Form):
    """Formulario para filtrar ventas en el admin"""
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    mesero = forms.ModelChoiceField(
        queryset=User.objects.filter(perfil__rol='bartender'),
        required=False,
        empty_label="Todos los meseros",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    mesa = forms.ModelChoiceField(
        queryset=Mesa.objects.filter(activa=True),
        required=False,
        empty_label="Todas las mesas",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )