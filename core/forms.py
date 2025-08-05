from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Perfil
from .models import Producto
from .models import Mesa


from .models import Producto, Categoria, Mesa, Perfil, Gasto, PagoBartender
# Agrega estas clases a tu archivo forms.py

class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ['concepto', 'monto']
        widgets = {
            'concepto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Arriendo del local'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01'
            })
        }

class PagoBartenderForm(forms.ModelForm):
    class Meta:
        model = PagoBartender
        fields = ['bartender', 'monto', 'observacion']
        widgets = {
            'bartender': forms.Select(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'observacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales (opcional)'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bartender'].queryset = User.objects.filter(perfil__rol='bartender')

class RegistroForm(UserCreationForm):
    telefono = forms.CharField(max_length=15, required=True)
    avatar = forms.ImageField(required=False)
    ROL_CHOICES = (
        ('admin', 'Administrador'),
        ('bartender', 'Bartender'),
    )
    rol = forms.ChoiceField(choices=ROL_CHOICES)

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'telefono', 'avatar', 'rol']

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'descripcion', 'precio_costo', 'precio', 'cantidad']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre del producto'}),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Descripción opcional'}),
            'precio_costo': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0.00'}),
            'precio': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0.00'}),
            'cantidad': forms.NumberInput(attrs={'placeholder': 'Cantidad inicial'}),
        }
        labels = {
            'precio_costo': 'Precio de Costo',
            'precio': 'Precio de Venta',
        }
        from django import forms
from .models import Categoria

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la categoría'})
        }
class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero', 'ubicacion', 'activa']
        widgets = {
            'numero': forms.NumberInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

from .models import Devolucion  # Asegúrate de que este import esté

class DevolucionForm(forms.ModelForm):
    class Meta:
        model = Devolucion
        fields = ['producto', 'cantidad', 'observaciones']
        widgets = {
            'producto': forms.Select(attrs={
                'class': 'form-control',
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
        # Solo mostrar productos que tienen stock
        self.fields['producto'].queryset = Producto.objects.filter(cantidad__gt=0)
        
    def clean(self):
        cleaned_data = super().clean()
        producto = cleaned_data.get('producto')
        cantidad = cleaned_data.get('cantidad')
        
        if producto and cantidad:
            if cantidad > producto.cantidad:
                raise forms.ValidationError(f'No puedes devolver más de {producto.cantidad} unidades disponibles.')
        
        return cleaned_data