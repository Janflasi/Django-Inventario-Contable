# middleware.py - Crear este archivo en tu carpeta core/

from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

class AccountStatusMiddleware(MiddlewareMixin):
    """
    Middleware para manejar usuarios inactivos y redirecciones de autenticación
    """
    
    def process_request(self, request):
        # 🔥 INTERCEPTAR REDIRECCIONES A /accounts/login/
        if request.path.startswith('/accounts/login/'):
            # Extraer la URL de destino del parámetro 'next'
            next_url = request.GET.get('next', '')
            
            # Si hay un usuario autenticado pero inactivo
            if request.user.is_authenticated and not request.user.is_active:
                logout(request)
                messages.error(
                    request, 
                    "❌ Tu cuenta ha sido desactivada por el administrador. "
                    "Comunícate con el administrador para reactivar tu acceso."
                )
                return redirect('login')
            
            # 🔥 REDIRECCIÓN SILENCIOSA - Sin mensaje para evitar duplicados
            if next_url:
                return redirect(f'/login/?next={next_url}')
            else:
                return redirect('login')
        
        # 🔥 VERIFICAR USUARIOS ACTIVOS EN CADA REQUEST
        if request.user.is_authenticated:
            try:
                # Verificar si el usuario sigue activo
                if not request.user.is_active:
                    logout(request)
                    messages.error(
                        request,
                        "❌ Tu cuenta ha sido desactivada mientras navegabas. "
                        "Comunícate con el administrador para reactivar tu acceso."
                    )
                    return redirect('login')
                
                # Verificar si el perfil existe y es válido
                if hasattr(request.user, 'perfil'):
                    perfil = request.user.perfil
                    
                    # Si es un bartender intentando acceder a funciones de admin
                    admin_paths = [
                        '/panel/', '/gastos/', '/usuarios/', '/estadisticas/',
                        '/movimientos/', '/categorias/crear/', '/categorias/editar/',
                        '/productos/crear/', '/productos/editar/', '/mesas/crear/',
                        '/mesas/editar/', '/notificaciones/', '/panel/'
                    ]
                    
                    if (perfil.rol == 'bartender' and 
                        any(request.path.startswith(path) for path in admin_paths) and
                        not request.path.startswith('/panel/devoluciones/')):  # Permitir ver sus devoluciones
                        
                        messages.error(
                            request,
                            "🚫 No tienes permisos para acceder a esa sección."
                        )
                        return redirect('inicio')
                        
            except Exception as e:
                # Si hay algún error con el perfil, cerrar sesión por seguridad
                print(f"Error en AccountStatusMiddleware: {e}")
                logout(request)
                messages.error(
                    request,
                    "⚠️ Se produjo un error con tu sesión. Por favor, inicia sesión nuevamente."
                )
                return redirect('login')
        
        return None  # Continuar con el request normal


# 🔥 DECORADOR ADICIONAL PARA MAYOR SEGURIDAD
from functools import wraps
from django.http import HttpResponseForbidden

def active_user_required(view_func):
    """
    Decorador que verifica que el usuario esté activo
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Debes iniciar sesión para continuar.")
            return redirect('login')
        
        if not request.user.is_active:
            logout(request)
            messages.error(
                request,
                "❌ Tu cuenta ha sido desactivada. Comunícate con el administrador."
            )
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def role_required(allowed_roles):
    """
    Decorador que verifica roles específicos
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.info(request, "Debes iniciar sesión para continuar.")
                return redirect('login')
            
            if not request.user.is_active:
                logout(request)
                messages.error(
                    request,
                    "❌ Tu cuenta ha sido desactivada. Comunícate con el administrador."
                )
                return redirect('login')
            
            try:
                user_role = request.user.perfil.rol
                if user_role not in allowed_roles:
                    messages.error(
                        request,
                        f"🚫 Acceso denegado. Se requiere rol: {', '.join(allowed_roles)}"
                    )
                    return redirect('inicio' if user_role == 'bartender' else 'admin_dashboard')
            except:
                messages.error(request, "⚠️ Error con tu perfil. Contacta al administrador.")
                return redirect('login')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator