# core/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def peso_colombiano(value):
    """
    Convierte números a formato peso colombiano: $28.315.500
    """
    try:
        if value == 0 or value is None:
            return "$0"
        
        # Convertir a entero
        if isinstance(value, (int, float)):
            value = int(value)
        else:
            value = int(float(str(value)))
        
        # Formatear con separadores de miles usando puntos
        formatted = f"{value:,}".replace(',', '.')
        return f"${formatted}"
    except (ValueError, TypeError):
        return "$0"