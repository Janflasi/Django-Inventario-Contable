# 🔥 FORMS.PY LIMPIO Y OPTIMIZADO - Basado en tu código existente

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
import re

# Imports de modelos - Todo en una línea organizada
from .models import (
    Perfil, Producto, Categoria, Mesa, Gasto, 
    PagoBartender, Devolucion
)


# ========================================================================================
# FORMULARIO DE REGISTRO (Mejorado basado en tu código)
# ========================================================================================

class RegistroForm(UserCreationForm):
    telefono = forms.CharField(
        max_length=15, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '3001234567'
        })
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    ROL_CHOICES = (
        ('admin', 'Administrador'),
        ('bartender', 'Bartender'),
    )
    
    rol = forms.ChoiceField(
        choices=ROL_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'telefono', 'avatar', 'rol']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de usuario'
            })
        }

    # 🔥 VALIDACIONES AGREGADAS
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        
        if not telefono:
            raise ValidationError('El teléfono es obligatorio.')
        
        # Limpiar caracteres no numéricos
        telefono_clean = re.sub(r'[^0-9]', '', telefono)
        
        if len(telefono_clean) < 7:
            raise ValidationError('El teléfono debe tener al menos 7 dígitos.')
        
        if len(telefono_clean) > 15:
            raise ValidationError('El teléfono no puede tener más de 15 dígitos.')
        
        return telefono_clean

    def clean_username(self):
        username = self.cleaned_data.get('username')
        
        if len(username) < 3:
            raise ValidationError('El nombre de usuario debe tener al menos 3 caracteres.')
        
        return username


# ========================================================================================
# FORMULARIO DE PRODUCTOS (Mejorado con validaciones críticas)
# ========================================================================================

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'descripcion', 'precio_costo', 'precio', 'cantidad']
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
        }
        labels = {
            'precio_costo': 'Precio de Costo (COP)',
            'precio': 'Precio de Venta (COP)',
            'cantidad': 'Cantidad en Stock'
        }

    # 🔥 VALIDACIÓN CRÍTICA: Precios válidos
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

    # 🔥 VALIDACIÓN CRÍTICA: Precio de costo
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

    # 🔥 VALIDACIÓN CRÍTICA: Cantidad no negativa
    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        
        if cantidad is None:
            raise ValidationError('La cantidad es obligatoria.')
        
        if cantidad < 0:
            raise ValidationError('La cantidad no puede ser negativa.')
        
        if cantidad > 999999:
            raise ValidationError('La cantidad es demasiado alta (máximo: 999.999).')
        
        return cantidad

    # 🔥 VALIDACIÓN GLOBAL: Precio costo < precio venta
    def clean(self):
        cleaned_data = super().clean()
        precio_costo = cleaned_data.get('precio_costo')
        precio_venta = cleaned_data.get('precio')
        
        if precio_costo and precio_venta:
            if precio_costo > 0 and precio_venta > 0:
                if precio_costo >= precio_venta:
                    raise ValidationError({
                        'precio_costo': 'El precio de costo debe ser menor al precio de venta.',
                        'precio': 'El precio de venta debe ser mayor al precio de costo.'
                    })
                
                # Validar margen mínimo razonable (5%)
                margen = ((precio_venta - precio_costo) / precio_costo) * 100
                if margen < 5:
                    raise ValidationError({
                        'precio': f'El margen de ganancia es muy bajo ({margen:.1f}%). Se recomienda al menos 5%.'
                    })
        
        return cleaned_data


# ========================================================================================
# FORMULARIO DE CATEGORÍAS (Mejorado)
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
        
        # Verificar duplicados (excluyendo la categoría actual si es edición)
        queryset = Categoria.objects.filter(nombre__iexact=nombre)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError(f'Ya existe una categoría con el nombre "{nombre}".')
        
        return nombre


# ========================================================================================
# FORMULARIO DE MESAS (Mejorado)
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
        
        # Verificar duplicados (excluyendo la mesa actual si es edición)
        queryset = Mesa.objects.filter(numero=numero)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError(f'Ya existe una mesa con el número {numero}.')
        
        return numero


# ========================================================================================
# FORMULARIO DE GASTOS (Mejorado)
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
# FORMULARIO DE PAGOS A BARTENDER (Mejorado)
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
        # Solo mostrar bartenders activos
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
# FORMULARIO DE DEVOLUCIONES (Mejorado basado en tu código)
# ========================================================================================

class DevolucionForm(forms.ModelForm):
    class Meta:
        model = Devolucion
        fields = ['producto', 'cantidad', 'observaciones']
        widgets = {
            'producto': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Selecciona el producto'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cantidad a devolver',
                'min': '1'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe el motivo de la devolución (defecto, vencimiento, etc.)'
            })
        }
        labels = {
            'producto': 'Producto a devolver',
            'cantidad': 'Cantidad',
            'observaciones': 'Motivo de la devolución'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar productos que tienen stock (tu código original)
        self.fields['producto'].queryset = Producto.objects.filter(cantidad__gt=0).order_by('nombre')

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad')
        
        if cantidad is None:
            raise ValidationError('La cantidad es obligatoria.')
        
        if cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor a cero.')
        
        if cantidad > 999:
            raise ValidationError('La cantidad es demasiado alta (máximo: 999 unidades).')
        
        return cantidad

    def clean_observaciones(self):
        observaciones = self.cleaned_data.get('observaciones')
        
        if not observaciones:
            raise ValidationError('Debes explicar el motivo de la devolución.')
        
        observaciones = observaciones.strip()
        
        if len(observaciones) < 10:
            raise ValidationError('La explicación debe tener al menos 10 caracteres.')
        
        return observaciones

    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get('producto')
        cantidad = cleaned_data.get('cantidad')
        
        # Tu validación original mejorada
        if producto and cantidad:
            if cantidad > producto.cantidad:
                raise ValidationError({
                    'cantidad': f'No puedes devolver más de {producto.cantidad} unidades disponibles en stock.'
                })
        
        return cleaned_data


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


# ========================================================================================
# COMENTARIOS Y NOTAS IMPORTANTES
# ========================================================================================

"""
🔥 RESUMEN DE MEJORAS APLICADAS A TU CÓDIGO:

1. ✅ ORGANIZACIÓN:
   - Imports limpiados y organizados
   - Comentarios claros por sección
   - Orden lógico de formularios

2. ✅ VALIDACIONES CRÍTICAS AGREGADAS:
   - ProductoForm: precios válidos, cantidades no negativas
   - Todos los formularios: validaciones de negocio
   - Mensajes de error claros y específicos

3. ✅ WIDGETS MEJORADOS:
   - Bootstrap 5 classes consistentes
   - Placeholders descriptivos
   - Atributos HTML5 (min, max, step)

4. ✅ FUNCIONALIDAD PRESERVADA:
   - Tu DevolucionForm mantiene la lógica original
   - PagoBartenderForm con filtro de bartenders
   - Todos los campos y widgets que ya tenías

5. ✅ AGREGADOS ÚTILES:
   - BusquedaProductosForm para filtros
   - FiltroVentasForm para admin
   - Validaciones robustas en todos los formularios

🎯 TU CÓDIGO ORIGINAL + MIS MEJORAS = FORMULARIOS PROFESIONALES
"""