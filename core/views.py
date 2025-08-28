# ========================================================================================
# SISTEMA DE INVENTARIO Y CONTABILIDAD PARA BAR - views.py
# ========================================================================================
# 📊 Sistema completo de gestión de inventario, ventas, contabilidad y usuarios
# 🔧 Incluye manejo robusto de errores, validaciones y seguridad
# 🎯 Optimizado para bares y restaurantes con múltiples roles de usuario
# ========================================================================================


# ✅ USAR ESTOS IMPORTS EN SU LUGAR:
import decimal
from django import forms
from django.db.models import Q, F, Sum, Count, Avg
from decimal import Decimal, InvalidOperation
from django.utils.timezone import now
from django.utils import timezone  # 🔥 ESTE ES EL CORRECTO
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
from datetime import date, timedelta  # 🔥 SOLO IMPORTAR date y timedelta
from django.http import JsonResponse

# 🔥 IMPORTS DE MODELOS Y FORMULARIOS
from .models import (
    Factura, Gasto, PagoBartender, Perfil, Producto, MovimientoContable, 
    Categoria, Mesa, Venta, DetalleVenta, Notificacion, Deuda,
    PagoCompartido, PagoMixto, Devolucion, AbonoDeuda
)
from .models import ProductoCombinado, ComponenteCombo, VentaCombo

from .models import InventarioFactura

from .forms import (
    GastoForm, PagoBartenderForm, DevolucionForm, ProductoForm, 
    CategoriaForm, MesaForm
)
from .models import Proveedor, FacturaCompra, DetalleFacturaCompra, PagoFactura
from .forms import ProveedorForm, FacturaCompraForm, DetalleFacturaForm, BusquedaFacturasForm

import pytz

from core import models

def obtener_hora_colombia():
    """
    🇨🇴 Obtiene la hora actual en zona horaria de Colombia
    
    Returns:
        datetime: Fecha y hora actual en Colombia (UTC-5)
    """
    try:
        # Zona horaria de Colombia
        colombia_tz = pytz.timezone('America/Bogota')
        
        # Hora actual en Colombia
        hora_colombia = timezone.now().astimezone(colombia_tz)
        
        return hora_colombia
    except Exception as e:
        print(f"Error obteniendo hora de Colombia: {e}")
        # Fallback: UTC-5 manual
        return timezone.now() - timedelta(hours=5)


def formatear_fecha_colombia(fecha_utc):
    """
    🇨🇴 Convierte fecha UTC a formato colombiano
    
    Args:
        fecha_utc: Fecha en UTC
    
    Returns:
        str: Fecha formateada para Colombia
    """
    try:
        if not fecha_utc:
            return "N/A"
        
        # Convertir a zona horaria de Colombia
        colombia_tz = pytz.timezone('America/Bogota')
        fecha_colombia = fecha_utc.astimezone(colombia_tz)
        
        # Formato colombiano: DD/MM/YYYY HH:MM
        return fecha_colombia.strftime('%d/%m/%Y %H:%M')
    except Exception as e:
        print(f"Error formateando fecha: {e}")
        return fecha_utc.strftime('%d/%m/%Y %H:%M') if fecha_utc else "N/A"


def formatear_hora_colombia(fecha_utc):
    """
    🇨🇴 Extrae solo la hora en formato colombiano
    
    Args:
        fecha_utc: Fecha en UTC
    
    Returns:
        str: Hora en formato HH:MM
    """
    try:
        if not fecha_utc:
            return "N/A"
        
        colombia_tz = pytz.timezone('America/Bogota')
        fecha_colombia = fecha_utc.astimezone(colombia_tz)
        
        return fecha_colombia.strftime('%H:%M')
    except Exception as e:
        print(f"Error formateando hora: {e}")
        return "N/A"


# ========================================================================================
# 🛡️ FUNCIONES AUXILIARES Y UTILITIES
# ========================================================================================

def formatear_peso_colombiano(valor):
    """
    🇨🇴 Convierte números a formato peso colombiano: $2.224.600
    
    Args:
        valor: Número a formatear (int, float, Decimal, str)
    
    Returns:
        str: Valor formateado en pesos colombianos
    """
    try:
        if valor is None:
            return "$0"
        
        # Convertir a entero
        if isinstance(valor, (int, float)):
            valor = int(valor)
        else:
            valor = int(float(str(valor)))
        
        # Formatear con separadores de miles usando puntos
        formatted = f"{valor:,}".replace(',', '.')
        return f"${formatted}"
    except (ValueError, TypeError):
        return "$0"


def formatear_numero_puntos(valor):
    """
    📊 Solo agrega separadores de miles con puntos: 2.224.600
    
    Args:
        valor: Número a formatear
    
    Returns:
        str: Número formateado con separadores de miles
    """
    try:
        if valor is None:
            return "0"
            
        if isinstance(valor, (int, float)):
            valor = int(valor)
        else:
            valor = int(float(str(valor)))
        
        return f"{valor:,}".replace(',', '.')
    except (ValueError, TypeError):
        return "0"


def es_admin(user):
    """
    🔐 Verifica si un usuario es administrador
    
    Args:
        user: Usuario de Django
    
    Returns:
        bool: True si es admin, False si no
    """
    return user.is_superuser or user.perfil.rol == 'admin'


# ========================================================================================
# 🔐 AUTENTICACIÓN Y GESTIÓN DE USUARIOS
# ========================================================================================

@never_cache
def custom_login(request):
    """
    🚪 Vista de login personalizada con manejo avanzado de mensajes y redirección
    
    Features:
    - Evita mensajes duplicados
    - Verifica usuarios activos y perfiles válidos
    - Redirección inteligente según rol
    - Mensajes de bienvenida personalizados por hora
    """
    # 🔍 Si ya está autenticado, redirigir según su rol
    if request.user.is_authenticated:
        try:
            if not request.user.is_active:
                logout(request)
                messages.error(
                    request,
                    "❌ Tu cuenta ha sido desactivada. Comunícate con el administrador para reactivarla."
                )
            else:
                perfil = Perfil.objects.get(user=request.user)
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('admin_dashboard' if perfil.rol == 'admin' else 'inicio')
        except Perfil.DoesNotExist:
            logout(request)
            messages.error(request, "⚠️ Error con tu perfil. Contacta al administrador.")

    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            
            # 🔒 VERIFICAR QUE EL USUARIO ESTÉ ACTIVO
            if not usuario.is_active:
                messages.error(
                    request,
                    "❌ Tu cuenta está desactivada. Comunícate con el administrador para reactivar tu acceso."
                )
                return render(request, 'core/login.html', {
                    'form': AuthenticationForm(),
                    'error_cuenta_inactiva': True
                })
            
            # 👤 VERIFICAR QUE TENGA PERFIL
            try:
                perfil = Perfil.objects.get(user=usuario)
            except Perfil.DoesNotExist:
                messages.error(
                    request,
                    "⚠️ Tu cuenta no tiene un perfil asignado. Contacta al administrador."
                )
                return render(request, 'core/login.html', {
                    'form': AuthenticationForm(),
                    'error_sin_perfil': True
                })
            
            # ✅ LOGIN EXITOSO - LIMPIAR MENSAJES ANTERIORES
            from django.contrib.messages import get_messages
            storage = get_messages(request)
            for _ in storage:
                pass  # Esto limpia los mensajes anteriores
            
            login(request, usuario)
            
            # 🌅 MENSAJE DE BIENVENIDA PERSONALIZADO POR HORA
            hora_actual = now().hour
            if 5 <= hora_actual < 12:
                saludo = "Buenos días"
            elif 12 <= hora_actual < 18:
                saludo = "Buenas tardes"
            else:
                saludo = "Buenas noches"
                
            messages.success(
                request,
                f"✅ {saludo}, {usuario.first_name or usuario.username}. Sesión iniciada correctamente."
            )
            
            # 🎯 Redirigir según parámetro 'next' o rol
            next_url = request.GET.get('next')
            if next_url and not next_url.startswith('/accounts/'):
                return redirect(next_url)
            
            return redirect('admin_dashboard' if perfil.rol == 'admin' else 'inicio')
        else:
            # ❌ ERRORES DE AUTENTICACIÓN
            messages.error(
                request,
                "❌ Usuario o contraseña incorrectos. Verifica tus credenciales."
            )
    else:
        form = AuthenticationForm()
        
        # 🔗 MENSAJE SOLO SI VIENE DE REDIRECCIÓN
        next_url = request.GET.get('next')
        if next_url:
            from django.contrib.messages import get_messages
            storage = get_messages(request)
            messages_exist = any(storage)
            
            if not messages_exist:
                messages.info(
                    request,
                    "🔐 Debes iniciar sesión para acceder a esa página."
                )

    return render(request, 'core/login.html', {'form': form})


@never_cache
def custom_logout(request):
    """
    🚪 Vista de logout personalizada que evita mensajes innecesarios
    
    Features:
    - Solo muestra mensaje si no es redirección automática
    - Maneja referencias del navegador
    """
    if request.user.is_authenticated:
        username = request.user.first_name or request.user.username
        logout(request)
        
        # 🎯 SOLO MOSTRAR MENSAJE SI NO ES REDIRECCIÓN AUTOMÁTICA
        next_url = request.GET.get('next')
        referrer = request.META.get('HTTP_REFERER', '')
        
        # Si no viene de una redirección automática, mostrar mensaje
        if not next_url and 'accounts/login' not in referrer:
            messages.success(
                request,
                f"👋 Hasta luego, {username}. Tu sesión se cerró correctamente."
            )
    
    return redirect('login')


@never_cache
@login_required
def perfil(request):
    """
    👤 Vista del perfil del usuario actual
    """
    perfil = Perfil.objects.get(user=request.user)
    return render(request, 'core/perfil.html', {'perfil': perfil})


class PerfilForm(forms.ModelForm):
    """
    📝 Formulario para editar información básica del usuario
    """
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


@never_cache
@login_required
def perfil_editar(request):
    """
    ✏️ Vista para editar el perfil del usuario
    """
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('perfil')
    else:
        form = PerfilForm(instance=request.user)
    return render(request, 'core/perfil_editar.html', {'form': form})


@never_cache
@login_required
def cuenta_eliminar(request):
    """
    🗑️ Vista para eliminar la cuenta del usuario
    """
    if request.method == 'POST':
        request.user.delete()
        return redirect('login')
    return render(request, 'core/cuenta_eliminar.html')


@never_cache
@login_required
def asignar_roles(request):
    """
    👥 Vista para gestionar usuarios y roles (Solo administradores)
    
    Features:
    - Crear nuevos usuarios (única forma de registro)
    - Editar roles existentes
    - Activar/desactivar usuarios
    - Eliminar usuarios
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")

    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        # 🆕 CREAR USUARIO (ÚNICA FORMA DE REGISTRAR NUEVOS USUARIOS)
        if accion == 'crear_usuario':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            rol_nuevo = request.POST.get('rol_nuevo')
            telefono = request.POST.get('telefono', '')
            
            # Verificar si el usuario ya existe
            if User.objects.filter(username=username).exists():
                messages.error(request, f"El usuario '{username}' ya existe.")
            elif User.objects.filter(email=email).exists():
                messages.error(request, f"El email '{email}' ya está registrado.")
            else:
                try:
                    # Crear el usuario
                    nuevo_usuario = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password
                    )
                    
                    # Crear el perfil
                    Perfil.objects.create(
                        user=nuevo_usuario,
                        telefono=telefono,
                        rol=rol_nuevo
                    )
                    
                    messages.success(request, f"Usuario '{username}' creado exitosamente como {rol_nuevo}.")
                    
                except Exception as e:
                    messages.error(request, f"Error al crear el usuario: {str(e)}")
        
        # 🔧 FUNCIONALIDADES EXISTENTES
        elif accion in ['editar', 'eliminar', 'toggle_estado']:
            user_id = request.POST.get('user_id')
            usuario = get_object_or_404(User, id=user_id)

            if accion == 'editar':
                nuevo_rol = request.POST.get('rol')
                if nuevo_rol in ['admin', 'bartender']:
                    usuario.perfil.rol = nuevo_rol
                    usuario.perfil.save()
                    messages.success(request, f"Rol actualizado para {usuario.username}.")

            elif accion == 'eliminar':
                usuario.delete()
                messages.success(request, f"Usuario eliminado correctamente.")

            elif accion == 'toggle_estado':
                usuario.is_active = not usuario.is_active
                usuario.save()
                estado = "activado" if usuario.is_active else "desactivado"
                messages.success(request, f"Usuario {usuario.username} ha sido {estado}.")

    usuarios = User.objects.exclude(id=request.user.id)
    return render(request, 'core/asignar_roles.html', {'usuarios': usuarios})


@never_cache
@login_required
def enviar_notificacion_usuario(request, user_id):
    """
    📧 Enviar notificación a un usuario específico
    """
    if request.method == 'POST':
        mensaje = request.POST.get('mensaje')
        usuario = get_object_or_404(User, id=user_id)
        if mensaje:
            Notificacion.objects.create(
                producto=None,
                mensaje=mensaje,
                creado_por=request.user
            )
            messages.success(request, f"Mensaje enviado a {usuario.username}.")
    return redirect('asignar_roles')


# ========================================================================================
# 📊 DASHBOARD Y PANELES DE CONTROL
# ========================================================================================



@never_cache
@login_required
def admin_dashboard(request):
    """
    🎛️ Dashboard principal para administradores - CORREGIDO
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return redirect('inicio')

    try:
        from django.db.models import Sum, Count
        
        # 📊 CÁLCULO CORRECTO DEL STOCK TOTAL
        stock_stats = Producto.objects.aggregate(
            total_stock=Sum('cantidad'),
            total_productos=Count('id')
        )
        
        stock_total = stock_stats['total_stock'] or 0
        total_productos = stock_stats['total_productos'] or 0
        
        # 📦 PRODUCTOS CON STOCK BAJO Y SIN STOCK
        productos_stock_bajo = Producto.objects.filter(cantidad__lte=5, cantidad__gt=0).count()
        productos_sin_stock = Producto.objects.filter(cantidad=0).count()
        
        # 🔔 NOTIFICACIONES
        notificaciones_nuevas = Notificacion.objects.filter(leido=False).count()
        
        # 🛒 VENTAS Y MOVIMIENTOS
        total_ventas = Venta.objects.filter(cerrada=True).count()
        total_movimientos = MovimientoContable.objects.count()
        
        # 👥 USUARIOS
        total_usuarios = User.objects.count()
        
        # 🧾 FACTURAS
        try:
            facturas_pendientes = FacturaCompra.objects.filter(estado='pendiente').count()
            facturas_vencidas = FacturaCompra.objects.filter(
                estado__in=['pendiente', 'recibida'],
                fecha_vencimiento__lt=timezone.now().date()
            ).count()
            total_facturas = FacturaCompra.objects.count()
        except:
            facturas_pendientes = 0
            facturas_vencidas = 0
            total_facturas = 0
        
        # 🔄 DEVOLUCIONES
        try:
            devoluciones_pendientes = Devolucion.objects.filter(estado='pendiente').count()
        except:
            devoluciones_pendientes = 0
        
        # 💳 DEUDAS
        try:
            deudas_pendientes = Deuda.objects.filter(pagado=False).count()
            monto_deudas = Deuda.objects.filter(pagado=False).aggregate(
                total=Sum('monto_adeudado')
            )['total'] or 0
        except:
            deudas_pendientes = 0
            monto_deudas = 0
        
        # 📊 CONTEXT COMPLETO
        context = {
            'total_usuarios': total_usuarios,
            'total_productos': total_productos,
            'total_ventas': total_ventas,
            'total_movimientos': total_movimientos,
            'notificaciones_nuevas': notificaciones_nuevas,
            'stock_total': stock_total,  # 🔥 VARIABLE CORREGIDA
            'productos_stock_bajo': productos_stock_bajo,
            'productos_sin_stock': productos_sin_stock,
            'total_facturas': total_facturas,
            'facturas_pendientes': facturas_pendientes,
            'facturas_vencidas': facturas_vencidas,
            'devoluciones_pendientes': devoluciones_pendientes,
            'deudas_pendientes': deudas_pendientes,
            'monto_deudas': monto_deudas,
        }

        return render(request, 'core/admin_dashboard.html', context)
        
    except Exception as e:
        # 🆘 CONTEXT DE EMERGENCIA
        context = {
            'total_usuarios': 0,
            'total_productos': 0,
            'stock_total': 0,
            'productos_stock_bajo': 0,
            'productos_sin_stock': 0,
            'total_ventas': 0,
            'total_movimientos': 0,
            'notificaciones_nuevas': 0,
            'total_facturas': 0,
            'facturas_pendientes': 0,
            'facturas_vencidas': 0,
            'devoluciones_pendientes': 0,
            'deudas_pendientes': 0,
            'monto_deudas': 0,
            'error_message': f'Error al cargar datos: {str(e)}'
        }
        
        messages.error(request, f"Error al cargar el dashboard: {str(e)}")
        return render(request, 'core/admin_dashboard.html', context)



@never_cache
@login_required
def inicio(request):
    """
    🏠 Página de inicio para bartenders
    """
    perfil = Perfil.objects.get(user=request.user)
    if perfil.rol != 'bartender':
        return redirect('admin_dashboard')
    return render(request, 'core/inicio.html')


@never_cache
@login_required
def seguimiento_mesas(request):
    """
    🏓 Vista de seguimiento de mesas con manejo ultra-seguro de datos corruptos
    
    Features:
    - Manejo robusto de errores en totales de ventas
    - Conversión segura de Decimales corruptos
    - Información completa de cada mesa y su estado
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")

    try:
        from decimal import Decimal, InvalidOperation
        
        # 🏓 OBTENER MESAS CON MANEJO SEGURO DE VENTAS
        mesas_data = []
        mesas_base = Mesa.objects.all().order_by('numero')
        
        for mesa in mesas_base:
            try:
                # 💰 OBTENER LA ÚLTIMA VENTA DE FORMA SEGURA
                ultima_venta = None
                venta_total_seguro = Decimal('0.00')
                venta_cerrada = True
                
                try:
                    # Buscar la última venta usando values() para evitar problemas de conversión
                    venta_raw = Venta.objects.filter(mesa=mesa).values(
                        'id', 'total', 'cerrada', 'fecha', 'metodo_pago'
                    ).order_by('-fecha').first()
                    
                    if venta_raw:
                        # 🔥 CONVERSIÓN ULTRA-SEGURA DEL TOTAL
                        total_raw = venta_raw.get('total')
                        try:
                            if total_raw is not None:
                                if isinstance(total_raw, Decimal):
                                    venta_total_seguro = total_raw
                                elif isinstance(total_raw, (int, float)):
                                    venta_total_seguro = Decimal(str(total_raw))
                                elif isinstance(total_raw, str):
                                    # Limpiar string de caracteres no numéricos
                                    total_clean = ''.join(c for c in total_raw if c.isdigit() or c in '.-')
                                    if total_clean and total_clean not in ['-', '.', '-.']:
                                        venta_total_seguro = Decimal(total_clean)
                                else:
                                    venta_total_seguro = Decimal(str(float(total_raw)))
                        except (InvalidOperation, ValueError, TypeError, OverflowError):
                            print(f"🔥 ERROR: Total corrupto en venta de mesa {mesa.numero}: {total_raw}")
                            venta_total_seguro = Decimal('0.00')
                        
                        venta_cerrada = venta_raw.get('cerrada', True)
                        
                        # Crear objeto venta seguro
                        ultima_venta = {
                            'id': venta_raw['id'],
                            'total': venta_total_seguro,
                            'total_formateado': f"${int(venta_total_seguro):,}".replace(',', '.'),
                            'cerrada': venta_cerrada,
                            'fecha': venta_raw['fecha'],
                            'metodo_pago': venta_raw['metodo_pago']
                        }
                        
                except Exception as e:
                    print(f"🔥 ERROR obteniendo venta para mesa {mesa.numero}: {e}")
                    ultima_venta = None
                
                # 🏓 CREAR OBJETO MESA SEGURO
                mesa_segura = {
                    'id': mesa.id,
                    'numero': mesa.numero,
                    'ubicacion': mesa.ubicacion,
                    'activa': mesa.activa,
                    'venta_actual': ultima_venta
                }
                
                mesas_data.append(mesa_segura)
                
            except Exception as e:
                print(f"🔥 ERROR procesando mesa {mesa.numero}: {e}")
                # Agregar mesa con datos mínimos seguros
                mesa_segura = {
                    'id': mesa.id,
                    'numero': mesa.numero,
                    'ubicacion': mesa.ubicacion if hasattr(mesa, 'ubicacion') else 'N/A',
                    'activa': mesa.activa if hasattr(mesa, 'activa') else False,
                    'venta_actual': None
                }
                mesas_data.append(mesa_segura)
                continue
        
        print(f"🔥 DEBUG: Se procesaron {len(mesas_data)} mesas correctamente")
        
        context = {
            'mesas_seguras': mesas_data,
            'total_mesas': len(mesas_data),
            'mesas_activas': len([m for m in mesas_data if m['activa']]),
            'mesas_con_venta': len([m for m in mesas_data if m['venta_actual'] and not m['venta_actual']['cerrada']])
        }
        
        return render(request, 'core/mesas/seguimiento_mesas.html', context)
        
    except Exception as e:
        print(f"🔥 ERROR CRÍTICO EN SEGUIMIENTO_MESAS: {e}")
        import traceback
        traceback.print_exc()
        
        messages.error(request, f"Error al cargar el seguimiento de mesas: {str(e)}")
        
        # 🆘 CONTEXTO DE EMERGENCIA
        context = {
            'mesas_seguras': [],
            'total_mesas': 0,
            'mesas_activas': 0,
            'mesas_con_venta': 0,
            'error_message': f'Error al cargar los datos: {str(e)}'
        }
        
        return render(request, 'core/mesas/seguimiento_mesas.html', context)


# ========================================================================================
# 🏷️ GESTIÓN DE CATEGORÍAS
# ========================================================================================

@never_cache
@login_required
def categorias_listar(request):
    """
    📋 Lista todas las categorías de productos
    """
    categorias = Categoria.objects.all()
    return render(request, 'core/categorias/listar.html', {'categorias': categorias})


@never_cache
@login_required
def categoria_crear(request):
    """
    ➕ Crear nueva categoría de productos
    """
    form = CategoriaForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('categorias_listar')
    return render(request, 'core/categorias/formulario.html', {'form': form, 'titulo': 'Crear'})


@never_cache
@login_required
def categoria_editar(request, pk):
    """
    ✏️ Editar categoría existente
    """
    categoria = get_object_or_404(Categoria, pk=pk)
    form = CategoriaForm(request.POST or None, instance=categoria)
    if form.is_valid():
        form.save()
        return redirect('categorias_listar')
    return render(request, 'core/categorias/formulario.html', {'form': form, 'titulo': 'Editar'})


@never_cache
@login_required
def categoria_eliminar(request, pk):
    """
    🗑️ Eliminar categoría
    """
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        return redirect('categorias_listar')
    return render(request, 'core/categorias/confirmar_eliminar.html', {'categoria': categoria})


# ========================================================================================
# 📦 GESTIÓN DE PRODUCTOS E INVENTARIO
# ========================================================================================

@never_cache
@login_required
def productos_listar(request):
    """
    📋 Lista productos individuales Y combos en el mismo inventario - ACTUALIZADA
    
    Features:
    - Productos individuales (existentes)
    - Productos combinados/promos (nuevos)
    - Filtros por categoría y búsqueda
    - Estadísticas completas
    """
    try:
        from django.db.models import Sum, Count, Q
        
        # 🔍 OBTENER PARÁMETROS DE FILTRO
        categoria_filtro = request.GET.get('categoria')
        busqueda = request.GET.get('buscar', '').strip()
        tipo_filtro = request.GET.get('tipo', 'todos')  # todos, individuales, combos
        
        # 📦 PRODUCTOS INDIVIDUALES (con filtros)
        productos = Producto.objects.select_related('categoria').order_by('nombre')
        
        # Aplicar filtro de categoría
        if categoria_filtro and categoria_filtro != 'todas':
            try:
                categoria_id = int(categoria_filtro)
                productos = productos.filter(categoria_id=categoria_id)
            except (ValueError, TypeError):
                pass
        
        # Aplicar búsqueda inteligente para productos
        if busqueda:
            productos = productos.filter(
                Q(nombre__icontains=busqueda) |
                Q(descripcion__icontains=busqueda) |
                Q(categoria__nombre__icontains=busqueda)
            )
        
        # 🎁 PRODUCTOS COMBINADOS/PROMOS (con filtros)
        combos = ProductoCombinado.objects.filter(activo=True).order_by('nombre')
        
        # Aplicar búsqueda inteligente para combos
        if busqueda:
            combos = combos.filter(
                Q(nombre__icontains=busqueda) |
                Q(descripcion__icontains=busqueda) |
                Q(componentes__producto__nombre__icontains=busqueda)
            ).distinct()
        
        # 🎯 APLICAR FILTRO DE TIPO
        if tipo_filtro == 'individuales':
            combos = ProductoCombinado.objects.none()  # No mostrar combos
        elif tipo_filtro == 'combos':
            productos = Producto.objects.none()  # No mostrar productos individuales
        
        # 📊 ESTADÍSTICAS CORREGIDAS
        stats_productos = productos.aggregate(
            total_productos=Count('id'),
            stock_total=Sum('cantidad'),
            valor_inventario=Sum(F('cantidad') * F('precio_costo'))
        )
        
        stats_combos = {
            'total_combos': combos.count(),
            'combos_con_stock': len([c for c in combos if c.tiene_stock_disponible]),
            'combos_sin_stock': len([c for c in combos if not c.tiene_stock_disponible]),
        }
        
        # 🚨 ALERTAS DE STOCK (solo productos individuales)
        stock_bajo = productos.filter(cantidad__lte=5, cantidad__gt=0)
        sin_stock = productos.filter(cantidad=0)
        
        # 🏷️ CATEGORÍAS PARA FILTRO
        categorias_disponibles = Categoria.objects.annotate(
            cantidad_productos=Count('productos')
        ).filter(cantidad_productos__gt=0).order_by('nombre')
        
        # 🎁 PREPARAR COMBOS CON INFORMACIÓN COMPLETA
        combos_con_info = []
        for combo in combos:
            combo_info = {
                'objeto': combo,
                'componentes': combo.componentes_info,
                'puede_venderse': combo.tiene_stock_disponible and combo.esta_vigente,
                'stock_limitante': combo.stock_limitante,
                'descuento_real': combo.porcentaje_descuento_real,
            }
            combos_con_info.append(combo_info)
        
        context = {
            # Datos principales
            'productos': productos,
            'combos': combos_con_info,
            
            # Estadísticas productos individuales
            'total_productos': stats_productos['total_productos'] or 0,
            'stock_total': stats_productos['stock_total'] or 0,
            'valor_inventario': stats_productos['valor_inventario'] or 0,
            
            # Estadísticas combos
            'total_combos': stats_combos['total_combos'],
            'combos_con_stock': stats_combos['combos_con_stock'],
            'combos_sin_stock': stats_combos['combos_sin_stock'],
            
            # Alertas de stock
            'productos_stock_bajo': stock_bajo.count(),
            'productos_sin_stock': sin_stock.count(),
            'alertas_stock_bajo': stock_bajo[:5],
            'alertas_sin_stock': sin_stock[:5],
            
            # Filtros aplicados
            'categoria_filtro': categoria_filtro,
            'busqueda': busqueda,
            'tipo_filtro': tipo_filtro,
            'categorias_disponibles': categorias_disponibles,
        }
        
        return render(request, 'core/productos/listar.html', context)
        
    except Exception as e:
        print(f"Error en productos_listar: {e}")
        messages.error(request, f"Error al cargar inventario: {str(e)}")
        return redirect('admin_dashboard')


@never_cache
@login_required
def productos_bartender(request):
    """
    🍺 Vista de productos Y COMBOS para bartenders (solo lectura) - ACTUALIZADA
    
    Features:
    - Productos individuales disponibles
    - Combos activos y con stock
    - Filtros por categoría y búsqueda
    - Información completa para ventas
    """
    perfil = Perfil.objects.get(user=request.user)
    if perfil.rol != 'bartender':
        return redirect('productos_listar')
    
    try:
        from django.db.models import Q
        
        # 🔍 OBTENER PARÁMETROS DE FILTRO
        categoria_filtro = request.GET.get('categoria')
        busqueda = request.GET.get('buscar', '').strip()
        tipo_filtro = request.GET.get('tipo', 'todos')  # todos, individuales, combos
        
        # 📦 PRODUCTOS INDIVIDUALES (con stock)
        productos = Producto.objects.filter(cantidad__gt=0).select_related('categoria').order_by('nombre')
        
        # Aplicar filtro de categoría a productos
        if categoria_filtro and categoria_filtro != 'todas':
            try:
                categoria_id = int(categoria_filtro)
                productos = productos.filter(categoria_id=categoria_id)
            except (ValueError, TypeError):
                pass
        
        # Aplicar búsqueda a productos
        if busqueda:
            productos = productos.filter(
                Q(nombre__icontains=busqueda) |
                Q(descripcion__icontains=busqueda) |
                Q(categoria__nombre__icontains=busqueda)
            )
        
        # 🎁 COMBOS DISPONIBLES (activos, vigentes y con stock)
        combos_base = ProductoCombinado.objects.filter(activo=True).order_by('nombre')
        
        # Filtrar combos que tengan stock disponible
        combos_con_stock = []
        for combo in combos_base:
            if combo.tiene_stock_disponible and combo.esta_vigente:
                combos_con_stock.append(combo)
        
        # Aplicar búsqueda a combos
        if busqueda:
            combos_filtrados = []
            for combo in combos_con_stock:
                if (busqueda.lower() in combo.nombre.lower() or 
                    busqueda.lower() in combo.descripcion.lower()):
                    combos_filtrados.append(combo)
            combos_con_stock = combos_filtrados
        
        # 🎯 APLICAR FILTRO DE TIPO
        if tipo_filtro == 'individuales':
            combos_con_stock = []  # No mostrar combos
        elif tipo_filtro == 'combos':
            productos = Producto.objects.none()  # No mostrar productos individuales
        
        # 🎁 PREPARAR COMBOS CON INFORMACIÓN COMPLETA PARA BARTENDER
        combos_para_bartender = []
        for combo in combos_con_stock:
            combo_info = {
                'objeto': combo,
                'componentes': combo.componentes_info,
                'puede_venderse': True,  # Ya están filtrados los que se pueden vender
                'stock_limitante': combo.stock_limitante,
                'descuento_real': combo.porcentaje_descuento_real,
                'precio_individual_total': combo.precio_individual_total,
                'ahorro': combo.precio_individual_total - combo.precio_combo,
            }
            combos_para_bartender.append(combo_info)
        
        # 🏷️ CATEGORÍAS PARA FILTRO (solo las que tienen productos con stock)
        categorias_disponibles = Categoria.objects.filter(
            productos__cantidad__gt=0
        ).distinct().order_by('nombre')
        
        # 📊 ESTADÍSTICAS PARA EL BARTENDER
        stats = {
            'total_productos_disponibles': productos.count(),
            'total_combos_disponibles': len(combos_para_bartender),
            'productos_stock_bajo': productos.filter(cantidad__lte=5).count(),
        }
        
        context = {
            # Datos principales
            'productos': productos,
            'combos': combos_para_bartender,
            
            # Estadísticas
            'stats': stats,
            
            # Filtros aplicados
            'categoria_filtro': categoria_filtro,
            'busqueda': busqueda,
            'tipo_filtro': tipo_filtro,
            'categorias_disponibles': categorias_disponibles,
            
            # Info adicional
            'es_bartender': True,
            'puede_notificar': True,
        }
        
        return render(request, 'core/productos/listar_bartender.html', context)
        
    except Exception as e:
        print(f"Error en productos_bartender: {e}")
        messages.error(request, f"Error al cargar productos: {str(e)}")
        return redirect('inicio')


@never_cache
@login_required
def producto_crear(request):
    """
    ➕ Crear nuevo producto con imagen y registro automático de inversión
    
    Features:
    - Manejo de imagen con validaciones
    - Redimensionamiento automático
    - Validaciones completas del formulario
    - Registro automático como MovimientoContable tipo 'costo'
    - Cálculo de inversión total (precio_costo × cantidad)
    """
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)  # 🔥 AGREGAR request.FILES
        if form.is_valid():
            try:
                producto = form.save()
                
                # ✅ REGISTRAR INVERSIÓN COMO COSTO (no gasto)
                if producto.precio_costo > 0:
                    MovimientoContable.objects.create(
                        tipo='costo',  # 🔥 TIPO CORRECTO: costo para inversiones
                        concepto=f'Inversión en producto: {producto.nombre} (x{producto.cantidad})',
                        monto=producto.precio_costo * producto.cantidad,  # Costo total de la inversión
                        usuario=request.user
                    )
                    
                    # 🔥 MENSAJE MEJORADO CON INFO DE IMAGEN
                    imagen_info = " con imagen" if hasattr(producto, 'tiene_imagen') and producto.tiene_imagen() else ""
                    messages.success(
                        request, 
                        f'✅ Producto "{producto.nombre}" creado{imagen_info}. '
                        f'Inversión de ${producto.precio_costo * producto.cantidad:,.0f} COP registrada como costo.'
                    )
                else:
                    imagen_info = " con imagen" if hasattr(producto, 'tiene_imagen') and producto.tiene_imagen() else ""
                    messages.success(request, f'✅ Producto "{producto.nombre}" creado{imagen_info} correctamente.')
                
                return redirect('productos_listar')
                
            except Exception as e:
                print(f"Error creando producto: {e}")
                messages.error(request, f'❌ Error al crear el producto: {str(e)}')
        else:
            # 🔥 MOSTRAR ERRORES ESPECÍFICOS
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"❌ {error}")
                    else:
                        field_name = form.fields[field].label or field
                        messages.error(request, f"❌ Error en {field_name}: {error}")
    else:
        form = ProductoForm()
    
    return render(request, 'core/productos/formulario.html', {
        'form': form, 
        'titulo': 'Crear Producto',
        'es_creacion': True
    })


@never_cache
@login_required
def producto_editar(request, pk):
    """
    ✏️ Editar producto existente con manejo de imagen y detección automática de surtido
    
    Features:
    - Manejo completo de imágenes (actualizar, eliminar, mantener)
    - Detecta aumentos en cantidad (surtir inventario)
    - Registra inversiones adicionales automáticamente
    - Manejo seguro de todas las validaciones
    """
    producto = get_object_or_404(Producto, pk=pk)
    
    # 📊 GUARDAR DATOS ORIGINALES ANTES DE EDITAR
    cantidad_original = producto.cantidad
    imagen_original = producto.imagen.url if producto.imagen else None
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)  # 🔥 AGREGAR request.FILES
        if form.is_valid():
            try:
                producto_editado = form.save()
                
                # 🔍 DETECTAR SI SE AUMENTÓ LA CANTIDAD (surtir inventario)
                cantidad_nueva = producto_editado.cantidad
                if cantidad_nueva > cantidad_original:
                    diferencia = cantidad_nueva - cantidad_original
                    
                    # 💰 Calcular la inversión adicional
                    if producto_editado.precio_costo > 0:
                        inversion_adicional = producto_editado.precio_costo * diferencia
                        
                        # 📝 Registrar como COSTO (no gasto)
                        MovimientoContable.objects.create(
                            tipo='costo',  # 🔥 TIPO CORRECTO: costo para inversiones
                            concepto=f'Surtir inventario: {producto_editado.nombre} (+{diferencia} unidades)',
                            monto=inversion_adicional,
                            usuario=request.user
                        )
                
                # 🔥 DETECTAR CAMBIOS EN LA IMAGEN
                imagen_nueva = producto_editado.imagen.url if producto_editado.imagen else None
                cambio_imagen = ""
                
                if imagen_original != imagen_nueva:
                    if imagen_nueva and not imagen_original:
                        cambio_imagen = " Se agregó imagen."
                    elif not imagen_nueva and imagen_original:
                        cambio_imagen = " Se eliminó la imagen."
                    elif imagen_nueva and imagen_original:
                        cambio_imagen = " Se actualizó la imagen."
                
                # 🔥 MENSAJE COMPLETO CON TODOS LOS CAMBIOS
                if cantidad_nueva > cantidad_original:
                    diferencia = cantidad_nueva - cantidad_original
                    inversion_adicional = producto_editado.precio_costo * diferencia if producto_editado.precio_costo > 0 else 0
                    
                    if inversion_adicional > 0:
                        messages.success(
                            request, 
                            f'✅ Producto "{producto_editado.nombre}" actualizado.{cambio_imagen} '
                            f'Inversión adicional de ${inversion_adicional:,.0f} COP registrada como costo '
                            f'(surtir +{diferencia} unidades).'
                        )
                    else:
                        messages.success(
                            request, 
                            f'✅ Producto "{producto_editado.nombre}" actualizado.{cambio_imagen} '
                            f'Se aumentó el stock en {diferencia} unidades.'
                        )
                else:
                    messages.success(request, f'✅ Producto "{producto_editado.nombre}" actualizado correctamente.{cambio_imagen}')
                
                return redirect('productos_listar')
                
            except Exception as e:
                print(f"Error editando producto: {e}")
                messages.error(request, f'❌ Error al actualizar el producto: {str(e)}')
        else:
            # 🔥 MOSTRAR ERRORES ESPECÍFICOS
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f"❌ {error}")
                    else:
                        field_name = form.fields[field].label or field
                        messages.error(request, f"❌ Error en {field_name}: {error}")
    else:
        form = ProductoForm(instance=producto)
    
    return render(request, 'core/productos/formulario.html', {
        'form': form,
        'titulo': 'Editar Producto',
        'producto': producto,
        'es_edicion': True
    })


@never_cache
@login_required
def producto_eliminar(request, pk):
    """
    🗑️ Eliminar producto del inventario con manejo de imagen
    """
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        nombre_producto = producto.nombre
        tiene_imagen = bool(producto.imagen)
        
        # 🔥 ELIMINAR IMAGEN FÍSICAMENTE ANTES DE ELIMINAR EL PRODUCTO
        if producto.imagen:
            try:
                import os
                imagen_path = producto.imagen.path
                producto.imagen.delete(save=False)  # No guardar el modelo aún
                # Eliminar archivo físico
                if os.path.exists(imagen_path):
                    os.remove(imagen_path)
            except Exception as e:
                print(f"Error eliminando imagen del producto {pk}: {e}")
        
        # Eliminar el producto
        producto.delete()
        
        # Mensaje informativo
        imagen_info = " (incluida su imagen)" if tiene_imagen else ""
        messages.success(request, f'✅ Producto "{nombre_producto}" eliminado correctamente{imagen_info}.')
        
        return redirect('productos_listar')
    
    return render(request, 'core/productos/confirmar_eliminar.html', {
        'producto': producto
    })
# ========================================================================================
# 🔥 AGREGAR ESTAS FUNCIONES AL FINAL DE TU ARCHIVO views.py EXISTENTE
# ========================================================================================

# 🔥 NUEVA VISTA: Ver imagen en tamaño completo
@never_cache
@login_required
def producto_ver_imagen(request, pk):
    """
    🖼️ Ver imagen del producto en tamaño completo
    """
    producto = get_object_or_404(Producto, pk=pk)
    
    if not producto.imagen:
        messages.error(request, 'Este producto no tiene imagen.')
        return redirect('productos_listar')
    
    return render(request, 'core/productos/ver_imagen.html', {
        'producto': producto
    })


# 🔥 NUEVA VISTA API: Obtener información del producto con imagen
@never_cache
@login_required
def producto_info_api(request, pk):
    """
    📡 API para obtener información del producto incluyendo imagen
    """
    try:
        producto = get_object_or_404(Producto, pk=pk)
        
        data = {
            'id': producto.id,
            'nombre': producto.nombre,
            'precio': float(producto.precio),
            'precio_formateado': f"${int(producto.precio):,}".replace(',', '.'),
            'cantidad': producto.cantidad,
            'stock_bajo': producto.stock_bajo(),
            'estado_stock': producto.estado_stock(),
            'tiene_imagen': producto.tiene_imagen(),
            'imagen_url': producto.get_imagen_url(),
            'descripcion': producto.descripcion,
            'categoria': producto.categoria.nombre if producto.categoria else None,
            'precio_costo': float(producto.precio_costo),
            'ganancia_unitaria': float(producto.ganancia_unitaria()),
            'porcentaje_ganancia': round(producto.porcentaje_ganancia(), 2)
        }
        
        return JsonResponse({
            'success': True,
            'producto': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ========================================================================================
# 🛠️ UTILIDADES PARA GESTIÓN DE IMÁGENES
# ========================================================================================

@never_cache
@staff_member_required
def limpiar_imagenes_huerfanas(request):
    """
    🧹 Utilidad para administradores: limpiar imágenes huérfanas del servidor
    """
    import os
    import glob
    from django.conf import settings
    
    if request.method == 'POST':
        try:
            # Ruta de la carpeta de imágenes de productos
            productos_media_path = os.path.join(settings.MEDIA_ROOT, 'productos')
            
            if not os.path.exists(productos_media_path):
                messages.info(request, 'No existe la carpeta de imágenes de productos.')
                return redirect('admin_dashboard')
            
            # Obtener todas las imágenes físicas
            archivos_fisicos = set()
            for extension in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
                archivos_fisicos.update(glob.glob(os.path.join(productos_media_path, extension)))
                archivos_fisicos.update(glob.glob(os.path.join(productos_media_path, extension.upper())))
            
            # Obtener todas las imágenes referenciadas en la BD
            productos_con_imagen = Producto.objects.exclude(imagen='').exclude(imagen__isnull=True)
            archivos_bd = set()
            
            for producto in productos_con_imagen:
                if producto.imagen:
                    archivo_path = os.path.join(settings.MEDIA_ROOT, producto.imagen.name)
                    archivos_bd.add(archivo_path)
            
            # Encontrar archivos huérfanos
            archivos_huerfanos = archivos_fisicos - archivos_bd
            
            # Eliminar archivos huérfanos
            eliminados = 0
            for archivo_huerfano in archivos_huerfanos:
                try:
                    os.remove(archivo_huerfano)
                    eliminados += 1
                except Exception as e:
                    print(f"Error eliminando {archivo_huerfano}: {e}")
            
            if eliminados > 0:
                messages.success(
                    request, 
                    f'✅ Se eliminaron {eliminados} imágenes huérfanas del servidor.'
                )
            else:
                messages.info(request, 'ℹ️ No se encontraron imágenes huérfanas.')
                
        except Exception as e:
            messages.error(request, f'❌ Error al limpiar imágenes: {str(e)}')
    
    return redirect('admin_dashboard')


@never_cache
@staff_member_required
def estadisticas_imagenes(request):
    """
    📊 Estadísticas de uso de imágenes en productos
    """
    try:
        total_productos = Producto.objects.count()
        productos_con_imagen = Producto.objects.exclude(imagen='').exclude(imagen__isnull=True).count()
        productos_sin_imagen = total_productos - productos_con_imagen
        
        porcentaje_con_imagen = (productos_con_imagen / total_productos * 100) if total_productos > 0 else 0
        
        # Calcular tamaño total de imágenes
        import os
        from django.conf import settings
        
        productos_media_path = os.path.join(settings.MEDIA_ROOT, 'productos')
        tamaño_total = 0
        
        if os.path.exists(productos_media_path):
            for archivo in os.listdir(productos_media_path):
                archivo_path = os.path.join(productos_media_path, archivo)
                if os.path.isfile(archivo_path):
                    tamaño_total += os.path.getsize(archivo_path)
        
        # Convertir bytes a MB
        tamaño_total_mb = tamaño_total / (1024 * 1024)
        
        context = {
            'total_productos': total_productos,
            'productos_con_imagen': productos_con_imagen,
            'productos_sin_imagen': productos_sin_imagen,
            'porcentaje_con_imagen': round(porcentaje_con_imagen, 1),
            'tamaño_total_mb': round(tamaño_total_mb, 2),
        }
        
        return JsonResponse({
            'success': True,
            'estadisticas': context
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def recomendaciones_precio(request):
    """
    🤖 API para obtener recomendaciones inteligentes de precios
    
    Features:
    - Análisis por categoría
    - Análisis general del inventario
    - Recomendaciones estándar de la industria
    - Análisis de competitividad
    """
    if request.method == 'GET':
        costo = float(request.GET.get('costo', 0))
        categoria_id = request.GET.get('categoria')
        
        if costo <= 0:
            return JsonResponse({'error': 'Costo inválido'})
        
        recomendaciones = []
        
        # 🏷️ ANÁLISIS POR CATEGORÍA
        if categoria_id:
            try:
                productos_categoria = Producto.objects.filter(categoria_id=categoria_id)
                if productos_categoria.exists():
                    margen_promedio = 0
                    for p in productos_categoria:
                        if p.precio_costo > 0:
                            margen = ((p.precio - p.precio_costo) / p.precio_costo) * 100
                            margen_promedio += margen
                    
                    margen_promedio = margen_promedio / productos_categoria.count()
                    
                    precio_categoria = costo * (1 + margen_promedio/100)
                    recomendaciones.append({
                        'tipo': 'Categoría',
                        'precio': f"${precio_categoria:,.0f} COP",
                        'precio_numerico': round(precio_categoria, 0),
                        'margen': round(margen_promedio, 1),
                        'descripcion': f'Basado en promedio de tu categoría',
                        'recommended': True
                    })
            except:
                pass
        
        # 📊 ANÁLISIS GENERAL DEL INVENTARIO
        productos_existentes = Producto.objects.filter(precio_costo__gt=0)
        if productos_existentes.exists():
            margenes = []
            for p in productos_existentes:
                margen = ((p.precio - p.precio_costo) / p.precio_costo) * 100
                margenes.append(margen)
            
            margen_general = sum(margenes) / len(margenes)
            precio_general = costo * (1 + margen_general/100)
            
            recomendaciones.append({
                'tipo': 'Tu Promedio',
                'precio': f"${precio_general:,.0f} COP",
                'precio_numerico': round(precio_general, 0),
                'margen': round(margen_general, 1),
                'descripcion': 'Basado en tu inventario actual',
                'recommended': len(recomendaciones) == 0
            })
        
        # 🏭 RECOMENDACIONES ESTÁNDAR DE LA INDUSTRIA
        estandares = [
            {'tipo': 'Básico', 'margen': 30, 'descripcion': 'Margen mínimo recomendado'},
            {'tipo': 'Óptimo', 'margen': 60, 'descripcion': 'Equilibrio precio-ganancia', 'recommended': len(recomendaciones) == 0},
            {'tipo': 'Premium', 'margen': 100, 'descripcion': 'Para productos exclusivos'},
        ]
        
        for est in estandares:
            precio = costo * (1 + est['margen']/100)
            recomendaciones.append({
                'tipo': est['tipo'],
                'precio': f"${precio:,.0f} COP",
                'precio_numerico': round(precio, 0),
                'margen': est['margen'],
                'descripcion': est['descripcion'],
                'recommended': est.get('recommended', False)
            })
        
        # 🏆 ANÁLISIS DE COMPETITIVIDAD
        precio_competitivo = costo * 1.4  # 40% margen competitivo
        recomendaciones.append({
            'tipo': 'Competitivo',
            'precio': f"${precio_competitivo:,.0f} COP",
            'precio_numerico': round(precio_competitivo, 0),
            'margen': 40,
            'descripcion': 'Para competir en el mercado',
            'recommended': False
        })
        
        return JsonResponse({
            'recomendaciones': recomendaciones,
            'analisis': {
                'costo': f"${costo:,.0f} COP",
                'productos_categoria': productos_categoria.count() if categoria_id else 0,
                'productos_total': productos_existentes.count()
            }
        })
    
    return JsonResponse({'error': 'Método no permitido'})


# ========================================================================================
# 🏓 GESTIÓN DE MESAS - SISTEMA DE 20 MESAS FIJAS COMPLETO
# ========================================================================================
# REEMPLAZAR TODA LA SECCIÓN DE MESAS EN TU views.py CON ESTE CÓDIGO

@never_cache
@login_required
def mesas_listar(request):
    """
    📋 Lista las 20 mesas fijas del establecimiento - ACTUALIZADA
    
    Features:
    - Muestra las 20 mesas fijas siempre
    - Solo permite activar/desactivar (no crear/eliminar)
    - Estadísticas automáticas
    - Ordenación por número
    """
    # 🏓 OBTENER LAS 20 MESAS (crear si no existen)
    _asegurar_20_mesas()
    
    # Obtener todas las mesas ordenadas por número
    mesas = Mesa.objects.all().order_by('numero')
    
    # 📊 ESTADÍSTICAS AUTOMÁTICAS
    total_mesas = mesas.count()
    mesas_activas = mesas.filter(activa=True).count()
    mesas_inactivas = mesas.filter(activa=False).count()
    
    # 🛒 MESAS CON VENTAS ABIERTAS
    mesas_con_venta_abierta = []
    for mesa in mesas:
        venta_abierta = Venta.objects.filter(mesa=mesa, cerrada=False).first()
        if venta_abierta:
            mesas_con_venta_abierta.append({
                'mesa': mesa,
                'venta': venta_abierta,
                'total': venta_abierta.total or 0
            })
    
    context = {
        'mesas': mesas,
        'total_mesas': total_mesas,
        'mesas_activas': mesas_activas,
        'mesas_inactivas': mesas_inactivas,
        'mesas_con_venta': len(mesas_con_venta_abierta),
        'ventas_abiertas': mesas_con_venta_abierta,
        'es_sistema_fijo': True,  # Bandera para el template
    }
    
    return render(request, 'core/mesas/mesas_listar.html', context)


@never_cache
@login_required
def mesas_activas(request):
    """
    ✅ Lista solo las mesas activas del sistema fijo
    """
    # Asegurar que existan las 20 mesas
    _asegurar_20_mesas()
    
    # Obtener solo mesas activas
    mesas = Mesa.objects.filter(activa=True).order_by('numero')
    
    # Estadísticas
    total_activas = mesas.count()
    
    # Mesas con ventas abiertas
    mesas_con_venta = []
    for mesa in mesas:
        venta_abierta = Venta.objects.filter(mesa=mesa, cerrada=False).first()
        if venta_abierta:
            mesas_con_venta.append({
                'mesa': mesa,
                'venta': venta_abierta,
                'total': venta_abierta.total or 0
            })
    
    context = {
        'mesas': mesas,
        'total_activas': total_activas,
        'mesas_con_venta': len(mesas_con_venta),
        'ventas_abiertas': mesas_con_venta,
        'titulo': 'Mesas Activas',
        'es_sistema_fijo': True,
    }
    
    return render(request, 'core/mesas/mesas_activas.html', context)


@never_cache
@login_required
def mesa_editar(request, pk):
    """
    ✏️ Editar mesa fija - SOLO UBICACIÓN Y ESTADO
    """
    mesa = get_object_or_404(Mesa, pk=pk)
    
    if request.method == 'POST':
        # Solo permitir cambiar ubicación y estado activa
        nueva_ubicacion = request.POST.get('ubicacion', '').strip()
        nueva_activa = request.POST.get('activa') == 'on'
        
        # Validar ubicación
        if not nueva_ubicacion:
            messages.error(request, '❌ La ubicación es obligatoria.')
            return redirect('mesa_editar', pk=pk)
        
        # Verificar si tiene ventas abiertas antes de desactivar
        if mesa.activa and not nueva_activa:  # Si se está desactivando
            venta_abierta = Venta.objects.filter(mesa=mesa, cerrada=False).first()
            if venta_abierta:
                messages.error(
                    request, 
                    f'❌ No se puede desactivar la Mesa {mesa.numero} porque tiene una venta abierta. '
                    f'Finaliza la venta primero (Total: ${venta_abierta.total:,.0f}).'
                )
                return redirect('mesa_editar', pk=pk)
        
        # Actualizar datos
        mesa.ubicacion = nueva_ubicacion
        mesa.activa = nueva_activa
        mesa.save()
        
        estado = "activada" if nueva_activa else "desactivada"
        messages.success(
            request, 
            f'✅ Mesa {mesa.numero} actualizada correctamente y {estado}.'
        )
        return redirect('mesas_listar')
    
    context = {
        'mesa': mesa,
        'es_edicion': True,
        'es_sistema_fijo': True,
    }
    
    return render(request, 'core/mesas/mesa_editar_fija.html', context)


@never_cache
@login_required
def mesa_cambiar_estado(request, pk):
    """
    🔄 Cambiar estado activo/inactivo de una mesa
    """
    if request.method != 'POST':
        messages.error(request, 'Método no permitido')
        return redirect('mesas_listar')
    
    mesa = get_object_or_404(Mesa, pk=pk)
    
    # Verificar si tiene ventas abiertas antes de desactivar
    if mesa.activa:  # Si se quiere desactivar
        venta_abierta = Venta.objects.filter(mesa=mesa, cerrada=False).first()
        if venta_abierta:
            messages.error(
                request, 
                f'❌ No se puede desactivar la Mesa {mesa.numero} porque tiene una venta abierta. '
                f'Finaliza la venta primero (Total: ${venta_abierta.total:,.0f}).'
            )
            return redirect('mesas_listar')
    
    # Cambiar estado
    estado_anterior = mesa.activa
    mesa.activa = not mesa.activa
    mesa.save()
    
    # Mensaje personalizado
    if mesa.activa:
        messages.success(
            request, 
            f'✅ Mesa {mesa.numero} activada correctamente. Ya está disponible para ventas.'
        )
    else:
        messages.success(
            request, 
            f'⏸️ Mesa {mesa.numero} desactivada correctamente. No estará disponible para nuevas ventas.'
        )
    
    return redirect('mesas_listar')


@never_cache
@login_required
def inicializar_mesas_sistema(request):
    """
    🚀 Inicializar el sistema de 20 mesas fijas (para admin)
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado - Solo administradores")
    
    if request.method == 'POST':
        try:
            mesas_creadas = 0
            mesas_existentes = 0
            
            for numero in range(1, 21):
                mesa, creada = Mesa.objects.get_or_create(
                    numero=numero,
                    defaults={
                        'ubicacion': f'Zona {((numero-1)//5)+1}',
                        'activa': True
                    }
                )
                
                if creada:
                    mesas_creadas += 1
                else:
                    mesas_existentes += 1
            
            if mesas_creadas > 0:
                messages.success(
                    request,
                    f'🎉 Sistema inicializado exitosamente: '
                    f'{mesas_creadas} mesas creadas, {mesas_existentes} ya existían. '
                    f'Total: 20 mesas fijas disponibles.'
                )
            else:
                messages.info(
                    request,
                    '✅ El sistema ya estaba completamente inicializado con las 20 mesas fijas.'
                )
                
        except Exception as e:
            messages.error(request, f'❌ Error inicializando el sistema: {str(e)}')
    
    return redirect('mesas_listar')


@never_cache
@login_required
def reset_numeracion_mesas(request):
    """
    🔄 Resetear numeración de mesas a 1-20 (para admin)
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado - Solo administradores")
    
    if request.method == 'POST':
        try:
            # Verificar que no haya ventas abiertas
            ventas_abiertas = Venta.objects.filter(cerrada=False).count()
            if ventas_abiertas > 0:
                messages.error(
                    request,
                    f'❌ No se puede resetear la numeración. '
                    f'Hay {ventas_abiertas} ventas abiertas. Finalízalas primero.'
                )
                return redirect('mesas_listar')
            
            # Contar mesas existentes antes de eliminar
            mesas_antes = Mesa.objects.count()
            
            # Eliminar todas las mesas existentes
            Mesa.objects.all().delete()
            
            # Crear las 20 mesas nuevas
            for numero in range(1, 21):
                Mesa.objects.create(
                    numero=numero,
                    ubicacion=f'Zona {((numero-1)//5)+1}',
                    activa=True
                )
            
            messages.success(
                request,
                f'🔄 Numeración reseteada exitosamente. '
                f'Se eliminaron {mesas_antes} mesas anteriores y se crearon 20 mesas nuevas (1-20).'
            )
            
        except Exception as e:
            messages.error(request, f'❌ Error reseteando numeración: {str(e)}')
    
    return redirect('mesas_listar')


def _asegurar_20_mesas():
    """
    🔧 FUNCIÓN AUXILIAR: Asegura que existan las 20 mesas fijas
    Se ejecuta automáticamente cada vez que se accede al sistema de mesas
    """
    try:
        mesas_existentes = Mesa.objects.count()
        
        if mesas_existentes < 20:
            mesas_creadas = 0
            
            for numero in range(1, 21):
                mesa, creada = Mesa.objects.get_or_create(
                    numero=numero,
                    defaults={
                        'ubicacion': f'Zona {((numero-1)//5)+1}',
                        'activa': True
                    }
                )
                
                if creada:
                    mesas_creadas += 1
            
            # Log silencioso para debugging
            if mesas_creadas > 0:
                print(f"🔧 Sistema auto-inicializado: {mesas_creadas} mesas creadas automáticamente")
                
    except Exception as e:
        print(f"❌ Error en _asegurar_20_mesas: {e}")


# ========================================================================================
# 🔧 FUNCIONES AUXILIARES ADICIONALES (OPCIONALES)
# ========================================================================================

@never_cache
@login_required
def verificar_sistema_mesas(request):
    """
    🔍 Verificar integridad del sistema de mesas (para debugging)
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden("Solo superuser")
    
    try:
        # Verificar estado actual
        total_mesas = Mesa.objects.count()
        mesas_activas = Mesa.objects.filter(activa=True).count()
        mesas_inactivas = Mesa.objects.filter(activa=False).count()
        
        # Verificar numeración
        numeros_esperados = set(range(1, 21))
        numeros_existentes = set(Mesa.objects.values_list('numero', flat=True))
        
        numeros_faltantes = numeros_esperados - numeros_existentes
        numeros_extra = numeros_existentes - numeros_esperados
        
        # Verificar duplicados
        from django.db.models import Count
        duplicados = Mesa.objects.values('numero').annotate(
            count=Count('numero')
        ).filter(count__gt=1)
        
        # Verificar ventas abiertas
        ventas_abiertas = Venta.objects.filter(cerrada=False).count()
        
        diagnostico = {
            'sistema_completo': total_mesas == 20 and not numeros_faltantes and not numeros_extra,
            'total_mesas': total_mesas,
            'mesas_activas': mesas_activas,
            'mesas_inactivas': mesas_inactivas,
            'numeros_faltantes': list(numeros_faltantes),
            'numeros_extra': list(numeros_extra),
            'duplicados': list(duplicados),
            'ventas_abiertas': ventas_abiertas,
            'puede_resetear': ventas_abiertas == 0,
        }
        
        return JsonResponse({
            'success': True,
            'diagnostico': diagnostico,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@never_cache
@login_required
def mesa_info_api(request, pk):
    """
    📡 API para obtener información de una mesa específica
    """
    try:
        mesa = get_object_or_404(Mesa, pk=pk)
        
        # Información básica
        info = {
            'id': mesa.id,
            'numero': mesa.numero,
            'ubicacion': mesa.ubicacion,
            'activa': mesa.activa,
            'zona': f"Zona {((mesa.numero-1)//5)+1}",
        }
        
        # Venta actual
        venta_actual = Venta.objects.filter(mesa=mesa, cerrada=False).first()
        if venta_actual:
            info['venta_actual'] = {
                'id': venta_actual.id,
                'total': float(venta_actual.total),
                'total_formateado': venta_actual.get_total_formateado(),
                'fecha': venta_actual.fecha.isoformat(),
                'mesero': venta_actual.mesero.username if venta_actual.mesero else None,
                'productos': venta_actual.detalles.count()
            }
        else:
            info['venta_actual'] = None
        
        # Estadísticas históricas
        ventas_historial = Venta.objects.filter(mesa=mesa, cerrada=True)
        info['estadisticas'] = {
            'total_ventas': ventas_historial.count(),
            'ultima_venta': ventas_historial.last().fecha.isoformat() if ventas_historial.exists() else None
        }
        
        return JsonResponse({
            'success': True,
            'mesa': info
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)




# ========================================================================================
# 🛒 SISTEMA DE VENTAS Y FACTURACIÓN
# ========================================================================================

@never_cache
@login_required
def venta_mesa(request, mesa_id):
    """
    🛒 Gestión de ventas por mesa - CON CIERRE AUTOMÁTICO DE VENTAS ANTIGUAS
    """
    mesa = get_object_or_404(Mesa, id=mesa_id)
    
    # 🔥 CERRAR AUTOMÁTICAMENTE VENTAS ABIERTAS DE DÍAS ANTERIORES
    hoy = timezone.now().date()
    ventas_antiguas = Venta.objects.filter(
        mesa=mesa, 
        cerrada=False, 
        fecha__date__lt=hoy
    )
    
    ventas_cerradas = 0
    for venta_antigua in ventas_antiguas:
        # Solo cerrar si no tiene productos (venta vacía)
        if not venta_antigua.detalles.exists() and not VentaCombo.objects.filter(venta=venta_antigua).exists():
            venta_antigua.cerrada = True
            venta_antigua.metodo_pago = 'efectivo'
            venta_antigua.total = 0
            venta_antigua.save()
            ventas_cerradas += 1
        else:
            # Si tiene productos, mantenerla abierta pero notificar
            messages.warning(
                request, 
                f"Hay una venta pendiente de {venta_antigua.fecha.strftime('%d/%m/%Y')} "
                f"con productos (${venta_antigua.total:,.0f}). Revísala."
            )
    
    if ventas_cerradas > 0:
        messages.info(request, f"Se cerraron automáticamente {ventas_cerradas} ventas vacías de días anteriores.")
    
    # Crear/obtener venta del día actual
    venta, created = Venta.objects.get_or_create(
        mesa=mesa, 
        cerrada=False,
        fecha__date=hoy,
        defaults={'mesero': request.user, 'fecha': timezone.now()}
    )
    
    # 📦 PRODUCTOS INDIVIDUALES CON STOCK
    productos = Producto.objects.filter(cantidad__gt=0).order_by('nombre')
    
    # 🎁 COMBOS DISPONIBLES PARA VENTA
    combos_base = ProductoCombinado.objects.filter(activo=True).order_by('nombre')
    combos_disponibles = []
    
    for combo in combos_base:
        if combo.tiene_stock_disponible and combo.esta_vigente:
            combo_info = {
                'objeto': combo,
                'componentes': combo.componentes_info,
                'stock_limitante': combo.stock_limitante,
                'descuento_real': combo.porcentaje_descuento_real,
                'ahorro': combo.precio_individual_total - combo.precio_combo,
                'precio_individual_total': combo.precio_individual_total,
            }
            combos_disponibles.append(combo_info)
    
    # 🛒 DETALLES DE LA VENTA ACTUAL CON SUBTOTALES CALCULADOS
    detalles_base = venta.detalles.select_related('producto')
    detalles_con_subtotal = []
    
    for detalle in detalles_base:
        detalle_info = {
            'id': detalle.id,
            'producto': detalle.producto,
            'cantidad': detalle.cantidad,
            'precio_unitario': detalle.precio_unitario,
            'subtotal': detalle.cantidad * detalle.precio_unitario
        }
        detalles_con_subtotal.append(detalle_info)
    
    # 🎁 COMBOS EN LA VENTA ACTUAL CON SUBTOTALES CALCULADOS
    combos_venta_base = VentaCombo.objects.filter(venta=venta).select_related('combo')
    combos_venta_con_subtotal = []
    
    for combo_venta in combos_venta_base:
        combo_data = {
            'id': combo_venta.id,
            'combo': combo_venta.combo,
            'cantidad_vendida': combo_venta.cantidad_vendida,
            'precio_unitario': combo_venta.precio_unitario,
            'subtotal': combo_venta.cantidad_vendida * combo_venta.precio_unitario,
            'venta_combo': combo_venta,
        }
        combos_venta_con_subtotal.append(combo_data)
    
    # 💰 CALCULAR TOTALES
    total_productos = sum(detalle['subtotal'] for detalle in detalles_con_subtotal)
    total_combos = sum(combo['subtotal'] for combo in combos_venta_con_subtotal)
    total_venta = total_productos + total_combos

    if request.method == 'POST':
        tipo_item = request.POST.get('tipo_item')
        
        if tipo_item == 'producto':
            # 📦 AGREGAR PRODUCTO INDIVIDUAL
            producto_id = request.POST.get('producto')
            cantidad = int(request.POST.get('cantidad'))
            producto = get_object_or_404(Producto, id=producto_id)

            if cantidad > producto.cantidad:
                messages.error(request, f"No hay suficiente stock de {producto.nombre}. Disponible: {producto.cantidad}")
                return redirect('venta_mesa', mesa_id=mesa.id)

            detalle, creado = DetalleVenta.objects.get_or_create(
                venta=venta,
                producto=producto,
                defaults={'cantidad': cantidad, 'precio_unitario': producto.precio}
            )

            if not creado:
                if detalle.cantidad + cantidad > producto.cantidad:
                    messages.error(request, f"No hay suficiente stock de {producto.nombre}. Disponible: {producto.cantidad}")
                    return redirect('venta_mesa', mesa_id=mesa.id)
                
                detalle.cantidad += cantidad
                detalle.save()

            producto.cantidad -= cantidad
            producto.save()
            
            messages.success(request, f"{producto.nombre} agregado a la venta (x{cantidad})")
            
        elif tipo_item == 'combo':
            # 🎁 AGREGAR COMBO
            combo_id = request.POST.get('combo_id')
            cantidad = int(request.POST.get('cantidad', 1))
            
            combo = get_object_or_404(ProductoCombinado, id=combo_id)
            
            # Validaciones del combo
            if not combo.activo:
                messages.error(request, f'El combo "{combo.nombre}" no está activo.')
                return redirect('venta_mesa', mesa_id=mesa.id)
            
            if not combo.esta_vigente:
                messages.error(request, f'El combo "{combo.nombre}" no está vigente.')
                return redirect('venta_mesa', mesa_id=mesa.id)
            
            if not combo.tiene_stock_disponible:
                messages.error(request, f'No hay stock suficiente para el combo "{combo.nombre}".')
                return redirect('venta_mesa', mesa_id=mesa.id)
            
            # Verificar stock para la cantidad solicitada
            stock_info = combo.stock_limitante
            if cantidad > stock_info['cantidad_maxima_combos']:
                messages.error(
                    request,
                    f'Solo se pueden vender {stock_info["cantidad_maxima_combos"]} combos de "{combo.nombre}". '
                    f'Limitado por: {stock_info["producto"].nombre} (stock: {stock_info["stock_disponible"]})'
                )
                return redirect('venta_mesa', mesa_id=mesa.id)
            
            # Reducir stock de cada componente
            for componente in combo.componentes.all():
                producto = componente.producto
                cantidad_a_reducir = componente.cantidad * cantidad
                
                if producto.cantidad < cantidad_a_reducir:
                    messages.error(
                        request,
                        f'Stock insuficiente de {producto.nombre}. '
                        f'Disponible: {producto.cantidad}, Necesario: {cantidad_a_reducir}'
                    )
                    return redirect('venta_mesa', mesa_id=mesa.id)
                
                producto.cantidad -= cantidad_a_reducir
                producto.save()
            
            # Agregar o actualizar combo en la venta
            venta_combo, creado = VentaCombo.objects.get_or_create(
                venta=venta,
                combo=combo,
                defaults={
                    'cantidad_vendida': cantidad,
                    'precio_unitario': combo.precio_combo
                }
            )
            
            if not creado:
                venta_combo.cantidad_vendida += cantidad
                venta_combo.save()
            
            messages.success(
                request,
                f"Combo '{combo.nombre}' agregado a la venta (x{cantidad}). "
                f"Ahorro: ${(combo.precio_individual_total - combo.precio_combo) * cantidad:,.0f}"
            )

        # 💰 Actualizar total de la venta
        total_productos_nuevo = venta.detalles.aggregate(total=Sum(F('cantidad') * F('precio_unitario')))['total'] or 0
        total_combos_nuevo = VentaCombo.objects.filter(venta=venta).aggregate(total=Sum(F('cantidad_vendida') * F('precio_unitario')))['total'] or 0
        venta.total = total_productos_nuevo + total_combos_nuevo
        venta.save()
        
        return redirect('venta_mesa', mesa_id=mesa.id)

    return render(request, 'core/mesas/venta_mesa.html', {
        'mesa': mesa,
        'venta': venta,
        'productos': productos,
        'combos_disponibles': combos_disponibles,
        'detalles': detalles_con_subtotal,
        'combos_en_venta': combos_venta_con_subtotal,
        'total': total_venta,
        'total_productos': total_productos,
        'total_combos': total_combos,
    })

@never_cache
@login_required
def eliminar_detalle(request, detalle_id):
    """
    🗑️ Eliminar producto de una venta (devolver stock)
    """
    detalle = get_object_or_404(DetalleVenta, id=detalle_id)
    producto = detalle.producto
    
    # 📦 Devolver stock al producto
    producto.cantidad += detalle.cantidad
    producto.save()

    # 💰 Recalcular total de la venta
    venta = detalle.venta
    detalle.delete()
    venta.total = venta.detalles.aggregate(total=Sum(F('cantidad') * F('precio_unitario')))['total'] or 0
    venta.save()
    return redirect('venta_mesa', mesa_id=venta.mesa.id)


@never_cache
@login_required
def finalizar_venta(request, venta_id):
    """
    ✅ Finalizar venta con múltiples métodos de pago
    
    Features:
    - Pago en efectivo con cálculo de vuelto
    - Pago con crédito/fiado (genera deuda)
    - Validaciones completas
    - Registro automático en MovimientoContable
    """
    venta = get_object_or_404(Venta, id=venta_id)

    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')
        venta.metodo_pago = metodo_pago

        if metodo_pago == 'efectivo':
            try:
                monto_pagado = float(request.POST.get('monto_pagado', '0'))
                if monto_pagado < venta.total:
                    messages.error(request, "El monto pagado es menor al total.")
                    return redirect('venta_mesa', mesa_id=venta.mesa.id)

                venta.monto_pagado = monto_pagado
                venta.vuelto = monto_pagado - float(venta.total)
            except ValueError:
                messages.error(request, "Monto inválido.")
                return redirect('venta_mesa', mesa_id=venta.mesa.id)

        elif metodo_pago == 'credito':
            nombre = request.POST.get('nombre_cliente')
            telefono = request.POST.get('telefono_cliente')

            if not nombre or not telefono:
                messages.error(request, "Debe ingresar nombre y teléfono del cliente fiado.")
                return redirect('venta_mesa', mesa_id=venta.mesa.id)

            venta.save()
            # 💳 Crear registro de deuda
            Deuda.objects.create(
                venta=venta,
                nombre_cliente=nombre,
                telefono_cliente=telefono,
                monto_adeudado=venta.total
            )

        # ✅ Cerrar la venta
        venta.cerrada = True
        venta.save()
        messages.success(request, f"Venta de la mesa {venta.mesa.numero} finalizada.")
        return redirect('mesas_listar')

    return redirect('venta_mesa', mesa_id=venta.mesa.id)


# ========================================================================================
# 💳 MÉTODOS DE PAGO AVANZADOS
# ========================================================================================

@never_cache
@login_required
def pago_compartido(request, venta_id):
    """
    👥 Gestión de pagos compartidos entre múltiples clientes
    
    Features:
    - Múltiples pagadores en una sola venta
    - Seguimiento de montos por persona
    - Validación de totales
    """
    venta = get_object_or_404(Venta, id=venta_id)
    pagos = venta.pagos_compartidos.all()
    total_pagado = sum(pago.monto for pago in pagos)
    pendiente = venta.total - total_pagado

    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        if accion == 'agregar_pago':
            nombre = request.POST.get('nombre_cliente')
            monto = float(request.POST.get('monto', 0))
            metodo = request.POST.get('metodo_pago')
            
            if monto > pendiente:
                messages.error(request, "El monto es mayor al pendiente.")
            else:
                PagoCompartido.objects.create(
                    venta=venta,
                    nombre_cliente=nombre,
                    monto=monto,
                    metodo_pago=metodo
                )
                messages.success(request, f"Pago de {nombre} agregado correctamente.")
        
        elif accion == 'finalizar':
            if pendiente <= 0:
                venta.metodo_pago = 'compartido'
                venta.cerrada = True
                venta.save()
                messages.success(request, "Venta finalizada con pago compartido.")
                return redirect('mesas_listar')
            else:
                messages.error(request, f"Aún faltan ${pendiente:,.0f} COP por pagar.")

        return redirect('pago_compartido', venta_id=venta.id)

    return render(request, 'core/mesas/pago_compartido.html', {
        'venta': venta,
        'pagos': pagos,
        'total_pagado': total_pagado,
        'pendiente': pendiente
    })


@never_cache
@login_required
def pago_mixto(request, venta_id):
    """
    🔄 Gestión de pagos mixtos (efectivo + transferencia)
    
    Features:
    - Combinación de efectivo y transferencia
    - Cálculo automático de vuelto
    - Validaciones de montos
    """
    venta = get_object_or_404(Venta, id=venta_id)

    if request.method == 'POST':
        efectivo = float(request.POST.get('monto_efectivo', 0))
        transferencia = float(request.POST.get('monto_transferencia', 0))
        total_pagado = efectivo + transferencia

        if total_pagado < venta.total:
            messages.error(request, "El total pagado es menor al monto de la venta.")
            return redirect('pago_mixto', venta_id=venta.id)

        vuelto = total_pagado - float(venta.total)
        
        # 💳 Crear registro de pago mixto
        PagoMixto.objects.create(
            venta=venta,
            monto_efectivo=efectivo,
            monto_transferencia=transferencia,
            vuelto=vuelto
        )
        
        venta.metodo_pago = 'mixto'
        venta.cerrada = True
        venta.save()
        
        messages.success(request, "Venta finalizada con pago mixto.")
        return redirect('mesas_listar')

    return render(request, 'core/mesas/pago_mixto.html', {'venta': venta})


@never_cache
@login_required
def admin_ventas(request):
    """
    📊 Vista ultra-robusta de ventas para administradores con manejo de datos corruptos
    
    Features:
    - Filtros avanzados por fecha, método de pago, mesa, mesero
    - Manejo seguro de totales corruptos
    - Paginación optimizada
    - Estadísticas por método de pago
    - Exportación de datos
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")

    try:
        from datetime import datetime, timedelta
        from django.utils import timezone
        from django.core.paginator import Paginator
        from decimal import Decimal, InvalidOperation
        
        # 🔍 OBTENER PARÁMETROS DE FILTRO DE FORMA SEGURA
        filtro_fecha = request.GET.get('filtro_fecha', 'hoy')
        filtro_metodo = request.GET.get('filtro_metodo', 'todos')
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_fin = request.GET.get('fecha_fin')
        buscar_mesa = request.GET.get('buscar_mesa')
        buscar_mesero = request.GET.get('buscar_mesero')

        # 📅 APLICAR FILTROS DE FECHA SEGUROS Y CORREGIDOS
        hoy = timezone.now().date()
        print(f"DEBUG: Filtro fecha seleccionado: {filtro_fecha}")
        
        # 🔍 CONSTRUIR FILTROS USANDO VALUES() PARA EVITAR PROBLEMAS DE DECIMAL
        ventas_base = Venta.objects.filter(cerrada=True).values(
            'id', 'fecha', 'total', 'metodo_pago', 'cerrada', 
            'mesa__numero', 'mesero__username', 'mesero__first_name', 
            'mesero__last_name', 'mesero__id'
        )
        
        # 📅 APLICAR FILTROS DE FECHA
        try:
            if filtro_fecha == 'hoy':
                ventas_base = ventas_base.filter(fecha__date=hoy)
                
            elif filtro_fecha == 'ayer':
                ayer = hoy - timedelta(days=1)
                ventas_base = ventas_base.filter(fecha__date=ayer)
                
            elif filtro_fecha == 'ultima_semana':
                hace_7_dias = hoy - timedelta(days=7)
                ventas_base = ventas_base.filter(fecha__date__gte=hace_7_dias, fecha__date__lte=hoy)
                
            elif filtro_fecha == 'este_mes':
                primer_dia_mes = hoy.replace(day=1)
                ventas_base = ventas_base.filter(fecha__date__gte=primer_dia_mes, fecha__date__lte=hoy)
                
            elif filtro_fecha == 'ultimo_mes':
                hace_30_dias = hoy - timedelta(days=30)
                ventas_base = ventas_base.filter(fecha__date__gte=hace_30_dias, fecha__date__lte=hoy)
                
            elif filtro_fecha == 'este_trimestre':
                mes_actual = hoy.month
                if mes_actual <= 3:
                    primer_dia_trimestre = hoy.replace(month=1, day=1)
                elif mes_actual <= 6:
                    primer_dia_trimestre = hoy.replace(month=4, day=1)
                elif mes_actual <= 9:
                    primer_dia_trimestre = hoy.replace(month=7, day=1)
                else:
                    primer_dia_trimestre = hoy.replace(month=10, day=1)
                
                ventas_base = ventas_base.filter(fecha__date__gte=primer_dia_trimestre, fecha__date__lte=hoy)
                
            elif filtro_fecha == 'este_año':
                primer_dia_año = hoy.replace(month=1, day=1)
                ventas_base = ventas_base.filter(fecha__date__gte=primer_dia_año, fecha__date__lte=hoy)
                
            elif filtro_fecha == 'todas':
                pass  # No aplicar filtro de fecha
                
            elif filtro_fecha == 'personalizado' and fecha_inicio and fecha_fin:
                try:
                    inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                    fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                    ventas_base = ventas_base.filter(fecha__date__gte=inicio, fecha__date__lte=fin)
                except ValueError:
                    ventas_base = ventas_base.filter(fecha__date=hoy)
            else:
                ventas_base = ventas_base.filter(fecha__date=hoy)
                
        except Exception as e:
            print(f"DEBUG: Error en filtros de fecha: {e}")
            ventas_base = ventas_base.filter(fecha__date=hoy)

        # 💳 FILTRO POR MÉTODO DE PAGO SEGURO
        if filtro_metodo != 'todos':
            metodos_validos = [choice[0] for choice in Venta.METODO_PAGO_CHOICES]
            if filtro_metodo in metodos_validos:
                ventas_base = ventas_base.filter(metodo_pago=filtro_metodo)

        # 🏓 FILTRO POR MESA SEGURO
        if buscar_mesa:
            try:
                numero_mesa = int(buscar_mesa)
                ventas_base = ventas_base.filter(mesa__numero=numero_mesa)
            except (ValueError, TypeError):
                pass

        # 👤 FILTRO POR MESERO SEGURO
        if buscar_mesero:
            try:
                mesero_id = int(buscar_mesero)
                ventas_base = ventas_base.filter(mesero_id=mesero_id)
            except (ValueError, TypeError):
                pass

        # 📊 LIMITAR RESULTADOS Y ORDENAR
        ventas_base = ventas_base.order_by('-fecha')[:1000]
        total_ventas_encontradas = len(ventas_base)
        
        # 🔄 PROCESAR VENTAS DE FORMA ULTRA-SEGURA
        ventas_procesadas = []
        totales_por_metodo = {
            'efectivo': Decimal('0.00'),
            'transferencia': Decimal('0.00'),
            'credito': Decimal('0.00'),
            'mixto': Decimal('0.00'),
            'compartido': Decimal('0.00'),
        }
        
        ventas_evaluadas = 0
        ventas_con_errores = 0
        
        for venta_data in ventas_base:
            ventas_evaluadas += 1
            try:
                # 💰 CONVERSIÓN ULTRA-SEGURA DEL TOTAL
                total_seguro = Decimal('0.00')
                total_raw = venta_data.get('total')
                
                try:
                    if total_raw is not None:
                        if isinstance(total_raw, Decimal):
                            total_seguro = total_raw
                        elif isinstance(total_raw, (int, float)):
                            total_seguro = Decimal(str(total_raw))
                        elif isinstance(total_raw, str):
                            total_clean = ''.join(c for c in total_raw if c.isdigit() or c in '.-')
                            if total_clean and total_clean not in ['-', '.', '-.']:
                                total_seguro = Decimal(total_clean)
                        else:
                            total_seguro = Decimal(str(float(total_raw)))
                            
                except (InvalidOperation, ValueError, TypeError, OverflowError) as e:
                    print(f"DEBUG: Error convirtiendo total de venta {venta_data['id']}: {total_raw} -> {e}")
                    total_seguro = Decimal('0.00')
                    ventas_con_errores += 1

                # 🕐 HORA SEGURA (UTC-5 para Colombia)
                hora_colombia = "N/A"
                try:
                    if venta_data.get('fecha'):
                        fecha_colombia = venta_data['fecha'] - timedelta(hours=5)
                        hora_colombia = fecha_colombia.strftime('%H:%M')
                except:
                    hora_colombia = "N/A"

                # 💰 FORMATEO SEGURO DEL TOTAL
                total_formateado = "$0"
                try:
                    if total_seguro > 0:
                        total_int = int(total_seguro)
                        total_formateado = f"${total_int:,}".replace(',', '.')
                except:
                    total_formateado = "$0"

                # 📋 CREAR OBJETO VENTA SEGURO
                venta_segura = {
                    'id': venta_data['id'],
                    'fecha': venta_data['fecha'],
                    'hora': hora_colombia,
                    'total': total_seguro,
                    'total_formateado': total_formateado,
                    'metodo_pago': venta_data['metodo_pago'] or 'efectivo',
                    'metodo_pago_display': dict(Venta.METODO_PAGO_CHOICES).get(
                        venta_data['metodo_pago'], venta_data['metodo_pago']
                    ),
                    'mesa': {
                        'numero': venta_data['mesa__numero']
                    } if venta_data['mesa__numero'] else None,
                    'mesero': {
                        'id': venta_data['mesero__id'],
                        'username': venta_data['mesero__username'],
                        'first_name': venta_data['mesero__first_name'],
                        'last_name': venta_data['mesero__last_name']
                    } if venta_data['mesero__id'] else None,
                    'cerrada': venta_data['cerrada'],
                }
                
                ventas_procesadas.append(venta_segura)
                
                # 📊 SUMAR TOTALES POR MÉTODO DE FORMA SEGURA
                metodo = venta_data['metodo_pago'] or 'efectivo'
                if metodo in totales_por_metodo:
                    totales_por_metodo[metodo] += total_seguro
                
            except Exception as e:
                print(f"DEBUG: Error general procesando venta {venta_data.get('id', 'N/A')}: {e}")
                ventas_con_errores += 1
                continue

        # 📊 CALCULAR ESTADÍSTICAS SEGURAS
        total_ventas = len(ventas_procesadas)
        monto_total = sum(v['total'] for v in ventas_procesadas)

        # 📄 PAGINACIÓN SEGURA
        paginator = Paginator(ventas_procesadas, 20)
        page_number = request.GET.get('page', 1)
        
        try:
            page_number = int(page_number)
        except (ValueError, TypeError):
            page_number = 1
            
        ventas_paginadas = paginator.get_page(page_number)

        # 👥 OBTENER MESEROS DISPONIBLES DE FORMA SEGURA
        try:
            meseros_disponibles = User.objects.filter(
                perfil__rol='bartender'
            ).select_related('perfil').order_by('username')[:20]
        except:
            meseros_disponibles = []

        # 💰 CONVERTIR DECIMALES A ENTEROS PARA TEMPLATES
        try:
            monto_total_entero = int(monto_total) if monto_total else 0
            total_efectivo_entero = int(totales_por_metodo['efectivo'])
            total_transferencia_entero = int(totales_por_metodo['transferencia'])
            total_credito_entero = int(totales_por_metodo['credito'])
            total_mixto_entero = int(totales_por_metodo['mixto'])
            total_compartido_entero = int(totales_por_metodo['compartido'])
        except (ValueError, TypeError):
            monto_total_entero = 0
            total_efectivo_entero = 0
            total_transferencia_entero = 0
            total_credito_entero = 0
            total_mixto_entero = 0
            total_compartido_entero = 0

        # 📋 CONTEXTO FINAL SEGURO
        context = {
            'ventas': ventas_paginadas,
            'total_ventas': total_ventas,
            'monto_total': monto_total_entero,
            'meseros_disponibles': meseros_disponibles,
            
            # Totales por método de pago
            'total_efectivo': total_efectivo_entero,
            'total_transferencia': total_transferencia_entero,
            'total_credito': total_credito_entero,
            'total_mixto': total_mixto_entero,
            'total_compartido': total_compartido_entero,
            
            # Filtros aplicados
            'filtro_fecha': filtro_fecha,
            'filtro_metodo': filtro_metodo,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'buscar_mesa': buscar_mesa,
            'buscar_mesero': buscar_mesero,
            
            # Opciones para filtros
            'metodos_pago': Venta.METODO_PAGO_CHOICES,
            
            # Información adicional
            'fecha_actual': hoy,
            'total_paginas': paginator.num_pages,
        }
        
        # ⚠️ ADVERTENCIA SI HAY VENTAS CON ERRORES
        if ventas_con_errores > 0:
            messages.warning(
                request, 
                f"⚠️ Se encontraron {ventas_con_errores} ventas con datos corruptos que fueron omitidas. "
                f"Se recomienda revisar la integridad de los datos."
            )
        
        return render(request, 'core/ventas/admin_ventas.html', context)
        
    except Exception as e:
        print(f"ERROR CRÍTICO EN ADMIN_VENTAS: {e}")
        import traceback
        traceback.print_exc()
        
        # 🆘 CONTEXTO DE EMERGENCIA COMPLETAMENTE SEGURO
        messages.error(request, f"Error al cargar las ventas: {str(e)}. Filtro aplicado: {request.GET.get('filtro_fecha', 'N/A')}")
        
        context = {
            'ventas': [],
            'total_ventas': 0,
            'monto_total': 0,
            'meseros_disponibles': [],
            'total_efectivo': 0,
            'total_transferencia': 0,
            'total_credito': 0,
            'total_mixto': 0,
            'total_compartido': 0,
            'filtro_fecha': request.GET.get('filtro_fecha', 'hoy'),
            'filtro_metodo': request.GET.get('filtro_metodo', 'todos'),
            'fecha_inicio': request.GET.get('fecha_inicio'),
            'fecha_fin': request.GET.get('fecha_fin'),
            'buscar_mesa': request.GET.get('buscar_mesa'),
            'buscar_mesero': request.GET.get('buscar_mesero'),
            'metodos_pago': Venta.METODO_PAGO_CHOICES,
            'fecha_actual': timezone.now().date(),
            'total_paginas': 0,
            'error_message': f'Error al cargar los datos de ventas: {str(e)}',
        }
        
        return render(request, 'core/ventas/admin_ventas.html', context)


# ========================================================================================
# 💰 CONTABILIDAD Y CIERRE DE CAJA
# ========================================================================================

@never_cache
@login_required
def cerrar_caja_dia(request):
    """
    📊 Vista optimizada para mostrar el cierre de caja del día CON DESGLOSE COMPLETO
    
    Features:
    - Total vendido general
    - Desglose por método de pago (efectivo, transferencia, crédito/fiado, mixto, compartido)
    - Verificación de que todo cuadre
    - Estadísticas detalladas por bartender
    - Productos vendidos con detalles
    """
    hoy = now().date()
    usuario = request.user
    
    try:
        # 🔍 QUERY OPTIMIZADA - Una sola consulta con select_related
        ventas_del_dia = Venta.objects.filter(
            fecha__date=hoy,
            cerrada=True,
            mesero=usuario
        ).select_related('mesa').prefetch_related('detalles__producto').order_by('fecha')
        
        # 📊 ESTADÍSTICAS BÁSICAS CON AGGREGATE
        estadisticas = ventas_del_dia.aggregate(
            total_ventas=Count('id'),
            monto_total=Sum('total'),
            promedio_venta=Avg('total')
        )
        
        # 💳 DESGLOSE POR MÉTODO DE PAGO - LA CLAVE DEL SISTEMA
        metodos_pago = {
            'efectivo': {'total': Decimal('0.00'), 'cantidad': 0, 'ventas': []},
            'transferencia': {'total': Decimal('0.00'), 'cantidad': 0, 'ventas': []},
            'credito': {'total': Decimal('0.00'), 'cantidad': 0, 'ventas': []},
            'mixto': {'total': Decimal('0.00'), 'cantidad': 0, 'ventas': []},
            'compartido': {'total': Decimal('0.00'), 'cantidad': 0, 'ventas': []}
        }
        
        # 📦 PRODUCTOS VENDIDOS CON QUERY OPTIMIZADA
        productos_vendidos = DetalleVenta.objects.filter(
            venta__fecha__date=hoy,
            venta__cerrada=True,
            venta__mesero=usuario
        ).select_related('producto', 'venta__mesa').values(
            'venta__id',
            'venta__mesa__numero',
            'venta__fecha',
            'venta__metodo_pago',
            'producto__nombre',
            'cantidad',
            'precio_unitario'
        ).annotate(
            subtotal=F('cantidad') * F('precio_unitario')
        ).order_by('venta__fecha')
        
        # 🎁 COMBOS VENDIDOS (si existen)
        combos_vendidos = []
        try:
            from .models import VentaCombo
            combos_vendidos = VentaCombo.objects.filter(
                venta__fecha__date=hoy,
                venta__cerrada=True,
                venta__mesero=usuario
            ).select_related('combo', 'venta__mesa').values(
                'venta__id',
                'venta__mesa__numero', 
                'venta__fecha',
                'venta__metodo_pago',
                'combo__nombre',
                'cantidad_vendida',
                'precio_unitario'
            ).annotate(
                subtotal=F('cantidad_vendida') * F('precio_unitario')
            ).order_by('venta__fecha')
        except ImportError:
            combos_vendidos = []
        
        # 📋 PROCESAR VENTAS CON DESGLOSE POR MÉTODO DE PAGO
        ventas_procesadas = []
        total_del_dia = Decimal('0.00')
        total_productos_vendidos = 0
        total_combos_vendidos = 0
        
        for venta in ventas_del_dia:
            try:
                # Convertir total de forma segura
                total_venta = Decimal(str(venta.total)) if venta.total else Decimal('0.00')
                
                # 🇨🇴 Calcular hora en Colombia (UTC-5)
                hora_colombia = (venta.fecha - timedelta(hours=5)).strftime('%H:%M')
                
                # 📦 Obtener detalles de la venta
                detalles_venta = []
                for detalle in venta.detalles.all():
                    detalle_info = {
                        'nombre': detalle.producto.nombre if detalle.producto else "Producto eliminado",
                        'cantidad': detalle.cantidad,
                        'precio_unitario': float(detalle.precio_unitario),
                        'subtotal': float(detalle.cantidad * detalle.precio_unitario)
                    }
                    detalles_venta.append(detalle_info)
                    total_productos_vendidos += detalle.cantidad
                
                # 🎁 Obtener combos de la venta (si existen)
                combos_venta = []
                try:
                    for combo in VentaCombo.objects.filter(venta=venta):
                        combo_info = {
                            'nombre': combo.combo.nombre,
                            'cantidad': combo.cantidad_vendida,
                            'precio_unitario': float(combo.precio_unitario),
                            'subtotal': float(combo.cantidad_vendida * combo.precio_unitario)
                        }
                        combos_venta.append(combo_info)
                        total_combos_vendidos += combo.cantidad_vendida
                except:
                    pass
                
                # 💳 CLASIFICAR POR MÉTODO DE PAGO
                metodo = venta.metodo_pago or 'efectivo'
                if metodo in metodos_pago:
                    metodos_pago[metodo]['total'] += total_venta
                    metodos_pago[metodo]['cantidad'] += 1
                    metodos_pago[metodo]['ventas'].append({
                        'venta_id': venta.id,
                        'mesa': venta.mesa.numero if venta.mesa else 'N/A',
                        'total': float(total_venta),
                        'hora': hora_colombia
                    })
                
                # 📋 Información de la venta
                venta_info = {
                    'id': venta.id,
                    'mesa': venta.mesa,
                    'total': float(total_venta),
                    'total_formateado': f"${int(total_venta):,}".replace(',', '.'),
                    'fecha': venta.fecha,
                    'hora': hora_colombia,
                    'metodo_pago': venta.get_metodo_pago_display(),
                    'metodo_pago_codigo': metodo,
                    'detalles': detalles_venta,
                    'combos': combos_venta
                }
                
                ventas_procesadas.append(venta_info)
                total_del_dia += total_venta
                
            except Exception as e:
                print(f"Error procesando venta {venta.id}: {e}")
                continue
        
        # 💰 CÁLCULOS DE EFECTIVO REAL (considerando vueltos y pagos mixtos)
        efectivo_real_recibido = Decimal('0.00')
        transferencias_reales = Decimal('0.00')
        deudas_generadas = Decimal('0.00')
        
        # Cálculos específicos por método
        for venta in ventas_del_dia:
            metodo = venta.metodo_pago or 'efectivo'
            total_venta = Decimal(str(venta.total)) if venta.total else Decimal('0.00')
            
            if metodo == 'efectivo':
                # Para efectivo, considerar el monto pagado (si está registrado)
                if hasattr(venta, 'monto_pagado') and venta.monto_pagado:
                    efectivo_real_recibido += Decimal(str(venta.monto_pagado))
                else:
                    efectivo_real_recibido += total_venta
                    
            elif metodo == 'transferencia':
                transferencias_reales += total_venta
                
            elif metodo == 'credito':
                deudas_generadas += total_venta
                
            elif metodo == 'mixto':
                # Para pagos mixtos, buscar el desglose si existe
                try:
                    from .models import PagoMixto
                    pago_mixto = PagoMixto.objects.filter(venta=venta).first()
                    if pago_mixto:
                        efectivo_real_recibido += pago_mixto.monto_efectivo
                        transferencias_reales += pago_mixto.monto_transferencia
                    else:
                        # Si no hay desglose, asumir 50/50
                        mitad = total_venta / 2
                        efectivo_real_recibido += mitad
                        transferencias_reales += mitad
                except ImportError:
                    # Si no existe PagoMixto, asumir 50/50
                    mitad = total_venta / 2
                    efectivo_real_recibido += mitad
                    transferencias_reales += mitad
                    
            elif metodo == 'compartido':
                # Para pagos compartidos, buscar el desglose
                try:
                    from .models import PagoCompartido
                    pagos_compartidos = PagoCompartido.objects.filter(venta=venta)
                    for pago in pagos_compartidos:
                        if pago.metodo_pago == 'efectivo':
                            efectivo_real_recibido += pago.monto
                        elif pago.metodo_pago == 'transferencia':
                            transferencias_reales += pago.monto
                except ImportError:
                    # Si no existe PagoCompartido, asumir todo efectivo
                    efectivo_real_recibido += total_venta
        
        # ✅ VERIFICACIÓN DE CUADRE
        total_por_metodos = sum(metodos_pago[m]['total'] for m in metodos_pago)
        cuadra_perfecto = abs(total_del_dia - total_por_metodos) < Decimal('0.01')
        diferencia = total_del_dia - total_por_metodos
        
        # 📊 FORMATEAR DATOS PARA EL TEMPLATE
        context = {
            # Datos principales
            'ventas': ventas_procesadas,
            'productos_vendidos': list(productos_vendidos),
            'combos_vendidos': list(combos_vendidos),
            
            # Totales generales
            'total': int(total_del_dia),
            'total_formateado': f"${int(total_del_dia):,}".replace(',', '.'),
            'fecha': hoy,
            'total_ventas': len(ventas_procesadas),
            'total_productos': productos_vendidos.count(),
            'total_combos': len(combos_vendidos),
            'total_productos_vendidos': total_productos_vendidos,
            'total_combos_vendidos': total_combos_vendidos,
            
            # 💳 DESGLOSE POR MÉTODO DE PAGO - LO MÁS IMPORTANTE
            'metodos_pago': {
                metodo: {
                    'total': int(datos['total']),
                    'total_formateado': f"${int(datos['total']):,}".replace(',', '.'),
                    'cantidad': datos['cantidad'],
                    'ventas': datos['ventas'],
                    'porcentaje': round((float(datos['total']) / float(total_del_dia) * 100), 1) if total_del_dia > 0 else 0,
                    'promedio': int(datos['total'] / datos['cantidad']) if datos['cantidad'] > 0 else 0,
                    'promedio_formateado': f"${int(datos['total'] / datos['cantidad']):,}".replace(',', '.') if datos['cantidad'] > 0 else '$0'
                }
                for metodo, datos in metodos_pago.items() if datos['total'] > 0
            },
            
            # 💰 EFECTIVO REAL Y DESGLOSE DETALLADO
            'efectivo_real_recibido': int(efectivo_real_recibido),
            'efectivo_real_formateado': f"${int(efectivo_real_recibido):,}".replace(',', '.'),
            'transferencias_reales': int(transferencias_reales),
            'transferencias_reales_formateado': f"${int(transferencias_reales):,}".replace(',', '.'),
            'deudas_generadas': int(deudas_generadas),
            'deudas_generadas_formateado': f"${int(deudas_generadas):,}".replace(',', '.'),
            
            # ✅ VERIFICACIÓN DE CUADRE
            'cuadra_perfecto': cuadra_perfecto,
            'diferencia': float(diferencia),
            'diferencia_formateada': f"${int(abs(diferencia)):,}".replace(',', '.'),
            'total_por_metodos': int(total_por_metodos),
            'total_por_metodos_formateado': f"${int(total_por_metodos):,}".replace(',', '.'),
            
            # Información adicional
            'bartender': usuario.username,
            'promedio_venta': int(total_del_dia / len(ventas_procesadas)) if len(ventas_procesadas) > 0 else 0,
            'hora_actual': now().strftime('%H:%M'),
            'fecha_formateada': hoy.strftime('%d/%m/%Y'),
            
            # 📊 ESTADÍSTICAS ADICIONALES
            'venta_mas_alta': max([v['total'] for v in ventas_procesadas]) if ventas_procesadas else 0,
            'venta_mas_baja': min([v['total'] for v in ventas_procesadas]) if ventas_procesadas else 0,
            'metodo_mas_usado': max(metodos_pago.keys(), key=lambda k: metodos_pago[k]['cantidad']) if any(metodos_pago[k]['cantidad'] > 0 for k in metodos_pago) else 'ninguno'
        }
        
        return render(request, 'core/caja/cerrar_caja_dia.html', context)
        
    except Exception as e:
        print(f"ERROR EN CERRAR_CAJA_DIA: {e}")
        import traceback
        traceback.print_exc()
        
        messages.error(request, f"Error al cargar el cierre de caja: {str(e)}")
        
        # 🆘 Context de emergencia
        context = {
            'ventas': [],
            'productos_vendidos': [],
            'combos_vendidos': [],
            'total': 0,
            'total_formateado': '$0',
            'fecha': hoy,
            'total_ventas': 0,
            'total_productos': 0,
            'total_combos': 0,
            'total_productos_vendidos': 0,
            'total_combos_vendidos': 0,
            'metodos_pago': {},
            'efectivo_real_recibido': 0,
            'efectivo_real_formateado': '$0',
            'transferencias_reales': 0,
            'transferencias_reales_formateado': '$0', 
            'deudas_generadas': 0,
            'deudas_generadas_formateado': '$0',
            'cuadra_perfecto': True,
            'diferencia': 0,
            'diferencia_formateada': '$0',
            'total_por_metodos': 0,
            'total_por_metodos_formateado': '$0',
            'bartender': usuario.username,
            'promedio_venta': 0,
            'hora_actual': now().strftime('%H:%M'),
            'fecha_formateada': hoy.strftime('%d/%m/%Y'),
            'venta_mas_alta': 0,
            'venta_mas_baja': 0,
            'metodo_mas_usado': 'ninguno',
            'error_message': f'Error al cargar los datos: {str(e)}'
        }
        
        return render(request, 'core/caja/cerrar_caja_dia.html', context)
@never_cache
@login_required
def generar_factura_html(request):
    """
    🧾 Generar factura HTML optimizada para cierre de caja
    
    Features:
    - Reutiliza lógica optimizada de cierre de caja
    - Formato imprimible
    - Información completa de la empresa
    """
    hoy = now().date()
    usuario = request.user
    
    try:
        # 🔄 REUTILIZAR LA LÓGICA OPTIMIZADA
        ventas_del_dia = Venta.objects.filter(
            fecha__date=hoy,
            cerrada=True,
            mesero=usuario
        ).select_related('mesa').prefetch_related('detalles__producto')
        
        # 📊 ESTADÍSTICAS RÁPIDAS
        estadisticas = ventas_del_dia.aggregate(
            total_ventas=Count('id'),
            monto_total=Sum('total')
        )
        
        # 📦 PRODUCTOS VENDIDOS SIMPLIFICADO
        productos_vendidos = DetalleVenta.objects.filter(
            venta__fecha__date=hoy,
            venta__cerrada=True,
            venta__mesero=usuario
        ).select_related('producto', 'venta__mesa').annotate(
            subtotal=F('cantidad') * F('precio_unitario'),
            hora_venta=F('venta__fecha')
        ).order_by('venta__fecha')
        
        # 📋 PREPARAR DATOS SIMPLIFICADOS
        ventas_resumen = []
        total_del_dia = estadisticas['monto_total'] or Decimal('0.00')
        
        for venta in ventas_del_dia:
            try:
                hora_colombia = (venta.fecha - timedelta(hours=5)).strftime('%H:%M')
                
                venta_resumen = {
                    'id': venta.id,
                    'mesa_numero': venta.mesa.numero if venta.mesa else 'N/A',
                    'total': float(venta.total) if venta.total else 0,
                    'hora': hora_colombia,
                    'metodo_pago': venta.get_metodo_pago_display()
                }
                ventas_resumen.append(venta_resumen)
                
            except Exception as e:
                print(f"Error en factura para venta {venta.id}: {e}")
                continue
        
        # 📄 CONTEXT SIMPLIFICADO PARA FACTURA
        context = {
            'ventas': ventas_resumen,
            'productos_vendidos': productos_vendidos,
            'total': int(total_del_dia),
            'total_formateado': f"${int(total_del_dia):,}".replace(',', '.'),
            'fecha': hoy,
            'fecha_formateada': hoy.strftime('%d/%m/%Y'),
            'total_ventas': estadisticas['total_ventas'] or 0,
            'total_productos': productos_vendidos.count(),
            'bartender': usuario.username,
            'promedio_venta': int(total_del_dia / estadisticas['total_ventas']) if estadisticas['total_ventas'] > 0 else 0,
            'numero_factura': f"{hoy.strftime('%Y%m%d')}-{usuario.id:03d}",
            'hora_generacion': now().strftime('%H:%M:%S'),
            'empresa_nombre': 'Mi Bar & Restaurant',  # 🏢 Cambiar por tu nombre
            'empresa_direccion': 'Tu dirección aquí',
            'empresa_telefono': 'Tu teléfono aquí',
        }
        
        return render(request, 'core/caja/factura_imprimible.html', context)
        
    except Exception as e:
        print(f"ERROR EN GENERAR_FACTURA_HTML: {e}")
        messages.error(request, f"Error al generar la factura: {str(e)}")
        return redirect('cerrar_caja_dia')


@never_cache
@login_required
def resumen_dia_ajax(request):
    """
    ⚡ API AJAX para obtener resumen rápido del día
    
    Features:
    - Query súper optimizada
    - Respuesta JSON rápida
    - Ventas por método de pago
    """
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Solo peticiones AJAX'}, status=400)
    
    try:
        hoy = now().date()
        usuario = request.user
        
        # 🔍 QUERY SÚPER OPTIMIZADA
        resumen = Venta.objects.filter(
            fecha__date=hoy,
            cerrada=True,
            mesero=usuario
        ).aggregate(
            total_ventas=Count('id'),
            monto_total=Sum('total'),
            promedio_venta=Avg('total')
        )
        
        # 💳 VENTAS POR MÉTODO DE PAGO
        ventas_por_metodo = Venta.objects.filter(
            fecha__date=hoy,
            cerrada=True,
            mesero=usuario
        ).values('metodo_pago').annotate(
            cantidad=Count('id'),
            total=Sum('total')
        ).order_by('metodo_pago')
        
        return JsonResponse({
            'success': True,
            'total_ventas': resumen['total_ventas'] or 0,
            'monto_total': float(resumen['monto_total'] or 0),
            'monto_total_formateado': f"${int(resumen['monto_total'] or 0):,}".replace(',', '.'),
            'promedio_venta': float(resumen['promedio_venta'] or 0),
            'ventas_por_metodo': list(ventas_por_metodo),
            'fecha': hoy.strftime('%d/%m/%Y'),
            'hora': now().strftime('%H:%M')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@never_cache
@login_required
def comparacion_dias(request):
    """
    📈 Comparar ventas del día actual con días anteriores
    """
    try:
        hoy = now().date()
        usuario = request.user
        
        # 📅 VENTAS DE LOS ÚLTIMOS 7 DÍAS
        hace_7_dias = hoy - timedelta(days=7)
        
        ventas_por_dia = Venta.objects.filter(
            fecha__date__gte=hace_7_dias,
            fecha__date__lte=hoy,
            cerrada=True,
            mesero=usuario
        ).extra(
            select={'dia': 'date(fecha)'}
        ).values('dia').annotate(
            total_ventas=Count('id'),
            monto_total=Sum('total')
        ).order_by('dia')
        
        return JsonResponse({
            'success': True,
            'ventas_por_dia': list(ventas_por_dia)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@never_cache
@login_required
def movimientos_contables(request):
    """
    💼 Vista mejorada de movimientos contables con totales - INCLUYE COSTOS
    
    Features:
    - Separación clara entre ingresos, gastos y costos
    - Cálculo correcto de ganancias (ingresos - gastos - costos)
    - Estadísticas por período
    - Últimos movimientos
    """
    
    # 💰 TOTALES GENERALES
    total_ingresos = MovimientoContable.objects.filter(tipo='ingreso').aggregate(
        total=Sum('monto'))['total'] or 0
    
    total_gastos = MovimientoContable.objects.filter(tipo='gasto').aggregate(
        total=Sum('monto'))['total'] or 0
    
    # 🔥 NUEVO: TOTAL DE COSTOS
    total_costos = MovimientoContable.objects.filter(tipo='costo').aggregate(
        total=Sum('monto'))['total'] or 0
    
    # 🔥 ACTUALIZADO: Ganancia total ahora resta costos también
    ganancia_total = total_ingresos - total_gastos - total_costos
    
    # 📅 MOVIMIENTOS HOY
    hoy = now().date()
    ingresos_hoy = MovimientoContable.objects.filter(
        fecha=hoy, tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
    
    gastos_hoy = MovimientoContable.objects.filter(
        fecha=hoy, tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
    
    # 🔥 NUEVO: COSTOS HOY
    costos_hoy = MovimientoContable.objects.filter(
        fecha=hoy, tipo='costo').aggregate(total=Sum('monto'))['total'] or 0
    
    # 💳 DEUDAS PENDIENTES
    deudas_pendientes = Deuda.objects.filter(pagado=False)
    total_por_cobrar = deudas_pendientes.aggregate(
        total=Sum('monto_adeudado'))['total'] or 0
    
    # 🛒 VENTAS TOTALES
    ventas_totales = Venta.objects.filter(cerrada=True).aggregate(
        total=Sum('total'))['total'] or 0
    
    # 📋 ÚLTIMOS MOVIMIENTOS (todos los tipos)
    movimientos = MovimientoContable.objects.all().order_by('-fecha', '-id')[:15]
    
    # 📊 CONTEXT ACTUALIZADO CON COSTOS
    context = {
        'movimientos': movimientos,
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'total_costos': total_costos,  # 🔥 NUEVO
        'ganancia_total': ganancia_total,
        'ingresos_hoy': ingresos_hoy,
        'gastos_hoy': gastos_hoy,
        'costos_hoy': costos_hoy,  # 🔥 NUEVO
        'total_por_cobrar': total_por_cobrar,
        'cantidad_deudores': deudas_pendientes.count(),
        'ventas_totales': ventas_totales,
    }
    
    return render(request, 'core/movimientos_contables.html', context)


# ========================================================================================
# 🔔 SISTEMA DE NOTIFICACIONES
# ========================================================================================

@never_cache
@login_required
def notificar_admin(request, producto_id):
    """
    📧 Enviar notificación al administrador sobre un producto
    """
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        mensaje = request.POST.get('mensaje')
        if mensaje:
            Notificacion.objects.create(
                producto=producto,
                mensaje=mensaje,
                creado_por=request.user
            )
            messages.success(request, 'Notificación enviada al administrador.')
            return redirect('productos_bartender')
    return render(request, 'core/notificaciones/notificar_form.html', {'producto': producto})


@never_cache
@login_required
def ver_notificaciones(request):
    """
    📬 Ver todas las notificaciones (Solo administradores)
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Solo los administradores pueden ver notificaciones.")
    
    notificaciones = Notificacion.objects.all().order_by('-fecha_creacion')
    # 🔄 Marcar como leídas automáticamente
    notificaciones.filter(leido=False).update(leido=True)
    return render(request, 'core/notificaciones/listar.html', {'notificaciones': notificaciones})


@login_required
@user_passes_test(es_admin)
def ver_deudores(request):
    """
    💰 Ver lista de deudores con información de abonos
    """
    try:
        # 🔍 OBTENER DEUDAS BÁSICAS PRIMERO
        deudas_base = Deuda.objects.filter(pagado=False).order_by('-fecha_registro')
        
        # 📊 PROCESAR CADA DEUDA CON CÁLCULOS DE ABONOS
        deudas_procesadas = []
        total_por_cobrar = Decimal('0.00')
        total_abonos = Decimal('0.00')
        
        for deuda in deudas_base:
            try:
                # 💰 CALCULAR ABONOS TOTALES (SAFE)
                try:
                    # Verificar si existe la relación abonos
                    if hasattr(deuda, 'abonos'):
                        abonos_deuda = deuda.abonos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
                        cantidad_abonos = deuda.abonos.count()
                        abonos_lista = deuda.abonos.all().order_by('-fecha_abono')
                    else:
                        abonos_deuda = Decimal('0.00')
                        cantidad_abonos = 0
                        abonos_lista = []
                except Exception:
                    # Si no existe AbonoDeuda aún, usar valores por defecto
                    abonos_deuda = Decimal('0.00')
                    cantidad_abonos = 0
                    abonos_lista = []
                
                # 🧮 CALCULAR SALDO PENDIENTE
                saldo_pendiente = deuda.monto_adeudado - abonos_deuda
                
                # 📈 CALCULAR PORCENTAJE PAGADO
                porcentaje_pagado = (abonos_deuda / deuda.monto_adeudado * 100) if deuda.monto_adeudado > 0 else 0
                
                # 📅 CALCULAR DÍAS DE VENCIMIENTO
                dias_vencida = (timezone.now().date() - deuda.fecha_registro.date()).days
                
                # 📋 INFORMACIÓN PROCESADA
                deuda_info = {
                    'id': deuda.id,
                    'nombre_cliente': deuda.nombre_cliente,
                    'telefono_cliente': deuda.telefono_cliente,
                    'monto_adeudado': deuda.monto_adeudado,
                    'total_abonos': abonos_deuda,
                    'saldo_pendiente': saldo_pendiente,
                    'porcentaje_pagado': round(porcentaje_pagado, 1),
                    'cantidad_abonos': cantidad_abonos,
                    'fecha_registro': deuda.fecha_registro,
                    'pagado': deuda.pagado or saldo_pendiente <= 0,
                    'dias_vencida': dias_vencida,
                    'abonos': abonos_lista,
                    'venta': getattr(deuda, 'venta', None)
                }
                
                deudas_procesadas.append(deuda_info)
                
                # 🔢 SUMAR TOTALES
                if saldo_pendiente > 0:
                    total_por_cobrar += saldo_pendiente
                total_abonos += abonos_deuda
                
                # ✅ AUTO-MARCAR COMO PAGADA SI SALDO ES 0
                if saldo_pendiente <= 0 and not deuda.pagado:
                    deuda.pagado = True
                    deuda.save()
                    
                    # 📝 REGISTRAR MOVIMIENTO CONTABLE
                    MovimientoContable.objects.create(
                        tipo='ingreso',
                        concepto=f'Deuda completada: {deuda.nombre_cliente} (abonos)',
                        monto=deuda.monto_adeudado,
                        usuario=request.user
                    )
                
            except Exception as e:
                print(f"Error procesando deuda {deuda.id}: {e}")
                continue
        
        # 📊 ESTADÍSTICAS GENERALES
        saldo_pendiente_total = sum(d['saldo_pendiente'] for d in deudas_procesadas if d['saldo_pendiente'] > 0)
        
        context = {
            'deudas': deudas_procesadas,
            'total_deudores': len(deudas_procesadas),
            'total_por_cobrar': total_por_cobrar,
            'total_abonos': total_abonos,
            'saldo_pendiente': saldo_pendiente_total,
        }
        
        return render(request, 'core/admin/deudores_lista.html', context)
        
    except Exception as e:
        print(f"Error en ver_deudores: {e}")
        messages.error(request, f"Error al cargar deudores: {str(e)}")
        return redirect('admin_dashboard')


@login_required
@user_passes_test(es_admin)
def registrar_abono_deuda(request, deuda_id):
    """
    💰 Registrar abono parcial a una deuda - CORREGIDO SIN DUPLICADOS
    """
    if request.method != 'POST':
        messages.error(request, "Método no permitido")
        return redirect('ver_deudores')
    
    try:
        # IMPORTAR MODELO DE FORMA SEGURA
        try:
            from .models import AbonoDeuda
        except ImportError:
            messages.error(request, "El sistema de abonos no está disponible. Contacta al administrador.")
            return redirect('ver_deudores')
        
        deuda = get_object_or_404(Deuda, id=deuda_id)
        
        # 🔍 VERIFICAR QUE LA DEUDA NO ESTÉ PAGADA
        if deuda.pagado:
            messages.error(request, "Esta deuda ya está marcada como pagada")
            return redirect('ver_deudores')
        
        # 📝 OBTENER DATOS DEL FORMULARIO
        monto_abono = Decimal(request.POST.get('monto_abono', '0'))
        metodo_pago = request.POST.get('metodo_pago')
        observaciones = request.POST.get('observaciones', '')
        
        # ✅ VALIDACIONES
        if monto_abono <= 0:
            messages.error(request, "El monto del abono debe ser mayor a cero")
            return redirect('ver_deudores')
        
        if not metodo_pago:
            messages.error(request, "Debe seleccionar un método de pago")
            return redirect('ver_deudores')
        
        # 🧮 CALCULAR SALDO ACTUAL
        try:
            abonos_previos = deuda.abonos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        except:
            abonos_previos = Decimal('0.00')
            
        saldo_actual = deuda.monto_adeudado - abonos_previos
        
        if monto_abono > saldo_actual:
            messages.error(request, f"El abono (${monto_abono:,.0f}) no puede ser mayor al saldo pendiente (${saldo_actual:,.0f})")
            return redirect('ver_deudores')
        
        # 💾 CREAR REGISTRO DE ABONO
        abono = AbonoDeuda.objects.create(
            deuda=deuda,
            monto=monto_abono,
            metodo_pago=metodo_pago,
            observaciones=observaciones,
            registrado_por=request.user
        )
        
        # 🔥 REGISTRAR MOVIMIENTO CONTABLE DEL ABONO (SIEMPRE)
        MovimientoContable.objects.create(
            tipo='ingreso',
            concepto=f'Abono deuda: {deuda.nombre_cliente} (${monto_abono:,.0f})',
            monto=monto_abono,
            usuario=request.user
        )
        
        # 🧮 RECALCULAR SALDO
        nuevo_saldo = saldo_actual - monto_abono
        
        # ✅ SI EL SALDO ES 0, MARCAR COMO PAGADA (SIN MOVIMIENTO ADICIONAL)
        if nuevo_saldo <= 0:
            deuda.pagado = True
            deuda.save()
            
            messages.success(
                request,
                f'✅ ¡Deuda completada! Abono final de ${monto_abono:,.0f} registrado. '
                f'{deuda.nombre_cliente} ha completado el pago de ${deuda.monto_adeudado:,.0f}.'
            )
        else:
            messages.success(
                request,
                f'✅ Abono registrado exitosamente. ${monto_abono:,.0f} de {deuda.nombre_cliente}. '
                f'Saldo pendiente: ${nuevo_saldo:,.0f}'
            )
        
        return redirect('ver_deudores')
        
    except Decimal.InvalidOperation:
        messages.error(request, "Monto inválido")
        return redirect('ver_deudores')
    except Exception as e:
        print(f"Error registrando abono: {e}")
        messages.error(request, f"Error al registrar el abono: {str(e)}")
        return redirect('ver_deudores')

@login_required
@user_passes_test(es_admin)
def marcar_deuda_pagada(request, deuda_id):
    """
    ✅ Marcar deuda como pagada completamente - CORREGIDO SIN DUPLICADOS
    """
    if request.method != 'POST':
        messages.error(request, "Método no permitido")
        return redirect('ver_deudores')
    
    try:
        deuda = get_object_or_404(Deuda, id=deuda_id)
        
        if deuda.pagado:
            messages.warning(request, "Esta deuda ya está marcada como pagada")
            return redirect('ver_deudores')
        
        # 🧮 CALCULAR SALDO PENDIENTE
        try:
            abonos_totales = deuda.abonos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        except:
            abonos_totales = Decimal('0.00')
            
        saldo_pendiente = deuda.monto_adeudado - abonos_totales
        
        # ✅ MARCAR COMO PAGADA (SIN MOVIMIENTO CONTABLE AUTOMÁTICO DEL MODELO)
        deuda.pagado = True
        deuda.save()
        
        # 🔥 SOLO REGISTRAR INGRESO SI HAY SALDO PENDIENTE REAL
        if saldo_pendiente > Decimal('0.01'):  # Solo si hay más de 1 peso pendiente
            # Registrar el saldo restante como ingreso
            MovimientoContable.objects.create(
                tipo='ingreso',
                concepto=f'Pago final deuda: {deuda.nombre_cliente} (saldo restante: ${saldo_pendiente:,.0f})',
                monto=saldo_pendiente,
                usuario=request.user
            )
            
            # Crear abono automático por el saldo restante
            try:
                from .models import AbonoDeuda
                AbonoDeuda.objects.create(
                    deuda=deuda,
                    monto=saldo_pendiente,
                    metodo_pago='efectivo',
                    observaciones='Pago final - marcado como pagado por administrador',
                    registrado_por=request.user
                )
            except:
                pass
            
            mensaje = f'✅ Deuda de {deuda.nombre_cliente} marcada como pagada. Total: ${deuda.monto_adeudado:,.0f} (pago final: ${saldo_pendiente:,.0f})'
        else:
            # 🔥 SI NO HAY SALDO PENDIENTE: NO REGISTRAR NINGÚN MOVIMIENTO
            mensaje = f'✅ Deuda de {deuda.nombre_cliente} confirmada como pagada. Total: ${deuda.monto_adeudado:,.0f} (completamente pagada con abonos)'
        
        messages.success(request, mensaje)
        return redirect('ver_deudores')
        
    except Exception as e:
        print(f"Error marcando deuda como pagada: {e}")
        messages.error(request, f"Error al marcar como pagada: {str(e)}")
        return redirect('ver_deudores')

# 🔥 FUNCIÓN ADICIONAL: Corregir duplicados existentes
@login_required
@user_passes_test(es_admin)
def corregir_duplicados_deudas(request):
    """
    🔧 Función para corregir duplicados existentes en el sistema
    """
    if request.method == 'POST':
        try:
            duplicados_eliminados = 0
            
            # 🔍 Buscar casos específicos como el de Gonzalez
            # Buscar "Pago deuda" que coincidan con una deuda completa
            movimientos_pago_deuda = MovimientoContable.objects.filter(
                tipo='ingreso',
                concepto__startswith='Pago deuda:'
            )
            
            for movimiento in movimientos_pago_deuda:
                try:
                    # Extraer nombre del cliente
                    nombre_cliente = movimiento.concepto.replace('Pago deuda: ', '')
                    
                    # Buscar la deuda correspondiente
                    deuda = Deuda.objects.filter(
                        nombre_cliente=nombre_cliente,
                        monto_adeudado=movimiento.monto
                    ).first()
                    
                    if deuda:
                        # Verificar si ya hay abonos que sumen el total
                        try:
                            total_abonos = deuda.abonos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
                            
                            # Si los abonos ya cubren la deuda, este movimiento es duplicado
                            if total_abonos >= deuda.monto_adeudado:
                                movimiento.delete()
                                duplicados_eliminados += 1
                                print(f"Eliminado duplicado: {movimiento.concepto} - ${movimiento.monto}")
                        except:
                            pass
                            
                except Exception as e:
                    print(f"Error procesando movimiento {movimiento.id}: {e}")
                    continue
            
            # 🔍 También buscar "Pago final deuda" cuando saldo era 0
            movimientos_pago_final = MovimientoContable.objects.filter(
                tipo='ingreso',
                concepto__contains='Pago final deuda:'
            )
            
            for movimiento in movimientos_pago_final:
                try:
                    # Extraer nombre del cliente
                    nombre_cliente = movimiento.concepto.split('Pago final deuda: ')[1].split(' (')[0]
                    
                    # Buscar si hay abonos del mismo cliente que sumen igual o más
                    deuda = Deuda.objects.filter(nombre_cliente=nombre_cliente).first()
                    
                    if deuda:
                        try:
                            total_abonos = deuda.abonos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
                            
                            # Si ya había abonos suficientes antes de este movimiento
                            if total_abonos >= deuda.monto_adeudado:
                                movimiento.delete()
                                duplicados_eliminados += 1
                                print(f"Eliminado pago final duplicado: {movimiento.concepto}")
                        except:
                            pass
                            
                except Exception as e:
                    print(f"Error procesando pago final {movimiento.id}: {e}")
                    continue
            
            if duplicados_eliminados > 0:
                messages.success(
                    request,
                    f'✅ Se corrigieron {duplicados_eliminados} movimientos duplicados de deudas. '
                    f'Los ingresos ahora reflejan el monto correcto.'
                )
            else:
                messages.info(request, 'ℹ️ No se encontraron duplicados para corregir.')
                
        except Exception as e:
            messages.error(request, f'❌ Error al corregir duplicados: {str(e)}')
    
    return redirect('ver_deudores')
@login_required
@user_passes_test(es_admin)
def eliminar_abono(request, abono_id):
    """
    🗑️ Eliminar un abono específico (opcional)
    """
    if request.method != 'POST':
        messages.error(request, "Método no permitido")
        return redirect('ver_deudores')
    
    try:
        from .models import AbonoDeuda
        
        abono = get_object_or_404(AbonoDeuda, id=abono_id)
        deuda = abono.deuda
        monto = abono.monto
        
        # ⚠️ VERIFICAR QUE LA DEUDA NO ESTÉ CERRADA
        if deuda.pagado:
            # Si está pagada, despagar
            deuda.pagado = False
            deuda.save()
        
        # 🗑️ ELIMINAR EL ABONO
        abono.delete()
        
        # 📝 REGISTRAR MOVIMIENTO CONTABLE DE REVERSA
        MovimientoContable.objects.create(
            tipo='gasto',
            concepto=f'Reversa abono: {deuda.nombre_cliente} (-${monto:,.0f})',
            monto=monto,
            usuario=request.user
        )
        
        messages.success(request, f'✅ Abono de ${monto:,.0f} eliminado correctamente')
        return redirect('ver_deudores')
        
    except Exception as e:
        print(f"Error eliminando abono: {e}")
        messages.error(request, f"Error al eliminar abono: {str(e)}")
        return redirect('ver_deudores')


@login_required
@user_passes_test(es_admin)
def reporte_deudores(request):
    """
    📊 Reporte detallado de deudores y abonos
    """
    try:
        from datetime import timedelta
        
        # 📅 PARÁMETROS DE FECHA
        hoy = timezone.now().date()
        hace_30_dias = hoy - timedelta(days=30)
        hace_7_dias = hoy - timedelta(days=7)
        
        # 📊 ESTADÍSTICAS GENERALES
        total_deudas = Deuda.objects.count()
        deudas_activas = Deuda.objects.filter(pagado=False).count()
        deudas_pagadas = Deuda.objects.filter(pagado=True).count()
        
        # 💰 MONTOS TOTALES
        monto_total_prestado = Deuda.objects.aggregate(total=Sum('monto_adeudado'))['total'] or Decimal('0.00')
        
        try:
            from .models import AbonoDeuda
            monto_total_abonos = AbonoDeuda.objects.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            
            # 📈 ABONOS POR PERÍODO
            abonos_hoy = AbonoDeuda.objects.filter(fecha_abono__date=hoy).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            abonos_semana = AbonoDeuda.objects.filter(fecha_abono__date__gte=hace_7_dias).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            abonos_mes = AbonoDeuda.objects.filter(fecha_abono__date__gte=hace_30_dias).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            
            # 📊 MÉTODOS DE PAGO MÁS USADOS EN ABONOS
            metodos_pago = AbonoDeuda.objects.values('metodo_pago').annotate(
                total=Sum('monto'),
                cantidad=Count('id')
            ).order_by('-total')
            
        except ImportError:
            monto_total_abonos = Decimal('0.00')
            abonos_hoy = Decimal('0.00')
            abonos_semana = Decimal('0.00')
            abonos_mes = Decimal('0.00')
            metodos_pago = []
        
        saldo_pendiente_total = monto_total_prestado - monto_total_abonos
        
        # 🏆 TOP DEUDORES
        top_deudores = Deuda.objects.filter(pagado=False).values(
            'nombre_cliente', 'telefono_cliente'
        ).annotate(
            total_adeudado=Sum('monto_adeudado'),
            cantidad_deudas=Count('id')
        ).order_by('-total_adeudado')[:10]
        
        context = {
            'estadisticas': {
                'total_deudas': total_deudas,
                'deudas_activas': deudas_activas,
                'deudas_pagadas': deudas_pagadas,
                'monto_total_prestado': monto_total_prestado,
                'monto_total_abonos': monto_total_abonos,
                'saldo_pendiente_total': saldo_pendiente_total,
                'tasa_recuperacion': (monto_total_abonos / monto_total_prestado * 100) if monto_total_prestado > 0 else 0,
            },
            'abonos_periodo': {
                'hoy': abonos_hoy,
                'semana': abonos_semana,
                'mes': abonos_mes,
            },
            'top_deudores': top_deudores,
            'metodos_pago': metodos_pago,
            'fecha_desde': hace_30_dias,
            'fecha_hasta': hoy,
        }
        
        return render(request, 'core/admin/reporte_deudores.html', context)
        
    except Exception as e:
        print(f"Error en reporte_deudores: {e}")
        messages.error(request, f"Error al generar reporte: {str(e)}")
        return redirect('ver_deudores')


@login_required
@user_passes_test(es_admin)
def deudores_stats_api(request):
    """
    📡 API para obtener estadísticas de deudores en tiempo real
    """
    try:
        # 📊 ESTADÍSTICAS RÁPIDAS
        total_deudores = Deuda.objects.filter(pagado=False).count()
        total_por_cobrar = Deuda.objects.filter(pagado=False).aggregate(
            total=Sum('monto_adeudado')
        )['total'] or 0
        
        try:
            from .models import AbonoDeuda
            total_abonos = AbonoDeuda.objects.aggregate(
                total=Sum('monto')
            )['total'] or 0
        except ImportError:
            total_abonos = 0
        
        # 🚨 DEUDAS VENCIDAS (más de 30 días)
        hace_30_dias = timezone.now().date() - timedelta(days=30)
        deudas_vencidas = Deuda.objects.filter(
            pagado=False,
            fecha_registro__date__lt=hace_30_dias
        ).count()
        
        return JsonResponse({
            'success': True,
            'stats': {
                'total_deudores': total_deudores,
                'total_por_cobrar': float(total_por_cobrar),
                'total_por_cobrar_formateado': f"${int(total_por_cobrar):,}".replace(',', '.'),
                'total_abonos': float(total_abonos),
                'total_abonos_formateado': f"${int(total_abonos):,}".replace(',', '.'),
                'deudas_vencidas': deudas_vencidas,
                'saldo_pendiente': float(total_por_cobrar - total_abonos),
            },
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# ========================================================================================
# 📊 ESTADÍSTICAS Y REPORTES
# ========================================================================================

@never_cache
@login_required
def estadisticas(request):
    """
    📈 Estadísticas completas del bar con análisis por períodos
    
    Features:
    - Ventas por período (hoy, semana, mes)
    - Productos más vendidos
    - Clientes frecuentes
    - Utilidades por período
    - Métodos de pago más usados
    """
    hoy = timezone.now().date()
    hace_7_dias = hoy - timedelta(days=7)
    hace_30_dias = hoy - timedelta(days=30)
    
    # 🛒 VENTAS POR PERÍODO
    ventas_hoy = Venta.objects.filter(fecha__date=hoy, cerrada=True).aggregate(
        total=Sum('total'), count=Count('id'))
    ventas_semana = Venta.objects.filter(fecha__date__gte=hace_7_dias, cerrada=True).aggregate(
        total=Sum('total'), count=Count('id'))
    ventas_mes = Venta.objects.filter(fecha__date__gte=hace_30_dias, cerrada=True).aggregate(
        total=Sum('total'), count=Count('id'))
    
    # 🏆 PRODUCTOS MÁS VENDIDOS
    productos_top = DetalleVenta.objects.filter(venta__cerrada=True)\
        .values('producto__nombre')\
        .annotate(total_vendido=Sum('cantidad'), ingresos=Sum(F('cantidad') * F('precio_unitario')))\
        .order_by('-total_vendido')[:5]
    
    # 👥 CLIENTES FRECUENTES (por teléfono en deudas)
    clientes_frecuentes = Deuda.objects.values('telefono_cliente', 'nombre_cliente')\
        .annotate(visitas=Count('id'), total_gastado=Sum('monto_adeudado'))\
        .order_by('-visitas')[:5]
    
    # 💰 UTILIDADES POR PERÍODO  
    mov_hoy = MovimientoContable.objects.filter(fecha=hoy)
    mov_semana = MovimientoContable.objects.filter(fecha__gte=hace_7_dias)
    mov_mes = MovimientoContable.objects.filter(fecha__gte=hace_30_dias)
    
    utilidad_hoy = (mov_hoy.filter(tipo='ingreso').aggregate(Sum('monto'))['monto__sum'] or 0) - \
                   (mov_hoy.filter(tipo='gasto').aggregate(Sum('monto'))['monto__sum'] or 0)
    
    utilidad_semana = (mov_semana.filter(tipo='ingreso').aggregate(Sum('monto'))['monto__sum'] or 0) - \
                      (mov_semana.filter(tipo='gasto').aggregate(Sum('monto'))['monto__sum'] or 0)
    
    utilidad_mes = (mov_mes.filter(tipo='ingreso').aggregate(Sum('monto'))['monto__sum'] or 0) - \
                   (mov_mes.filter(tipo='gasto').aggregate(Sum('monto'))['monto__sum'] or 0)
    
    # 💳 MÉTODOS DE PAGO MÁS USADOS
    metodos_pago = Venta.objects.filter(cerrada=True)\
        .values('metodo_pago')\
        .annotate(count=Count('id'), total=Sum('total'))\
        .order_by('-count')
    
    # 📊 TOTALES PARA GRÁFICAS
    total_ingresos = MovimientoContable.objects.filter(tipo='ingreso').aggregate(Sum('monto'))['monto__sum'] or 0
    total_gastos = MovimientoContable.objects.filter(tipo='gasto').aggregate(Sum('monto'))['monto__sum'] or 0
    total_por_cobrar = Deuda.objects.filter(pagado=False).aggregate(Sum('monto_adeudado'))['monto_adeudado__sum'] or 0
    
    context = {
        'ventas_hoy': ventas_hoy,
        'ventas_semana': ventas_semana, 
        'ventas_mes': ventas_mes,
        'productos_top': productos_top,
        'clientes_frecuentes': clientes_frecuentes,
        'utilidad_hoy': utilidad_hoy,
        'utilidad_semana': utilidad_semana,
        'utilidad_mes': utilidad_mes,
        'metodos_pago': metodos_pago,
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'total_por_cobrar': total_por_cobrar,
    }
    
    return render(request, 'core/estadisticas.html', context)


# ========================================================================================
# 💸 GESTIÓN DE GASTOS Y PAGOS
# ========================================================================================

@never_cache
@login_required
def gastos_dashboard(request):
    """
    💸 Dashboard principal de gastos y pagos a empleados
    
    Features:
    - Gastos generales y pagos a bartenders separados
    - Estadísticas por período
    - Formularios integrados
    - Últimos movimientos
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")

    # 📅 Estadísticas generales
    hoy = now().date()
    hace_30_dias = hoy - timedelta(days=30)
    
    # 💸 Gastos por categoría
    gastos_generales = Gasto.objects.all()
    pagos_bartender = PagoBartender.objects.all()
    
    # 📊 Totales
    total_gastos_generales = gastos_generales.aggregate(Sum('monto'))['monto__sum'] or 0
    total_pagos_bartender = pagos_bartender.aggregate(Sum('monto'))['monto__sum'] or 0
    total_gastos = total_gastos_generales + total_pagos_bartender
    
    # 📅 Gastos del mes actual
    gastos_mes = Gasto.objects.filter(fecha__gte=hace_30_dias).aggregate(Sum('monto'))['monto__sum'] or 0
    pagos_mes = PagoBartender.objects.filter(fecha_pago__gte=hace_30_dias).aggregate(Sum('monto'))['monto__sum'] or 0
    total_mes = gastos_mes + pagos_mes
    
    # 📅 Gastos de hoy
    gastos_hoy = Gasto.objects.filter(fecha=hoy).aggregate(Sum('monto'))['monto__sum'] or 0
    pagos_hoy = PagoBartender.objects.filter(fecha_pago=hoy).aggregate(Sum('monto'))['monto__sum'] or 0
    total_hoy = gastos_hoy + pagos_hoy
    
    # 📋 Últimos movimientos
    ultimos_gastos = Gasto.objects.all().order_by('-fecha')[:10]
    ultimos_pagos = PagoBartender.objects.all().order_by('-fecha_pago')[:10]
    
    # 👥 Bartenders para el formulario
    bartenders = User.objects.filter(perfil__rol='bartender')
    
    context = {
        'total_gastos': total_gastos,
        'total_gastos_generales': total_gastos_generales,
        'total_pagos_bartender': total_pagos_bartender,
        'total_mes': total_mes,
        'total_hoy': total_hoy,
        'gastos_mes': gastos_mes,
        'pagos_mes': pagos_mes,
        'gastos_hoy': gastos_hoy,
        'pagos_hoy': pagos_hoy,
        'ultimos_gastos': ultimos_gastos,
        'ultimos_pagos': ultimos_pagos,
        'bartenders': bartenders,
        'gasto_form': GastoForm(),
        'pago_form': PagoBartenderForm(),
    }
    
    return render(request, 'core/gastos.html', context)


@never_cache
@login_required
def crear_gasto(request):
    """
    ➕ Crear nuevo gasto general
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    if request.method == 'POST':
        form = GastoForm(request.POST)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.registrado_por = request.user
            gasto.save()  # Esto crea automáticamente el MovimientoContable
            messages.success(request, f'Gasto "{gasto.concepto}" registrado por ${gasto.monto:,.0f} COP')
            return redirect('gastos_dashboard')
        else:
            messages.error(request, 'Error en el formulario. Verifica los datos.')
    
    return redirect('gastos_dashboard')


@never_cache
@login_required
def crear_pago_bartender(request):
    """
    💰 Crear pago a bartender
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    if request.method == 'POST':
        form = PagoBartenderForm(request.POST)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.pagado_por = request.user
            pago.save()  # Esto crea automáticamente el MovimientoContable
            messages.success(request, f'Pago de ${pago.monto:,.0f} COP registrado para {pago.bartender.username}')
            return redirect('gastos_dashboard')
        else:
            messages.error(request, 'Error en el formulario. Verifica los datos.')
    
    return redirect('gastos_dashboard')


@never_cache
@login_required
def eliminar_gasto(request, gasto_id):
    """
    🗑️ Eliminar gasto general
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    gasto = get_object_or_404(Gasto, id=gasto_id)
    if request.method == 'POST':
        concepto = gasto.concepto
        monto = gasto.monto
        gasto.delete()
        messages.success(request, f'Gasto "{concepto}" de ${monto:,.0f} COP eliminado correctamente')
        return redirect('gastos_dashboard')
    
    return redirect('gastos_dashboard')


@never_cache
@login_required
def eliminar_pago_bartender(request, pago_id):
    """
    🗑️ Eliminar pago a bartender
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    pago = get_object_or_404(PagoBartender, id=pago_id)
    if request.method == 'POST':
        bartender = pago.bartender.username
        monto = pago.monto
        pago.delete()
        messages.success(request, f'Pago de ${monto:,.0f} COP a {bartender} eliminado correctamente')
        return redirect('gastos_dashboard')
    
    return redirect('gastos_dashboard')


# ========================================================================================
# 🔄 SISTEMA DE DEVOLUCIONES
# ========================================================================================

@never_cache
@login_required
def solicitar_devolucion(request):
    """
    🔄 FUNCIÓN CORREGIDA: Solicitar devolución con múltiples orígenes
    """
    perfil = request.user.perfil
    if perfil.rol not in ['bartender', 'admin']:
        return HttpResponseForbidden("Acceso denegado")
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            producto_id = request.POST.get('producto')
            cantidad = int(request.POST.get('cantidad', 0))
            tipo = request.POST.get('tipo', 'cliente')
            razon = request.POST.get('razon')
            observaciones = request.POST.get('observaciones', '')
            
            # Orígenes opcionales
            venta_origen_id = request.POST.get('venta_origen') or None
            factura_origen_id = request.POST.get('factura_origen') or None
            
            # Validaciones
            producto = get_object_or_404(Producto, id=producto_id)
            
            if cantidad <= 0:
                messages.error(request, "La cantidad debe ser mayor a cero.")
                return redirect('solicitar_devolucion')
            
            if cantidad > producto.cantidad:
                messages.error(request, f"No hay suficiente stock. Disponible: {producto.cantidad}")
                return redirect('solicitar_devolucion')
            
            # Validar origen según tipo
            venta_origen = None
            factura_origen = None
            
            if tipo == 'cliente':
                if venta_origen_id:
                    venta_origen = get_object_or_404(Venta, id=venta_origen_id)
            elif tipo in ['inventario', 'proveedor']:
                if factura_origen_id:
                    factura_origen = get_object_or_404(FacturaCompra, id=factura_origen_id)
            
            # Crear devolución
            devolucion = Devolucion.objects.create(
                producto=producto,
                cantidad=cantidad,
                tipo=tipo,
                razon=razon,
                observaciones=observaciones,
                solicitada_por=request.user,
                venta_origen=venta_origen,
                factura_origen=factura_origen
            )
            
            # Mensaje según tipo
            if tipo == 'cliente':
                impacto = "Se sumará al inventario una vez autorizada"
                origen_msg = f" (Venta: Mesa {venta_origen.mesa.numero})" if venta_origen else ""
            elif tipo == 'inventario':
                impacto = "Se registrará como pérdida de inventario"
                origen_msg = f" (Factura: {factura_origen.numero_factura})" if factura_origen else ""
            else:  # proveedor
                impacto = "Se tramitará devolución al proveedor"
                origen_msg = f" (Factura: {factura_origen.numero_factura})" if factura_origen else ""
            
            messages.success(
                request,
                f'Solicitud de devolución enviada: {cantidad} x {producto.nombre}{origen_msg}. {impacto}.'
            )
            
            return redirect('mis_devoluciones')
            
        except Exception as e:
            print(f"Error en solicitar_devolucion: {e}")
            messages.error(request, f"Error al procesar la solicitud: {str(e)}")
    
    # Obtener datos para el formulario
    productos = Producto.objects.all().order_by('nombre')
    
    # Ventas recientes del usuario para devoluciones de cliente
    ventas_recientes = None
    if request.user.perfil.rol in ['bartender', 'admin']:
        ventas_recientes = Venta.objects.filter(
            mesero=request.user,
            cerrada=True,
            fecha__date__gte=timezone.now().date() - timedelta(days=30)
        ).select_related('mesa').order_by('-fecha')[:20]
    
    # Facturas recientes para devoluciones de inventario/proveedor
    facturas_recientes = None
    if request.user.perfil.rol == 'admin':
        facturas_recientes = FacturaCompra.objects.filter(
            estado__in=['recibida', 'pagada'],
            fecha_factura__gte=timezone.now().date() - timedelta(days=90)
        ).select_related('proveedor').order_by('-fecha_factura')[:30]
    
    context = {
        'productos': productos,
        'ventas_recientes': ventas_recientes,
        'facturas_recientes': facturas_recientes,
        'tipos_devolucion': Devolucion.TIPO_CHOICES,
        'razones_devolucion': Devolucion.RAZON_CHOICES,
    }
    
    return render(request, 'core/devoluciones/solicitar_mejorado.html', context)


@never_cache
@login_required
def mis_devoluciones(request):
    """
    📋 Ver mis solicitudes de devolución (bartender)
    """
    perfil = request.user.perfil
    if perfil.rol not in ['bartender', 'admin']:
        return HttpResponseForbidden("Acceso denegado")
    
    devoluciones = Devolucion.objects.filter(
        solicitada_por=request.user
    ).select_related(
        'producto', 'producto__categoria', 'autorizada_por', 'venta_origen'
    ).order_by('-fecha_solicitud')
    
    context = {
        'devoluciones': devoluciones,
        'title': 'Mis Solicitudes de Devolución'
    }
    
    return render(request, 'core/devoluciones/mis_devoluciones.html', context)



@never_cache
@login_required
def gestionar_devoluciones(request):
    """
    🛠️ FUNCIÓN CORREGIDA: Admin gestiona devoluciones con múltiples tipos
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    # Filtros
    filtro_tipo = request.GET.get('tipo', 'todas')
    filtro_estado = request.GET.get('estado', 'pendiente')
    
    # Base queryset
    devoluciones_base = Devolucion.objects.select_related(
        'producto', 'producto__categoria', 'solicitada_por', 
        'autorizada_por', 'venta_origen', 'venta_origen__mesa',
        'factura_origen', 'factura_origen__proveedor'
    )
    
    # Aplicar filtros
    if filtro_tipo != 'todas':
        devoluciones_base = devoluciones_base.filter(tipo=filtro_tipo)
    
    if filtro_estado == 'pendiente':
        devoluciones = devoluciones_base.filter(estado='pendiente')
    elif filtro_estado == 'procesadas':
        devoluciones = devoluciones_base.exclude(estado='pendiente')
    else:
        devoluciones = devoluciones_base.filter(estado=filtro_estado)
    
    devoluciones = devoluciones.order_by('-fecha_solicitud')
    
    # Estadísticas
    stats = {
        'pendientes_cliente': devoluciones_base.filter(tipo='cliente', estado='pendiente').count(),
        'pendientes_inventario': devoluciones_base.filter(tipo='inventario', estado='pendiente').count(),
        'pendientes_proveedor': devoluciones_base.filter(tipo='proveedor', estado='pendiente').count(),
        'total_procesadas': devoluciones_base.filter(estado='procesada').count(),
        'total_rechazadas': devoluciones_base.filter(estado='rechazada').count(),
    }
    
    context = {
        'devoluciones': devoluciones,
        'stats': stats,
        'filtro_tipo': filtro_tipo,
        'filtro_estado': filtro_estado,
        'tipos_disponibles': Devolucion.TIPO_CHOICES,
    }
    
    return render(request, 'core/devoluciones/gestionar_mejorado.html', context)
@never_cache
@login_required
def autorizar_devolucion(request, devolucion_id):
    """
    ✅ Admin autoriza o rechaza una devolución
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    devolucion = get_object_or_404(
        Devolucion.objects.select_related(
            'producto', 'producto__categoria', 'solicitada_por', 'venta_origen'
        ), 
        id=devolucion_id
    )
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        comentario = request.POST.get('comentario_admin', '')
        
        if accion == 'autorizar':
            devolucion.estado = 'autorizada'
            devolucion.comentario_admin = comentario
            devolucion.autorizada_por = request.user
            devolucion.fecha_autorizacion = now()
            devolucion.save()
            
            # 📋 MENSAJE SEGÚN TIPO
            if devolucion.tipo == 'cliente':
                impacto_msg = "El producto se sumará al inventario cuando se procese"
            else:
                impacto_msg = "Se registrará como pérdida de inventario cuando se procese"
            
            messages.success(
                request, 
                f'Devolución de {devolucion.get_tipo_display().lower()} autorizada: '
                f'{devolucion.producto.nombre} ({devolucion.cantidad} unidades). '
                f'{impacto_msg}.'
            )
            
        elif accion == 'rechazar':
            devolucion.estado = 'rechazada'
            devolucion.comentario_admin = comentario
            devolucion.autorizada_por = request.user
            devolucion.fecha_autorizacion = now()
            devolucion.save()
            
            messages.info(
                request, 
                f'Devolución de {devolucion.get_tipo_display().lower()} rechazada: '
                f'{devolucion.producto.nombre} ({devolucion.cantidad} unidades).'
            )
        
        return redirect('gestionar_devoluciones')
    
    return render(request, 'core/devoluciones/autorizar.html', {'devolucion': devolucion})


@never_cache
@login_required
def procesar_devolucion(request, devolucion_id):
    """
    ⚙️ Admin procesa una devolución autorizada
    
    Features:
    - Procesamiento automático según tipo
    - Actualización de inventario para devoluciones de cliente
    - Registro contable automático
    - Cálculos de pérdidas y recuperaciones
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    devolucion = get_object_or_404(
        Devolucion.objects.select_related(
            'producto', 'autorizada_por'
        ), 
        id=devolucion_id
    )
    
    if devolucion.estado != 'autorizada':
        messages.error(request, 'Solo se pueden procesar devoluciones autorizadas.')
        return redirect('gestionar_devoluciones')
    
    if request.method == 'POST':
        try:
            # 🔄 EL PROCESAMIENTO SE HACE AUTOMÁTICAMENTE EN EL MODELO
            devolucion.estado = 'procesada'
            devolucion.save()  # Esto activa el método procesar_devolucion() del modelo
            
            # 📋 MENSAJE ESPECÍFICO SEGÚN TIPO DE DEVOLUCIÓN
            if devolucion.tipo == 'cliente':
                messages.success(
                    request, 
                    f'Devolución de cliente procesada exitosamente. '
                    f'Se devolvieron {devolucion.cantidad} unidades de {devolucion.producto.nombre} al inventario. '
                    f'Pérdida de venta: ${devolucion.valor_venta_perdida:,.0f} COP. '
                    f'Recuperación de inventario: ${devolucion.valor_total:,.0f} COP.'
                )
            else:  # inventario
                messages.success(
                    request, 
                    f'Devolución de inventario procesada exitosamente. '
                    f'Se registró la pérdida de {devolucion.cantidad} unidades de {devolucion.producto.nombre}. '
                    f'Pérdida total: ${devolucion.valor_total:,.0f} COP.'
                )
            
        except Exception as e:
            messages.error(request, f'Error al procesar la devolución: {str(e)}')
            print(f"Error procesando devolución {devolucion_id}: {e}")
        
        return redirect('gestionar_devoluciones')
    
    return render(request, 'core/devoluciones/procesar.html', {'devolucion': devolucion})


@never_cache
@login_required
def devoluciones_api_pendientes(request):
    """
    ⚡ API para obtener cantidad de devoluciones pendientes
    """
    try:
        # 🔍 VERIFICAR QUE EL USUARIO TENGA PERFIL
        if not hasattr(request.user, 'perfil'):
            return JsonResponse({'error': 'Usuario sin perfil'}, status=403)
        
        # 🔒 SOLO ADMIN PUEDE VER DEVOLUCIONES PENDIENTES
        if request.user.perfil.rol != 'admin':
            return JsonResponse({'error': 'Acceso denegado - Solo administradores'}, status=403)
        
        # 📊 CONTAR DEVOLUCIONES PENDIENTES POR TIPO
        pendientes_cliente = Devolucion.objects.filter(
            estado='pendiente', tipo='cliente'
        ).count()
        
        pendientes_inventario = Devolucion.objects.filter(
            estado='pendiente', tipo='inventario'
        ).count()
        
        total_pendientes = pendientes_cliente + pendientes_inventario
        
        return JsonResponse({
            'success': True,
            'pendientes': total_pendientes,
            'pendientes_cliente': pendientes_cliente,
            'pendientes_inventario': pendientes_inventario
        })
        
    except Exception as e:
        print(f"Error en devoluciones_api_pendientes: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'pendientes': 0
        }, status=500)


@never_cache
@login_required
def estadisticas_devoluciones(request):
    """
    📊 Vista con estadísticas detalladas de devoluciones
    
    Features:
    - Estadísticas generales y por tipo
    - Devoluciones recientes
    - Productos más devueltos
    - Razones más comunes
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    from datetime import timedelta
    from django.db.models import Sum, Count, Avg
    from django.utils import timezone
    
    # 📅 Fechas para análisis
    hoy = timezone.now().date()
    hace_30_dias = hoy - timedelta(days=30)
    hace_7_dias = hoy - timedelta(days=7)
    
    # 📊 ESTADÍSTICAS GENERALES
    stats_generales = {
        'total_devoluciones': Devolucion.objects.count(),
        'procesadas': Devolucion.objects.filter(estado='procesada').count(),
        'pendientes': Devolucion.objects.filter(estado='pendiente').count(),
        'rechazadas': Devolucion.objects.filter(estado='rechazada').count(),
    }
    
    # 📊 ESTADÍSTICAS POR TIPO
    stats_por_tipo = {
        'cliente': {
            'total': Devolucion.objects.filter(tipo='cliente').count(),
            'procesadas': Devolucion.objects.filter(tipo='cliente', estado='procesada').count(),
            'valor_total': Devolucion.objects.filter(
                tipo='cliente', estado='procesada'
            ).aggregate(total=Sum('valor_total'))['total'] or 0,
            'valor_venta_perdida': Devolucion.objects.filter(
                tipo='cliente', estado='procesada'
            ).aggregate(total=Sum('valor_venta_perdida'))['total'] or 0,
        },
        'inventario': {
            'total': Devolucion.objects.filter(tipo='inventario').count(),
            'procesadas': Devolucion.objects.filter(tipo='inventario', estado='procesada').count(),
            'valor_total': Devolucion.objects.filter(
                tipo='inventario', estado='procesada'
            ).aggregate(total=Sum('valor_total'))['total'] or 0,
        }
    }
    
    # 📋 DEVOLUCIONES RECIENTES (ÚLTIMOS 30 DÍAS)
    devoluciones_recientes = Devolucion.objects.filter(
        fecha_solicitud__date__gte=hace_30_dias
    ).select_related('producto', 'solicitada_por').order_by('-fecha_solicitud')
    
    # 🏆 PRODUCTOS MÁS DEVUELTOS
    productos_mas_devueltos = Devolucion.objects.filter(
        estado='procesada'
    ).values(
        'producto__nombre', 'tipo'
    ).annotate(
        cantidad_total=Sum('cantidad'),
        numero_devoluciones=Count('id'),
        valor_total=Sum('valor_total')
    ).order_by('-cantidad_total')[:10]
    
    # 📊 RAZONES MÁS COMUNES
    razones_comunes = Devolucion.objects.values(
        'razon', 'tipo'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    context = {
        'stats_generales': stats_generales,
        'stats_por_tipo': stats_por_tipo,
        'devoluciones_recientes': devoluciones_recientes,
        'productos_mas_devueltos': productos_mas_devueltos,
        'razones_comunes': razones_comunes,
        'fecha_desde': hace_30_dias,
        'fecha_hasta': hoy,
    }
    
    return render(request, 'core/devoluciones/estadisticas.html', context)

# ========================================================================================
# 🧾 SISTEMA DE FACTURAS COMPLETO Y CORREGIDO - SOLO ESTAS FUNCIONES
# ========================================================================================
# REEMPLAZAR SOLO LAS FUNCIONES DE FACTURAS EN TU views.py CON ESTAS
# NO TOCAR NADA MÁS DEL ARCHIVO

# ========================================================================================
# 🏪 GESTIÓN DE PROVEEDORES
# ========================================================================================

@never_cache
@login_required
def proveedores_listar(request):
    """
    📋 Lista todos los proveedores
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    
    # Estadísticas
    total_proveedores = proveedores.count()
    proveedores_con_facturas = proveedores.filter(facturacompra__isnull=False).distinct().count()
    
    context = {
        'proveedores': proveedores,
        'total_proveedores': total_proveedores,
        'proveedores_con_facturas': proveedores_con_facturas,
    }
    
    return render(request, 'core/facturas/proveedores_listar.html', context)


@never_cache
@login_required
def proveedor_crear(request):
    """
    ➕ Crear nuevo proveedor
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            proveedor = form.save()
            messages.success(request, f'✅ Proveedor "{proveedor.nombre}" creado correctamente.')
            return redirect('proveedores_listar')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    field_name = form.fields[field].label or field
                    messages.error(request, f"Error en {field_name}: {error}")
    else:
        form = ProveedorForm()
    
    return render(request, 'core/facturas/proveedor_form.html', {
        'form': form, 
        'titulo': 'Crear Proveedor'
    })


@never_cache
@login_required
def proveedor_editar(request, pk):
    """
    ✏️ Editar proveedor existente
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    proveedor = get_object_or_404(Proveedor, pk=pk)
    
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            proveedor = form.save()
            messages.success(request, f'✅ Proveedor "{proveedor.nombre}" actualizado correctamente.')
            return redirect('proveedores_listar')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    field_name = form.fields[field].label or field
                    messages.error(request, f"Error en {field_name}: {error}")
    else:
        form = ProveedorForm(instance=proveedor)
    
    return render(request, 'core/facturas/proveedor_form.html', {
        'form': form, 
        'titulo': 'Editar Proveedor',
        'proveedor': proveedor
    })


@never_cache
@login_required
def proveedor_eliminar(request, pk):
    """
    🗑️ Eliminar proveedor
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    proveedor = get_object_or_404(Proveedor, pk=pk)
    
    # Verificar si tiene facturas asociadas
    if proveedor.facturacompra_set.exists():
        messages.error(
            request, 
            f'❌ No se puede eliminar el proveedor "{proveedor.nombre}" porque tiene facturas asociadas.'
        )
        return redirect('proveedores_listar')
    
    if request.method == 'POST':
        nombre_proveedor = proveedor.nombre
        proveedor.delete()
        messages.success(request, f'✅ Proveedor "{nombre_proveedor}" eliminado correctamente.')
        return redirect('proveedores_listar')
    
    return render(request, 'core/facturas/confirmar_eliminar_proveedor.html', {
        'proveedor': proveedor
    })


@never_cache
@login_required
def proveedor_detalle(request, pk):
    """
    👁️ Ver detalles del proveedor con sus facturas
    """
    proveedor = get_object_or_404(Proveedor, pk=pk)
    
    # Facturas del proveedor
    facturas = FacturaCompra.objects.filter(proveedor=proveedor).select_related(
        'registrada_por'
    ).order_by('-fecha_factura')
    
    # Estadísticas del proveedor
    total_facturas = facturas.count()
    total_comprado = facturas.aggregate(total=Sum('total'))['total'] or 0
    facturas_pendientes = facturas.filter(estado='pendiente').count()
    promedio_por_factura = total_comprado / total_facturas if total_facturas > 0 else 0
    
    context = {
        'proveedor': proveedor,
        'facturas': facturas[:20],  # Mostrar las últimas 20
        'total_facturas': total_facturas,
        'total_comprado': total_comprado,
        'facturas_pendientes': facturas_pendientes,
        'promedio_por_factura': promedio_por_factura,
    }
    
    return render(request, 'core/facturas/proveedor_detalle.html', context)


# ========================================================================================
# 🧾 GESTIÓN DE FACTURAS
# ========================================================================================

@never_cache
@login_required
def facturas_dashboard(request):
    """
    🏠 Dashboard principal de facturas con estadísticas completas
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    try:
        from datetime import timedelta
        from django.db.models import Sum, Count, Q
        
        hoy = timezone.now().date()
        hace_30_dias = hoy - timedelta(days=30)
        hace_7_dias = hoy - timedelta(days=7)
        
        # 📊 ESTADÍSTICAS PRINCIPALES
        stats = {
            'facturas_pendientes': FacturaCompra.objects.filter(estado='pendiente').count(),
            'facturas_recibidas': FacturaCompra.objects.filter(estado='recibida').count(),
            'facturas_pagadas': FacturaCompra.objects.filter(estado='pagada').count(),
            'facturas_anuladas': FacturaCompra.objects.filter(estado='anulada').count(),
            'facturas_vencidas': FacturaCompra.objects.filter(
                estado__in=['pendiente', 'recibida'],
                fecha_vencimiento__lt=hoy
            ).count(),
            'total_por_pagar': FacturaCompra.objects.filter(
                estado__in=['pendiente', 'recibida']
            ).aggregate(total=Sum('total'))['total'] or 0,
            'facturas_mes': FacturaCompra.objects.filter(
                fecha_factura__gte=hace_30_dias
            ).count(),
        }
        
        # 🧾 FACTURAS RECIENTES (últimas 10)
        facturas_recientes = FacturaCompra.objects.select_related(
            'proveedor'
        ).order_by('-fecha_factura', '-id')[:10]
        
        # 🚨 FACTURAS VENCIDAS (para alertas)
        facturas_vencidas = FacturaCompra.objects.filter(
            estado__in=['pendiente', 'recibida'],
            fecha_vencimiento__lt=hoy
        ).select_related('proveedor')[:5]
        
        # 📦 PRODUCTOS CON STOCK BAJO
        stock_bajo = Producto.objects.filter(cantidad__lte=5)[:10]
        
        # 🏪 PROVEEDORES RECIENTES
        proveedores_recientes = Proveedor.objects.filter(
            activo=True
        ).order_by('-id')[:5]
        
        context = {
            'stats': stats,
            'facturas_recientes': facturas_recientes,
            'facturas_vencidas': facturas_vencidas,
            'stock_bajo': stock_bajo,
            'proveedores_recientes': proveedores_recientes,
            'hoy': hoy,
        }
        
        return render(request, 'core/facturas/dashboard.html', context)
        
    except Exception as e:
        print(f"Error en facturas_dashboard: {e}")
        messages.error(request, f"Error al cargar el dashboard: {str(e)}")
        return redirect('admin_dashboard')


@never_cache
@login_required
def facturas_listar(request):
    """
    📋 Lista todas las facturas con filtros avanzados
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    # Obtener todas las facturas ordenadas por fecha
    facturas = FacturaCompra.objects.select_related('proveedor').order_by('-fecha_factura')
    
    # Aplicar filtros si existen
    filtro_estado = request.GET.get('estado')
    if filtro_estado:
        if filtro_estado == 'vencida':
            # Filtro especial para facturas vencidas
            hoy = timezone.now().date()
            facturas = facturas.filter(
                estado__in=['pendiente', 'recibida'],
                fecha_vencimiento__lt=hoy
            )
        elif filtro_estado in ['pendiente', 'recibida', 'pagada', 'anulada']:
            facturas = facturas.filter(estado=filtro_estado)
    
    # Estadísticas rápidas
    total_facturas = facturas.count()
    
    # Paginación
    from django.core.paginator import Paginator
    paginator = Paginator(facturas, 20)
    page_number = request.GET.get('page')
    facturas_paginadas = paginator.get_page(page_number)
    
    context = {
        'facturas': facturas_paginadas,
        'total_facturas': total_facturas,
        'filtro_estado': filtro_estado,
    }
    
    return render(request, 'core/facturas/facturas_listar.html', context)


@never_cache
@login_required
def factura_crear(request):
    """
    ➕ Crear nueva factura de compra
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    if request.method == 'POST':
        form = FacturaCompraForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                factura = form.save(commit=False)
                factura.registrada_por = request.user
                factura.save()
                
                messages.success(
                    request, 
                    f'✅ Factura "{factura.numero_factura}" creada correctamente. '
                    f'Ahora puedes agregar productos.'
                )
                return redirect('factura_detalle', pk=factura.pk)
                
            except Exception as e:
                messages.error(request, f'❌ Error al crear la factura: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"❌ Error en {field}: {error}")
    else:
        form = FacturaCompraForm()
    
    return render(request, 'core/facturas/factura_form.html', {
        'form': form,
        'titulo': 'Crear Factura'
    })


@never_cache
@login_required
def factura_detalle(request, pk):
    """
    👁️ Ver detalles completos de una factura
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    factura = get_object_or_404(
        FacturaCompra.objects.select_related('proveedor', 'registrada_por'),
        pk=pk
    )
    
    # Obtener detalles de la factura
    detalles = factura.detalles.select_related('producto').order_by('id')
    
    # Obtener pagos de la factura
    pagos = factura.pagos.select_related('registrado_por').order_by('-fecha_pago')
    
    # Calcular totales
    total_pagos = pagos.aggregate(total=Sum('monto'))['total'] or 0
    saldo_pendiente = factura.total - total_pagos
    
    # Formulario para agregar productos
    form_detalle = DetalleFacturaForm()
    
    # Productos disponibles para enlazar
    productos_disponibles = Producto.objects.all().order_by('nombre')
    
    context = {
        'factura': factura,
        'detalles': detalles,
        'pagos': pagos,
        'total_pagos': total_pagos,
        'saldo_pendiente': saldo_pendiente,
        'form_detalle': form_detalle,
        'productos_disponibles': productos_disponibles,
        'puede_editar': factura.estado in ['pendiente'],
    }
    
    return render(request, 'core/facturas/detalle.html', context)


@never_cache
@login_required
def factura_editar(request, pk):
    """
    ✏️ Editar factura existente
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    factura = get_object_or_404(FacturaCompra, pk=pk)
    
    # Solo se pueden editar facturas pendientes
    if factura.estado not in ['pendiente']:
        messages.error(request, '❌ Solo se pueden editar facturas pendientes.')
        return redirect('factura_detalle', pk=pk)
    
    if request.method == 'POST':
        form = FacturaCompraForm(request.POST, request.FILES, instance=factura)
        if form.is_valid():
            factura = form.save()
            messages.success(request, f'✅ Factura "{factura.numero_factura}" actualizada correctamente.')
            return redirect('factura_detalle', pk=pk)
    else:
        form = FacturaCompraForm(instance=factura)
    
    return render(request, 'core/facturas/factura_form.html', {
        'form': form,
        'titulo': 'Editar Factura',
        'factura': factura
    })


@never_cache
@login_required
def factura_agregar_detalle(request, pk):
    """
    📝 Agregar producto a una factura
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    factura = get_object_or_404(FacturaCompra, pk=pk)
    
    if factura.estado not in ['pendiente']:
        messages.error(request, '❌ Solo se pueden agregar productos a facturas pendientes.')
        return redirect('factura_detalle', pk=pk)
    
    if request.method == 'POST':
        form = DetalleFacturaForm(request.POST)
        if form.is_valid():
            try:
                detalle = form.save(commit=False)
                detalle.factura = factura
                
                # Calcular subtotal
                detalle.subtotal = detalle.cantidad * detalle.precio_unitario
                detalle.save()
                
                # Recalcular totales de la factura
                total_detalles = factura.detalles.aggregate(
                    subtotal=Sum('subtotal')
                )['subtotal'] or Decimal('0.00')
                
                factura.subtotal = total_detalles
                factura.total = factura.subtotal + factura.iva - factura.descuento
                factura.save()
                
                messages.success(
                    request, 
                    f'✅ Producto "{detalle.nombre_producto}" agregado a la factura. '
                    f'Subtotal: ${detalle.subtotal:,.0f} COP'
                )
                
            except Exception as e:
                messages.error(request, f'❌ Error al agregar el producto: {str(e)}')
    
    return redirect('factura_detalle', pk=pk)


@never_cache
@login_required
def factura_eliminar_detalle(request, detalle_id):
    """
    🗑️ Eliminar detalle de factura
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    detalle = get_object_or_404(DetalleFacturaCompra, id=detalle_id)
    factura = detalle.factura
    
    if factura.estado not in ['pendiente']:
        messages.error(request, '❌ Solo se pueden eliminar productos de facturas pendientes.')
        return redirect('factura_detalle', pk=factura.pk)
    
    if request.method == 'POST':
        nombre_producto = detalle.nombre_producto
        detalle.delete()
        
        # Recalcular totales de la factura
        total_detalles = factura.detalles.aggregate(
            subtotal=Sum('subtotal')
        )['subtotal'] or Decimal('0.00')
        
        factura.subtotal = total_detalles
        factura.total = factura.subtotal + factura.iva - factura.descuento
        factura.save()
        
        messages.success(request, f'✅ Producto "{nombre_producto}" eliminado de la factura.')
    
    return redirect('factura_detalle', pk=factura.pk)


@never_cache
@login_required
def enlazar_producto_factura(request, detalle_id):
    """
    🔗 Enlazar un detalle de factura con un producto del inventario
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    detalle = get_object_or_404(DetalleFacturaCompra, id=detalle_id)
    
    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        if producto_id:
            try:
                producto = Producto.objects.get(id=producto_id)
                detalle.producto = producto
                detalle.save()
                
                messages.success(
                    request,
                    f'✅ Producto "{detalle.nombre_producto}" enlazado con "{producto.nombre}" del inventario.'
                )
            except Producto.DoesNotExist:
                messages.error(request, '❌ Producto no encontrado.')
    
    return redirect('factura_detalle', pk=detalle.factura.pk)


@never_cache
@login_required
def factura_cambiar_estado(request, pk):
    """
    🔄 Cambiar estado de una factura - CON INTEGRACIÓN AL INVENTARIO
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    factura = get_object_or_404(FacturaCompra, pk=pk)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        
        if nuevo_estado in ['pendiente', 'recibida', 'pagada', 'anulada']:
            estado_anterior = factura.estado
            factura.estado = nuevo_estado
            
            # 📦 SI SE MARCA COMO RECIBIDA, APLICAR AL INVENTARIO AUTOMÁTICAMENTE
            if nuevo_estado == 'recibida' and estado_anterior != 'recibida':
                try:
                    resultado = procesar_factura_al_inventario(factura)
                    if resultado['success']:
                        messages.success(
                            request,
                            f'✅ Factura marcada como recibida y aplicada al inventario exitosamente. '
                            f'{resultado["productos_actualizados"]} productos actualizados, '
                            f'{resultado["productos_nuevos"]} productos nuevos creados.'
                        )
                    else:
                        messages.warning(
                            request,
                            f'⚠️ Factura marcada como recibida pero hubo errores al aplicar al inventario: '
                            f'{resultado["error"]}'
                        )
                except Exception as e:
                    messages.error(request, f'❌ Error al aplicar la factura al inventario: {str(e)}')
            
            factura.save()
            
            if nuevo_estado != 'recibida' or estado_anterior == 'recibida':
                messages.success(
                    request, 
                    f'✅ Estado de la factura cambiado de "{estado_anterior}" a "{nuevo_estado}".'
                )
    
    return redirect('factura_detalle', pk=pk)


@never_cache
@login_required
def factura_aplicar_inventario(request, pk):
    """
    📦 Aplicar factura al inventario manualmente
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    factura = get_object_or_404(FacturaCompra, pk=pk)
    
    if factura.estado != 'recibida':
        messages.error(request, '❌ Solo se pueden aplicar facturas con estado "recibida".')
        return redirect('factura_detalle', pk=pk)
    
    if request.method == 'POST':
        try:
            resultado = procesar_factura_al_inventario(factura)
            if resultado['success']:
                messages.success(
                    request,
                    f'✅ Factura aplicada al inventario exitosamente. '
                    f'{resultado["productos_actualizados"]} productos actualizados, '
                    f'{resultado["productos_nuevos"]} productos nuevos creados.'
                )
            else:
                messages.error(request, f'❌ Error al aplicar la factura: {resultado["error"]}')
        except Exception as e:
            messages.error(request, f'❌ Error al aplicar la factura al inventario: {str(e)}')
    
    return redirect('factura_detalle', pk=pk)


@never_cache
@login_required
def factura_registrar_pago(request, pk):
    """
    💰 Registrar pago a una factura
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    factura = get_object_or_404(FacturaCompra, pk=pk)
    
    if request.method == 'POST':
        try:
            monto = Decimal(request.POST.get('monto', '0'))
            metodo_pago = request.POST.get('metodo_pago')
            referencia = request.POST.get('referencia', '')
            observaciones = request.POST.get('observaciones', '')
            
            # Crear registro de pago
            PagoFactura.objects.create(
                factura=factura,
                monto=monto,
                metodo_pago=metodo_pago,
                referencia=referencia,
                observaciones=observaciones,
                registrado_por=request.user
            )
            
            # Si el pago cubre el total, marcar como pagada
            total_pagos = factura.pagos.aggregate(total=Sum('monto'))['total'] or 0
            if total_pagos >= factura.total:
                factura.estado = 'pagada'
                factura.pagada_por = request.user
                factura.fecha_pago = timezone.now()
                factura.save()
            
            messages.success(request, f'✅ Pago de ${monto:,.0f} COP registrado correctamente.')
            
        except Exception as e:
            messages.error(request, f'❌ Error al registrar el pago: {str(e)}')
    
    return redirect('factura_detalle', pk=pk)


# ========================================================================================
# 📊 REPORTES DE FACTURAS
# ========================================================================================

@never_cache
@login_required
def facturas_reportes(request):
    """
    📊 Vista de reportes de facturas
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    context = {
        'titulo': 'Reportes de Facturas',
        'reportes_disponibles': [
            {
                'nombre': 'Análisis de Rentabilidad',
                'url': 'reporte_ventas_facturas',
                'descripcion': 'Conecta ventas con facturas para análisis de rentabilidad'
            },
        ]
    }
    
    return render(request, 'core/facturas/reportes.html', context)


@never_cache
@login_required
def reporte_ventas_facturas(request):
    """
    📊 Reporte que conecta ventas con facturas de compra
    
    Features:
    - Análisis de rentabilidad por producto
    - Conexión entre compras y ventas
    - Márgenes de ganancia reales
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    try:
        from datetime import timedelta
        from django.db.models import Sum, Avg, Count, F
        
        # 📅 Parámetros de fecha
        hoy = timezone.now().date()
        hace_30_dias = hoy - timedelta(days=30)
        
        # 🛒 ANÁLISIS DE COMPRAS VS VENTAS
        productos_analysis = []
        
        for producto in Producto.objects.all():
            # Compras (desde facturas)
            compras_facturas = DetalleFacturaCompra.objects.filter(
                producto=producto,
                factura__estado__in=['pagada', 'recibida'],
                factura__fecha_factura__gte=hace_30_dias
            ).aggregate(
                total_comprado=Sum('cantidad'),
                costo_total=Sum('subtotal')
            )
            
            # Ventas
            ventas_producto = DetalleVenta.objects.filter(
                producto=producto,
                venta__cerrada=True,
                venta__fecha__date__gte=hace_30_dias
            ).aggregate(
                total_vendido=Sum('cantidad'),
                ingresos_total=Sum(F('cantidad') * F('precio_unitario'))
            )
            
            total_comprado = compras_facturas['total_comprado'] or 0
            costo_total = compras_facturas['costo_total'] or 0
            total_vendido = ventas_producto['total_vendido'] or 0
            ingresos_total = ventas_producto['ingresos_total'] or 0
            
            if total_comprado > 0 or total_vendido > 0:
                # Calcular rentabilidad
                ganancia_bruta = float(ingresos_total or 0) - float(costo_total or 0)
                margen_rentabilidad = (ganancia_bruta / float(ingresos_total or 1)) * 100 if ingresos_total else 0
                
                productos_analysis.append({
                    'producto': producto,
                    'total_comprado': total_comprado,
                    'costo_total': float(costo_total or 0),
                    'total_vendido': total_vendido,
                    'ingresos_total': float(ingresos_total or 0),
                    'ganancia_bruta': ganancia_bruta,
                    'margen_rentabilidad': round(margen_rentabilidad, 2),
                    'stock_actual': producto.cantidad,
                    'rotacion': round((total_vendido / (producto.cantidad + total_vendido)) * 100, 1) if (producto.cantidad + total_vendido) > 0 else 0
                })
        
        # Ordenar por rentabilidad
        productos_analysis.sort(key=lambda x: x['ganancia_bruta'], reverse=True)
        
        # 📊 RESUMEN GENERAL
        resumen = {
            'total_inversion': sum(p['costo_total'] for p in productos_analysis),
            'total_ingresos': sum(p['ingresos_total'] for p in productos_analysis),
            'ganancia_total': sum(p['ganancia_bruta'] for p in productos_analysis),
            'productos_analizados': len(productos_analysis),
            'margen_promedio': sum(p['margen_rentabilidad'] for p in productos_analysis) / len(productos_analysis) if productos_analysis else 0
        }
        
        context = {
            'productos_analysis': productos_analysis[:50],  # Top 50
            'resumen': resumen,
            'fecha_desde': hace_30_dias,
            'fecha_hasta': hoy,
        }
        
        return render(request, 'core/facturas/reporte_rentabilidad.html', context)
        
    except Exception as e:
        print(f"Error en reporte_ventas_facturas: {e}")
        messages.error(request, f"❌ Error al generar el reporte: {str(e)}")
        return redirect('facturas_dashboard')


# ========================================================================================
# 🔗 APIs PARA FACTURAS
# ========================================================================================

@never_cache
@login_required
def producto_info_api_facturas(request, pk):
    """
    📡 API para obtener información del producto para facturas
    """
    try:
        producto = get_object_or_404(Producto, pk=pk)
        
        data = {
            'id': producto.id,
            'nombre': producto.nombre,
            'cantidad': producto.cantidad,
            'precio_costo': float(producto.precio_costo),
            'precio': float(producto.precio),
            'stock_bajo': producto.stock_bajo(),
            'estado_stock': producto.estado_stock(),
            'categoria': producto.categoria.nombre if producto.categoria else None,
        }
        
        return JsonResponse({
            'success': True,
            'producto': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@never_cache
@login_required
def dashboard_stats_api(request):
    """
    📊 API para estadísticas del dashboard en tiempo real
    """
    try:
        from django.db.models import Sum, Count
        from datetime import timedelta
        
        hoy = timezone.now().date()
        hace_7_dias = hoy - timedelta(days=7)
        
        # 📊 Estadísticas rápidas
        stats = {
            # Facturas
            'facturas_pendientes': FacturaCompra.objects.filter(estado='pendiente').count(),
            'facturas_vencidas': FacturaCompra.objects.filter(
                estado__in=['pendiente', 'recibida'],
                fecha_vencimiento__lt=hoy
            ).count(),
            'total_por_pagar': float(FacturaCompra.objects.filter(
                estado__in=['pendiente', 'recibida']
            ).aggregate(total=Sum('total'))['total'] or 0),
            
            # Ventas de la semana
            'ventas_semana': Venta.objects.filter(
                cerrada=True,
                fecha__date__gte=hace_7_dias
            ).count(),
            'ingresos_semana': float(Venta.objects.filter(
                cerrada=True,
                fecha__date__gte=hace_7_dias
            ).aggregate(total=Sum('total'))['total'] or 0),
            
            # Inventario
            'productos_stock_bajo': Producto.objects.filter(cantidad__lte=5).count(),
            'productos_sin_stock': Producto.objects.filter(cantidad=0).count(),
            
            # Deudas
            'deudas_pendientes': Deuda.objects.filter(pagado=False).count(),
            'monto_deudas': float(Deuda.objects.filter(pagado=False).aggregate(
                total=Sum('monto_adeudado'))['total'] or 0),
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ========================================================================================
# 🔧 FUNCIONES AUXILIARES PARA FACTURAS
# ========================================================================================

@never_cache
@login_required
def procesar_factura_al_inventario(factura):
    """
    📦 FUNCIÓN CORREGIDA: Aplica automáticamente una factura al inventario
    
    NUEVA FUNCIONALIDAD:
    - Crea registros de InventarioFactura para tracking
    - Mejor manejo de errores
    - Integración completa con devoluciones
    """
    try:
        productos_actualizados = 0
        productos_nuevos = 0
        errores = []
        
        for detalle in factura.detalles.all():
            try:
                # Usar el nuevo método del detalle
                exito, mensaje = detalle.aplicar_a_inventario(usuario=factura.registrada_por)
                
                if exito:
                    if detalle.producto and detalle.producto.pk:
                        # Era producto existente
                        productos_actualizados += 1
                    else:
                        # Era producto nuevo
                        productos_nuevos += 1
                else:
                    errores.append(f"{detalle.nombre_producto}: {mensaje}")
                    
            except Exception as e:
                print(f"Error procesando detalle {detalle.id}: {e}")
                errores.append(f"{detalle.nombre_producto}: Error - {str(e)}")
                continue
        
        # Marcar factura como aplicada al inventario
        factura.inventario_actualizado = True
        factura.save()
        
        resultado = {
            'success': len(errores) == 0,
            'productos_actualizados': productos_actualizados,
            'productos_nuevos': productos_nuevos,
            'errores': errores
        }
        
        if errores:
            resultado['mensaje'] = f"Procesado con {len(errores)} errores: {', '.join(errores)}"
        else:
            resultado['mensaje'] = f"Inventario actualizado exitosamente: {productos_actualizados} actualizados, {productos_nuevos} nuevos"
        
        return resultado
        
    except Exception as e:
        print(f"Error crítico aplicando factura {factura.id}: {e}")
        return {
            'success': False,
            'productos_actualizados': 0,
            'productos_nuevos': 0,
            'errores': [str(e)],
            'mensaje': f"Error crítico: {str(e)}"
        }



@never_cache
@login_required
def sincronizar_sistema_completo(request):
    """
    🔄 FUNCIÓN CORREGIDA: Sincronización completa del sistema
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    if request.method == 'POST':
        try:
            resultados = {
                'facturas_procesadas': 0,
                'inventarios_creados': 0,
                'productos_actualizados': 0,
                'movimientos_creados': 0,
                'devoluciones_corregidas': 0,
                'errores': []
            }
            
            # 1. Procesar facturas pendientes
            facturas_pendientes = FacturaCompra.objects.filter(
                estado='recibida',
                inventario_actualizado=False
            )
            
            for factura in facturas_pendientes:
                try:
                    resultado = procesar_factura_al_inventario(factura)
                    if resultado['success']:
                        resultados['facturas_procesadas'] += 1
                        resultados['productos_actualizados'] += resultado['productos_actualizados'] + resultado['productos_nuevos']
                    else:
                        resultados['errores'].extend(resultado['errores'])
                except Exception as e:
                    resultados['errores'].append(f"Factura {factura.numero_factura}: {str(e)}")
            
            # 2. Crear registros de InventarioFactura faltantes
            detalles_sin_tracking = DetalleFacturaCompra.objects.filter(
                aplicado_inventario=True,
                producto__isnull=False
            ).exclude(
                id__in=InventarioFactura.objects.values_list('factura__detalles__id', flat=True)
            )
            
            for detalle in detalles_sin_tracking:
                try:
                    InventarioFactura.objects.get_or_create(
                        producto=detalle.producto,
                        factura=detalle.factura,
                        defaults={
                            'cantidad_recibida': detalle.cantidad,
                            'cantidad_actual': min(detalle.cantidad, detalle.producto.cantidad),
                            'precio_costo_unitario': detalle.precio_unitario
                        }
                    )
                    resultados['inventarios_creados'] += 1
                except Exception as e:
                    resultados['errores'].append(f"Tracking {detalle.id}: {str(e)}")
            
            # 3. Verificar y corregir devoluciones sin origen
            devoluciones_sin_origen = Devolucion.objects.filter(
                venta_origen__isnull=True,
                factura_origen__isnull=True
            )
            
            for devolucion in devoluciones_sin_origen:
                try:
                    if devolucion.tipo == 'cliente':
                        # Buscar venta reciente del producto
                        venta_probable = Venta.objects.filter(
                            detalles__producto=devolucion.producto,
                            cerrada=True,
                            fecha__date__gte=devolucion.fecha_solicitud.date() - timedelta(days=30)
                        ).order_by('-fecha').first()
                        
                        if venta_probable:
                            devolucion.venta_origen = venta_probable
                            devolucion.save()
                            resultados['devoluciones_corregidas'] += 1
                            
                    elif devolucion.tipo in ['inventario', 'proveedor']:
                        # Buscar factura reciente del producto
                        factura_probable = FacturaCompra.objects.filter(
                            detalles__producto=devolucion.producto,
                            estado__in=['recibida', 'pagada']
                        ).order_by('-fecha_factura').first()
                        
                        if factura_probable:
                            devolucion.factura_origen = factura_probable
                            devolucion.save()
                            resultados['devoluciones_corregidas'] += 1
                            
                except Exception as e:
                    resultados['errores'].append(f"Devolución {devolucion.id}: {str(e)}")
            
            # Mensaje final
            if resultados['errores']:
                messages.warning(
                    request,
                    f"Sincronización completada con {len(resultados['errores'])} errores. "
                    f"Procesadas: {resultados['facturas_procesadas']} facturas, "
                    f"Creados: {resultados['inventarios_creados']} trackings, "
                    f"Corregidas: {resultados['devoluciones_corregidas']} devoluciones."
                )
            else:
                messages.success(
                    request,
                    f"Sincronización exitosa: "
                    f"{resultados['facturas_procesadas']} facturas procesadas, "
                    f"{resultados['productos_actualizados']} productos actualizados, "
                    f"{resultados['inventarios_creados']} trackings creados, "
                    f"{resultados['devoluciones_corregidas']} devoluciones corregidas."
                )
                
        except Exception as e:
            messages.error(request, f"Error en sincronización: {str(e)}")
    
    return redirect('facturas_dashboard')
    


# ========================================================================================
# 🎯 RESUMEN DE FUNCIONES CORREGIDAS
# ========================================================================================

"""
✅ SISTEMA DE FACTURAS COMPLETAMENTE CORREGIDO Y ESTRUCTURADO

🏪 PROVEEDORES:
- proveedores_listar: Lista todos los proveedores
- proveedor_crear: Crear nuevo proveedor  
- proveedor_editar: Editar proveedor
- proveedor_eliminar: Eliminar proveedor (SIN DUPLICACIÓN)
- proveedor_detalle: Ver detalles del proveedor

🧾 FACTURAS:
- facturas_dashboard: Dashboard principal
- facturas_listar: Lista con filtros
- factura_crear: Crear factura
- factura_detalle: Ver detalles completos
- factura_editar: Editar factura
- factura_agregar_detalle: Agregar productos
- factura_eliminar_detalle: Eliminar productos  
- enlazar_producto_factura: Enlazar con inventario
- factura_cambiar_estado: Cambiar estado (CON INTEGRACIÓN AL INVENTARIO)
- factura_aplicar_inventario: Aplicar manualmente
- factura_registrar_pago: Registrar pagos

📊 REPORTES:
- facturas_reportes: Vista de reportes
- reporte_ventas_facturas: Análisis de rentabilidad

🔗 APIs:
- producto_info_api_facturas: Info de productos
- dashboard_stats_api: Estadísticas en tiempo real

🔧 AUXILIARES:
- procesar_factura_al_inventario: FUNCIÓN CLAVE para inventario
- sincronizar_sistema: Sincronización completa

🎯 INTEGRACIÓN COMPLETA:
✅ Con inventario (ejemplo: 5 cervezas + 20 de factura = 25 total)
✅ Con contabilidad (MovimientoContable tipo 'costo')
✅ Con devoluciones (enlazado con sistema existente)
✅ Sin duplicaciones
✅ Manejo robusto de errores
✅ Mensajes informativos
"""

# ========================================================================================
# 🔧 FUNCIÓN AUXILIAR PARA VERIFICAR STOCK
# ========================================================================================

def verificar_stock_sistema():
    """
    🔍 Función para verificar la integridad del stock del sistema
    Útil para debugging
    """
    try:
        from django.db.models import Sum
        
        # Obtener todos los productos
        productos = Producto.objects.all()
        
        print("🔍 VERIFICACIÓN DE STOCK:")
        print(f"Total productos: {productos.count()}")
        
        stock_total = 0
        productos_con_stock = 0
        productos_sin_stock = 0
        
        for producto in productos:
            cantidad = producto.cantidad or 0
            stock_total += cantidad
            
            if cantidad > 0:
                productos_con_stock += 1
            else:
                productos_sin_stock += 1
            
            print(f"  - {producto.nombre}: {cantidad} unidades")
        
        print(f"\n📊 RESUMEN:")
        print(f"  Stock total: {stock_total}")
        print(f"  Productos con stock: {productos_con_stock}")
        print(f"  Productos sin stock: {productos_sin_stock}")
        
        # Verificar con aggregate
        stock_aggregate = Producto.objects.aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        print(f"  Stock con aggregate: {stock_aggregate}")
        
        if stock_total == stock_aggregate:
            print("✅ Cálculos coinciden")
        else:
            print("❌ ERROR: Cálculos no coinciden")
        
        return {
            'stock_total': stock_total,
            'productos_con_stock': productos_con_stock,
            'productos_sin_stock': productos_sin_stock,
            'calculo_correcto': stock_total == stock_aggregate
        }
        
    except Exception as e:
        print(f"❌ Error verificando stock: {e}")
        return None


# ========================================================================================
# 🧪 VISTA PARA DEBUGGING (TEMPORAL)
# ========================================================================================

@never_cache
@login_required
def debug_stock(request):
    """
    🧪 Vista temporal para debugging del stock
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden("Solo superuser")
    
    resultado = verificar_stock_sistema()
    
    return JsonResponse({
        'success': True,
        'debug_info': resultado,
        'productos': list(Producto.objects.values('id', 'nombre', 'cantidad'))
    })

    # ========================================================================================
# 🎁 GESTIÓN DE PRODUCTOS COMBINADOS/PROMOS - AGREGAR AL FINAL DE views.py
# ========================================================================================
# Agregar estas funciones al final de tu archivo views.py existente

@never_cache
@login_required
def combos_listar(request):
    """
    📋 Lista todos los productos combinados disponibles
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    try:
        from django.db.models import Count
        
        # 🎁 OBTENER COMBOS CON INFORMACIÓN COMPLETA
        combos = ProductoCombinado.objects.prefetch_related(
            'componentes__producto',
            'componentes__producto__categoria'
        ).order_by('-activo', '-fecha_creacion')
        
        # 📊 ESTADÍSTICAS
        total_combos = combos.count()
        combos_activos = combos.filter(activo=True).count()
        combos_inactivos = combos.filter(activo=False).count()
        
        # 🎁 PROCESAR COMBOS CON INFORMACIÓN DETALLADA
        combos_procesados = []
        for combo in combos:
            combo_info = {
                'objeto': combo,
                'componentes': combo.componentes_info,
                'tiene_stock': combo.tiene_stock_disponible,
                'esta_vigente': combo.esta_vigente,
                'puede_venderse': combo.tiene_stock_disponible and combo.esta_vigente and combo.activo,
                'stock_limitante': combo.stock_limitante,
                'descuento_real': combo.porcentaje_descuento_real,
                'descuento_absoluto': combo.descuento_absoluto,
                'precio_individual_total': combo.precio_individual_total,
                'ahorro': combo.precio_individual_total - combo.precio_combo,
            }
            combos_procesados.append(combo_info)
        
        context = {
            'combos': combos_procesados,
            'total_combos': total_combos,
            'combos_activos': combos_activos,
            'combos_inactivos': combos_inactivos,
        }
        
        return render(request, 'core/combos/listar.html', context)
        
    except Exception as e:
        print(f"Error en combos_listar: {e}")
        messages.error(request, f"Error al cargar combos: {str(e)}")
        return redirect('admin_dashboard')


# REEMPLAZAR la función combo_crear en tu views.py con esta versión corregida:
@never_cache
@login_required
def combo_crear(request):
    """
    ➕ Crear nuevo producto combinado - CORREGIDA para control manual de precios
    
    Features:
    - El administrador establece el precio manualmente
    - Asistente de precios que sugiere rangos
    - Sin cálculo automático de precios
    - Manejo completo de imágenes
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    if request.method == 'POST':
        try:
            import json
            from decimal import Decimal, InvalidOperation
            
            # DATOS DEL COMBO
            nombre = request.POST.get('nombre', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            tipo_combo = request.POST.get('tipo_combo', 'combo')
            
            # 🔥 PRECIO ESTABLECIDO POR EL ADMINISTRADOR (NO AUTOMÁTICO)
            precio_combo_manual = request.POST.get('precio_combo', '0')
            
            # IMAGEN DEL COMBO
            imagen = request.FILES.get('imagen', None)
            
            # PRODUCTOS SELECCIONADOS (JSON)
            productos_json = request.POST.get('productos_seleccionados', '{}')
            
            print(f"DEBUG - Nombre: {nombre}")
            print(f"DEBUG - Precio manual establecido: {precio_combo_manual}")
            print(f"DEBUG - Productos JSON: {productos_json}")
            
            try:
                productos_seleccionados = json.loads(productos_json) if productos_json else {}
            except json.JSONDecodeError:
                productos_seleccionados = {}
            
            # VALIDACIONES
            if not nombre:
                messages.error(request, '❌ El nombre del combo es obligatorio.')
                return redirect('combo_crear')
            
            if not productos_seleccionados:
                messages.error(request, '❌ Debes seleccionar al menos un producto para el combo.')
                return redirect('combo_crear')
            
            # 🔥 VALIDACIÓN DEL PRECIO MANUAL
            try:
                precio_combo = Decimal(str(precio_combo_manual))
                if precio_combo <= 0:
                    messages.error(request, '❌ El precio del combo debe ser mayor a cero.')
                    return redirect('combo_crear')
            except (ValueError, InvalidOperation):
                messages.error(request, '❌ Precio inválido. Ingresa un número válido.')
                return redirect('combo_crear')
            
            # 🔥 CREAR COMBO CON PRECIO MANUAL (SIN CÁLCULO AUTOMÁTICO)
            combo = ProductoCombinado.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                tipo_combo=tipo_combo,
                precio_combo=precio_combo,  # 🎯 PRECIO ESTABLECIDO POR ADMIN
                imagen=imagen,
                creado_por=request.user,
                activo=True
            )
            
            # AGREGAR PRODUCTOS AL COMBO
            productos_agregados = 0
            precio_individual_total = Decimal('0.00')
            
            for producto_data in productos_seleccionados.values():
                try:
                    producto = Producto.objects.get(id=producto_data['id'])
                    cantidad = int(producto_data['cantidad'])
                    
                    ComponenteCombo.objects.create(
                        combo=combo,
                        producto=producto,
                        cantidad=cantidad,
                        es_opcional=False
                    )
                    
                    # Calcular precio individual para estadísticas
                    precio_individual_total += producto.precio * cantidad
                    productos_agregados += 1
                    
                    print(f"Producto agregado: {producto.nombre} x{cantidad}")
                    
                except Exception as e:
                    print(f"Error agregando producto {producto_data.get('id')}: {e}")
            
            # 📊 CALCULAR ESTADÍSTICAS DEL COMBO (PARA INFORMACIÓN)
            if precio_individual_total > 0:
                descuento_absoluto = precio_individual_total - precio_combo
                porcentaje_descuento = (descuento_absoluto / precio_individual_total) * 100
                
                if descuento_absoluto > 0:
                    tipo_mensaje = "descuento"
                    mensaje_descuento = f"Descuento: ${int(descuento_absoluto):,} ({porcentaje_descuento:.1f}%)"
                else:
                    tipo_mensaje = "precio premium"
                    mensaje_descuento = f"Precio premium: ${int(abs(descuento_absoluto)):,} sobre precio individual"
            else:
                mensaje_descuento = ""
            
            # MENSAJE COMPLETO
            imagen_info = " con imagen" if imagen else ""
            precio_info = f" - ${int(precio_combo):,} COP"
            
            messages.success(
                request,
                f'✅ Combo "{combo.nombre}" creado exitosamente{imagen_info}. '
                f'Precio establecido{precio_info}. '
                f'Productos: {productos_agregados}. '
                f'{mensaje_descuento}'
            )
            
            return redirect('productos_listar')
            
        except Exception as e:
            print(f"Error creando combo: {e}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'❌ Error al crear el combo: {str(e)}')
    
    # PRODUCTOS Y CATEGORÍAS DISPONIBLES
    productos_disponibles = Producto.objects.filter(cantidad__gt=0).order_by('nombre')
    categorias_disponibles = Categoria.objects.filter(
        productos__cantidad__gt=0
    ).distinct().order_by('nombre')
    
    context = {
        'productos_disponibles': productos_disponibles,
        'categorias_disponibles': categorias_disponibles,
        'titulo': 'Crear Combo'
    }
    
    return render(request, 'core/combos/crear.html', context)


@never_cache
@login_required
def combo_asistente_precios_api(request):
    """
    🤖 API para asistente de precios de combos
    
    Features:
    - Calcula precio individual total de los productos
    - Sugiere diferentes estrategias de pricing
    - Análisis de descuentos recomendados
    - Comparación con precios de mercado
    """
    if request.method == 'GET':
        try:
            import json
            from decimal import Decimal
            
            # Obtener productos seleccionados
            productos_json = request.GET.get('productos', '{}')
            
            try:
                productos_seleccionados = json.loads(productos_json)
            except json.JSONDecodeError:
                return JsonResponse({
                    'success': False,
                    'error': 'JSON de productos inválido'
                })
            
            if not productos_seleccionados:
                return JsonResponse({
                    'success': False,
                    'error': 'No hay productos seleccionados'
                })
            
            # 📊 CALCULAR PRECIO INDIVIDUAL TOTAL
            precio_individual_total = Decimal('0.00')
            productos_info = []
            
            for producto_data in productos_seleccionados.values():
                try:
                    producto = Producto.objects.get(id=producto_data['id'])
                    cantidad = int(producto_data['cantidad'])
                    subtotal = producto.precio * cantidad
                    
                    precio_individual_total += subtotal
                    
                    productos_info.append({
                        'nombre': producto.nombre,
                        'precio_unitario': float(producto.precio),
                        'cantidad': cantidad,
                        'subtotal': float(subtotal)
                    })
                    
                except Producto.DoesNotExist:
                    continue
                except (ValueError, TypeError):
                    continue
            
            if precio_individual_total == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'No se pudo calcular el precio total'
                })
            
            # 🎯 ESTRATEGIAS DE PRECIOS RECOMENDADAS
            precio_individual_float = float(precio_individual_total)
            
            recomendaciones = [
                {
                    'nombre': 'Precio Individual',
                    'precio': precio_individual_float,
                    'precio_formateado': f"${int(precio_individual_float):,}".replace(',', '.'),
                    'descuento': 0,
                    'descripcion': 'Precio sin descuento (no recomendado para combos)',
                    'recomendado': False,
                    'color': 'secondary'
                },
                {
                    'nombre': 'Descuento Suave (5%)',
                    'precio': precio_individual_float * 0.95,
                    'precio_formateado': f"${int(precio_individual_float * 0.95):,}".replace(',', '.'),
                    'descuento': 5,
                    'descripcion': 'Descuento mínimo para incentivar compra',
                    'recomendado': False,
                    'color': 'info'
                },
                {
                    'nombre': 'Descuento Moderado (10%)',
                    'precio': precio_individual_float * 0.90,
                    'precio_formateado': f"${int(precio_individual_float * 0.90):,}".replace(',', '.'),
                    'descuento': 10,
                    'descripcion': 'Balance entre atractivo y rentabilidad',
                    'recomendado': True,
                    'color': 'success'
                },
                {
                    'nombre': 'Descuento Atractivo (15%)',
                    'precio': precio_individual_float * 0.85,
                    'precio_formateado': f"${int(precio_individual_float * 0.85):,}".replace(',', '.'),
                    'descuento': 15,
                    'descripcion': 'Muy atractivo para el cliente',
                    'recomendado': True,
                    'color': 'warning'
                },
                {
                    'nombre': 'Descuento Agresivo (20%)',
                    'precio': precio_individual_float * 0.80,
                    'precio_formateado': f"${int(precio_individual_float * 0.80):,}".replace(',', '.'),
                    'descuento': 20,
                    'descripción': 'Para promociones especiales o liquidación',
                    'recomendado': False,
                    'color': 'danger'
                },
                {
                    'nombre': 'Precio Premium (+5%)',
                    'precio': precio_individual_float * 1.05,
                    'precio_formateado': f"${int(precio_individual_float * 1.05):,}".replace(',', '.'),
                    'descuento': -5,
                    'descripcion': 'Para combos exclusivos o de alta demanda',
                    'recomendado': False,
                    'color': 'dark'
                }
            ]
            
            # 📊 ANÁLISIS ADICIONAL
            analisis = {
                'precio_individual_total': precio_individual_float,
                'precio_individual_formateado': f"${int(precio_individual_float):,}".replace(',', '.'),
                'cantidad_productos': len(productos_info),
                'precio_promedio_producto': precio_individual_float / len(productos_info) if productos_info else 0,
                'rango_recomendado_min': int(precio_individual_float * 0.85),
                'rango_recomendado_max': int(precio_individual_float * 0.95),
                'productos_detalle': productos_info
            }
            
            return JsonResponse({
                'success': True,
                'recomendaciones': recomendaciones,
                'analisis': analisis,
                'mensaje': f'Se analizaron {len(productos_info)} productos. Rango recomendado: ${analisis["rango_recomendado_min"]:,} - ${analisis["rango_recomendado_max"]:,} COP'
            })
            
        except Exception as e:
            print(f"Error en asistente de precios: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Error interno: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    })
@never_cache
@login_required
def combo_detalle(request, pk):
    """
    👁️ Ver detalles completos de un combo
    """
    combo = get_object_or_404(
        ProductoCombinado.objects.prefetch_related(
            'componentes__producto',
            'componentes__producto__categoria'
        ),
        pk=pk
    )
    
    # 📋 AGREGAR COMPONENTE SI SE ENVÍA FORMULARIO
    if request.method == 'POST' and request.user.perfil.rol == 'admin':
        accion = request.POST.get('accion')
        
        if accion == 'agregar_componente':
            try:
                producto_id = request.POST.get('producto_id')
                cantidad = int(request.POST.get('cantidad', 1))
                es_opcional = request.POST.get('es_opcional') == 'on'
                observaciones = request.POST.get('observaciones', '').strip()
                
                producto = get_object_or_404(Producto, id=producto_id)
                
                # Verificar que no exista ya
                if ComponenteCombo.objects.filter(combo=combo, producto=producto).exists():
                    messages.error(request, f'❌ {producto.nombre} ya está en este combo.')
                else:
                    ComponenteCombo.objects.create(
                        combo=combo,
                        producto=producto,
                        cantidad=cantidad,
                        es_opcional=es_opcional,
                        observaciones=observaciones
                    )
                    messages.success(request, f'✅ Producto {producto.nombre} agregado al combo.')
                
            except Exception as e:
                messages.error(request, f'❌ Error al agregar componente: {str(e)}')
    
    # 📦 PRODUCTOS DISPONIBLES PARA AGREGAR
    productos_ya_en_combo = combo.componentes.values_list('producto_id', flat=True)
    productos_disponibles = Producto.objects.exclude(
        id__in=productos_ya_en_combo
    ).filter(cantidad__gt=0).order_by('nombre')
    
    context = {
        'combo': combo,
        'componentes': combo.componentes_info,
        'productos_disponibles': productos_disponibles,
        'puede_editar': request.user.perfil.rol == 'admin',
        'tiene_stock': combo.tiene_stock_disponible,
        'esta_vigente': combo.esta_vigente,
        'puede_venderse': combo.tiene_stock_disponible and combo.esta_vigente and combo.activo,
        'stock_limitante': combo.stock_limitante,
        'descuento_real': combo.porcentaje_descuento_real,
        'precio_individual_total': combo.precio_individual_total,
    }
    
    return render(request, 'core/combos/combo_detalle.html', context)


@never_cache
@login_required
def combo_toggle_estado(request, pk):
    """
    🔄 Activar/desactivar combo
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    combo = get_object_or_404(ProductoCombinado, pk=pk)
    
    if request.method == 'POST':
        combo.activo = not combo.activo
        combo.save()
        
        estado = "activado" if combo.activo else "desactivado"
        messages.success(request, f'✅ Combo "{combo.nombre}" {estado} correctamente.')
    
    return redirect('combos_listar')


@never_cache
@login_required
def combo_eliminar(request, pk):
    """
    🗑️ Eliminar combo - VERSIÓN CORREGIDA con manejo de imagen
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    combo = get_object_or_404(ProductoCombinado, pk=pk)
    
    if request.method == 'POST':
        try:
            nombre_combo = combo.nombre
            tiene_imagen = bool(combo.imagen)
            
            # Eliminar imagen física si existe
            if combo.imagen:
                try:
                    import os
                    imagen_path = combo.imagen.path
                    if os.path.exists(imagen_path):
                        os.remove(imagen_path)
                        print(f"Imagen eliminada: {imagen_path}")
                except Exception as e:
                    print(f"Error eliminando imagen: {e}")
            
            # Eliminar el combo (esto también elimina automáticamente los ComponenteCombo)
            combo.delete()
            
            imagen_info = " (incluida su imagen)" if tiene_imagen else ""
            messages.success(
                request, 
                f'✅ Combo "{nombre_combo}" eliminado correctamente{imagen_info}.'
            )
            
            return redirect('productos_listar')  # O combos_listar si prefieres
            
        except Exception as e:
            print(f"Error eliminando combo: {e}")
            messages.error(request, f'❌ Error al eliminar el combo: {str(e)}')
            return redirect('combo_detalle', pk=pk)
    
    return render(request, 'core/combos/combo_confirmar_eliminar.html', {
        'combo': combo
    })    


@never_cache
@login_required
def venta_agregar_combo(request, mesa_id):
    """
    🛒 Agregar combo a una venta (desde la vista de venta de mesa)
    """
    mesa = get_object_or_404(Mesa, id=mesa_id)
    venta, _ = Venta.objects.get_or_create(mesa=mesa, cerrada=False, defaults={'mesero': request.user})
    
    if request.method == 'POST':
        try:
            combo_id = request.POST.get('combo_id')
            cantidad = int(request.POST.get('cantidad', 1))
            
            combo = get_object_or_404(ProductoCombinado, id=combo_id)
            
            # ✅ VALIDACIONES
            if not combo.activo:
                messages.error(request, f'❌ El combo "{combo.nombre}" no está activo.')
                return redirect('venta_mesa', mesa_id=mesa.id)
            
            if not combo.esta_vigente:
                messages.error(request, f'❌ El combo "{combo.nombre}" no está vigente.')
                return redirect('venta_mesa', mesa_id=mesa.id)
            
            if not combo.tiene_stock_disponible:
                messages.error(request, f'❌ No hay stock suficiente para el combo "{combo.nombre}".')
                return redirect('venta_mesa', mesa_id=mesa.id)
            
            # 🔍 VERIFICAR STOCK PARA LA CANTIDAD SOLICITADA
            stock_info = combo.stock_limitante
            if cantidad > stock_info['cantidad_maxima_combos']:
                messages.error(
                    request,
                    f'❌ Solo se pueden vender {stock_info["cantidad_maxima_combos"]} combos. '
                    f'Limitado por: {stock_info["producto"].nombre}'
                )
                return redirect('venta_mesa', mesa_id=mesa.id)
            
            # 📦 REDUCIR STOCK DE CADA COMPONENTE
            for componente in combo.componentes.all():
                producto = componente.producto
                cantidad_a_reducir = componente.cantidad * cantidad
                
                if producto.cantidad < cantidad_a_reducir:
                    messages.error(
                        request,
                        f'❌ Stock insuficiente de {producto.nombre}. '
                        f'Disponible: {producto.cantidad}, Necesario: {cantidad_a_reducir}'
                    )
                    return redirect('venta_mesa', mesa_id=mesa.id)
                
                producto.cantidad -= cantidad_a_reducir
                producto.save()
            
            # 🛒 AGREGAR COMBO COMO ITEM ESPECIAL EN LA VENTA
            # Crear un DetalleVenta especial para el combo
            detalle_combo = DetalleVenta.objects.create(
                venta=venta,
                producto=None,  # Los combos no tienen producto específico
                cantidad=cantidad,
                precio_unitario=combo.precio_combo
            )
            
            # 📝 REGISTRAR VENTA DE COMBO (para estadísticas)
            VentaCombo.objects.create(
                venta=venta,
                combo=combo,
                cantidad_vendida=cantidad,
                precio_unitario=combo.precio_combo
            )
            
            # 💰 ACTUALIZAR TOTAL DE LA VENTA
            venta.total = venta.detalles.aggregate(
                total=Sum(F('cantidad') * F('precio_unitario'))
            )['total'] or 0
            venta.save()
            
            messages.success(
                request,
                f'✅ Combo "{combo.nombre}" agregado a la venta. '
                f'Cantidad: {cantidad}, Subtotal: ${combo.precio_combo * cantidad:,.0f}'
            )
            
        except Exception as e:
            print(f"Error agregando combo a venta: {e}")
            messages.error(request, f'❌ Error al agregar combo: {str(e)}')
    
    return redirect('venta_mesa', mesa_id=mesa.id)


@never_cache
@login_required
def combos_estadisticas(request):
    """
    📊 Estadísticas de combos y promociones
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    try:
        from datetime import timedelta
        from django.db.models import Sum, Count, Avg
        
        # 📅 PARÁMETROS DE FECHA
        hoy = timezone.now().date()
        hace_30_dias = hoy - timedelta(days=30)
        hace_7_dias = hoy - timedelta(days=7)
        
        # 📊 ESTADÍSTICAS GENERALES
        stats_generales = {
            'total_combos': ProductoCombinado.objects.count(),
            'combos_activos': ProductoCombinado.objects.filter(activo=True).count(),
            'combos_con_stock': len([c for c in ProductoCombinado.objects.filter(activo=True) if c.tiene_stock_disponible]),
            'combos_vigentes': len([c for c in ProductoCombinado.objects.filter(activo=True) if c.esta_vigente]),
        }
        
        # 🛒 VENTAS DE COMBOS
        ventas_mes = VentaCombo.objects.filter(
            venta__fecha__date__gte=hace_30_dias,
            venta__cerrada=True
        ).aggregate(
            total_vendidos=Sum('cantidad_vendida'),
            ingresos_totales=Sum(F('cantidad_vendida') * F('precio_unitario'))
        )
        
        ventas_semana = VentaCombo.objects.filter(
            venta__fecha__date__gte=hace_7_dias,
            venta__cerrada=True
        ).aggregate(
            total_vendidos=Sum('cantidad_vendida'),
            ingresos_totales=Sum(F('cantidad_vendida') * F('precio_unitario'))
        )
        
        # 🏆 COMBOS MÁS VENDIDOS
        combos_mas_vendidos = VentaCombo.objects.filter(
            venta__cerrada=True
        ).values(
            'combo__nombre',
            'combo__id'
        ).annotate(
            total_vendido=Sum('cantidad_vendida'),
            ingresos_generados=Sum(F('cantidad_vendida') * F('precio_unitario')),
            numero_ventas=Count('id')
        ).order_by('-total_vendido')[:10]
        
        # 💰 ANÁLISIS DE DESCUENTOS
        combos_con_descuentos = []
        for combo in ProductoCombinado.objects.filter(activo=True):
            if combo.porcentaje_descuento_real > 0:
                combos_con_descuentos.append({
                    'combo': combo,
                    'descuento_porcentaje': combo.porcentaje_descuento_real,
                    'descuento_absoluto': combo.descuento_absoluto,
                    'precio_individual': combo.precio_individual_total,
                    'precio_combo': combo.precio_combo,
                })
        
        # Ordenar por descuento absoluto
        combos_con_descuentos.sort(key=lambda x: x['descuento_absoluto'], reverse=True)
        
        context = {
            'stats_generales': stats_generales,
            'ventas_mes': ventas_mes,
            'ventas_semana': ventas_semana,
            'combos_mas_vendidos': combos_mas_vendidos,
            'combos_con_descuentos': combos_con_descuentos[:10],
            'fecha_desde': hace_30_dias,
            'fecha_hasta': hoy,
        }
        
        return render(request, 'core/combos/combos_estadisticas.html', context)
        
    except Exception as e:
        print(f"Error en combos_estadisticas: {e}")
        messages.error(request, f"Error al generar estadísticas: {str(e)}")
        return redirect('combos_listar')


@never_cache
@login_required
def combo_info_api(request, pk):
    """
    📡 API para obtener información de un combo
    """
    try:
        combo = get_object_or_404(ProductoCombinado, pk=pk)
        
        data = {
            'id': combo.id,
            'nombre': combo.nombre,
            'descripcion': combo.descripcion,
            'precio_combo': float(combo.precio_combo),
            'precio_formateado': combo.get_precio_formateado(),
            'activo': combo.activo,
            'tiene_stock': combo.tiene_stock_disponible,
            'esta_vigente': combo.esta_vigente,
            'puede_venderse': combo.tiene_stock_disponible and combo.esta_vigente and combo.activo,
            'tipo_combo': combo.tipo_combo,
            'descuento_real': float(combo.porcentaje_descuento_real),
            'descuento_absoluto': float(combo.descuento_absoluto),
            'precio_individual_total': float(combo.precio_individual_total),
            'stock_limitante': combo.stock_limitante,
            'tiene_imagen': combo.tiene_imagen(),
            'imagen_url': combo.get_imagen_url(),
            'componentes': [
                {
                    'producto_nombre': comp['producto'].nombre,
                    'cantidad': comp['cantidad'],
                    'tiene_stock': comp['tiene_stock'],
                    'subtotal': float(comp['subtotal'])
                }
                for comp in combo.componentes_info
            ]
        }
        
        return JsonResponse({
            'success': True,
            'combo': data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@never_cache
@login_required
def eliminar_combo_venta(request, combo_venta_id):
    """
    🗑️ Eliminar combo de una venta (devolver stock de componentes)
    
    Features:
    - Devuelve el stock de todos los componentes del combo
    - Recalcula el total de la venta automáticamente
    - Elimina el registro de VentaCombo
    - Manejo seguro de errores
    """
    try:
        # 🔍 OBTENER EL COMBO DE LA VENTA
        combo_venta = get_object_or_404(
            VentaCombo.objects.select_related(
                'venta', 'venta__mesa', 'combo'
            ).prefetch_related(
                'combo__componentes__producto'
            ), 
            id=combo_venta_id
        )
        
        venta = combo_venta.venta
        combo = combo_venta.combo
        cantidad_vendida = combo_venta.cantidad_vendida
        
        # ✅ VERIFICAR QUE LA VENTA AÚN ESTÉ ABIERTA
        if venta.cerrada:
            messages.error(request, '❌ No se pueden eliminar items de una venta ya finalizada.')
            return redirect('venta_mesa', mesa_id=venta.mesa.id)
        
        # 📦 DEVOLVER STOCK A CADA COMPONENTE DEL COMBO
        componentes_restaurados = []
        for componente in combo.componentes.all():
            producto = componente.producto
            cantidad_a_devolver = componente.cantidad * cantidad_vendida
            
            # Devolver stock
            producto.cantidad += cantidad_a_devolver
            producto.save()
            
            componentes_restaurados.append({
                'nombre': producto.nombre,
                'cantidad_devuelta': cantidad_a_devolver,
                'stock_final': producto.cantidad
            })
        
        # 💰 GUARDAR INFORMACIÓN PARA EL MENSAJE
        subtotal_eliminado = combo_venta.cantidad_vendida * combo_venta.precio_unitario
        nombre_combo = combo.nombre
        
        # 🗑️ ELIMINAR EL REGISTRO DE VENTA DE COMBO
        combo_venta.delete()
        
        # 💰 RECALCULAR TOTAL DE LA VENTA
        # Total de productos individuales
        total_productos = venta.detalles.aggregate(
            total=Sum(F('cantidad') * F('precio_unitario'))
        )['total'] or Decimal('0.00')
        
        # Total de combos restantes
        total_combos = VentaCombo.objects.filter(venta=venta).aggregate(
            total=Sum(F('cantidad_vendida') * F('precio_unitario'))
        )['total'] or Decimal('0.00')
        
        # Actualizar total de la venta
        venta.total = total_productos + total_combos
        venta.save()
        
        # ✅ MENSAJE DE ÉXITO CON DETALLES
        mensaje_componentes = ", ".join([
            f"{comp['nombre']} (+{comp['cantidad_devuelta']})"
            for comp in componentes_restaurados
        ])
        
        messages.success(
            request,
            f'✅ Combo "{nombre_combo}" eliminado de la venta. '
            f'Stock restaurado: {mensaje_componentes}. '
            f'Subtotal eliminado: ${subtotal_eliminado:,.0f} COP. '
            f'Nuevo total: ${venta.total:,.0f} COP.'
        )
        
        return redirect('venta_mesa', mesa_id=venta.mesa.id)
        
    except VentaCombo.DoesNotExist:
        messages.error(request, '❌ El combo no existe o ya fue eliminado.')
        return redirect('mesas_listar')
        
    except Exception as e:
        print(f"❌ Error eliminando combo de venta: {e}")
        import traceback
        traceback.print_exc()
        
        messages.error(request, f'❌ Error al eliminar el combo: {str(e)}')
        
        # Intentar redirigir a la venta si existe
        try:
            if 'combo_venta' in locals() and combo_venta.venta:
                return redirect('venta_mesa', mesa_id=combo_venta.venta.mesa.id)
        except:
            pass
            
        return redirect('mesas_listar')

@never_cache
@login_required
def inventario_por_facturas(request):
    """
    📊 NUEVA FUNCIÓN: Ver inventario agrupado por facturas de origen
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    try:
        from django.db.models import Sum, Count
        
        # Obtener inventarios por factura con información completa
        inventarios = InventarioFactura.objects.select_related(
            'producto', 'factura', 'factura__proveedor'
        ).filter(cantidad_actual__gt=0).order_by('-fecha_ingreso')
        
        # Agrupar por factura
        inventarios_agrupados = {}
        for inventario in inventarios:
            factura_id = inventario.factura.id
            if factura_id not in inventarios_agrupados:
                inventarios_agrupados[factura_id] = {
                    'factura': inventario.factura,
                    'productos': [],
                    'valor_total': 0,
                    'productos_count': 0
                }
            
            inventarios_agrupados[factura_id]['productos'].append(inventario)
            inventarios_agrupados[factura_id]['valor_total'] += inventario.valor_inventario_actual
            inventarios_agrupados[factura_id]['productos_count'] += 1
        
        context = {
            'inventarios_agrupados': inventarios_agrupados.values(),
            'total_facturas': len(inventarios_agrupados),
            'valor_total_inventario': sum(grupo['valor_total'] for grupo in inventarios_agrupados.values())
        }
        
        return render(request, 'core/facturas/inventario_por_facturas.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al cargar inventario por facturas: {str(e)}")
        return redirect('facturas_dashboard')
        
@never_cache
@login_required
def devolver_a_proveedor(request, detalle_factura_id):
    """
    🔄 NUEVA FUNCIÓN: Devolver producto directamente al proveedor
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    detalle = get_object_or_404(DetalleFacturaCompra, id=detalle_factura_id)
    
    if not detalle.puede_devolver_proveedor:
        messages.error(request, "Este producto no se puede devolver al proveedor.")
        return redirect('factura_detalle', pk=detalle.factura.pk)
    
    if request.method == 'POST':
        try:
            cantidad = int(request.POST.get('cantidad', 0))
            razon = request.POST.get('razon', 'otro')
            observaciones = request.POST.get('observaciones', '')
            
            # Validar cantidad
            max_cantidad = detalle.cantidad_disponible_devolucion
            if cantidad <= 0 or cantidad > max_cantidad:
                messages.error(
                    request, 
                    f"Cantidad inválida. Máximo disponible para devolución: {max_cantidad}"
                )
                return redirect('factura_detalle', pk=detalle.factura.pk)
            
            # Crear solicitud de devolución
            devolucion = Devolucion.objects.create(
                producto=detalle.producto,
                cantidad=cantidad,
                tipo='proveedor',
                razon=razon,
                observaciones=observaciones,
                solicitada_por=request.user,
                factura_origen=detalle.factura,
                estado='autorizada',  # Auto-autorizada por admin
                autorizada_por=request.user,
                fecha_autorizacion=timezone.now()
            )
            
            # Procesar inmediatamente
            devolucion.estado = 'procesada'
            devolucion.save()
            
            # Actualizar detalle de factura
            detalle.cantidad_devuelta += cantidad
            detalle.save()
            
            messages.success(
                request,
                f"Devolución procesada: {cantidad} x {detalle.nombre_producto} devuelto a {detalle.factura.proveedor.nombre}. "
                f"Nota de crédito esperada: ${devolucion.nota_credito_proveedor:,.0f}"
            )
            
        except Exception as e:
            messages.error(request, f"Error procesando devolución: {str(e)}")
    
    return redirect('factura_detalle', pk=detalle.factura.pk)


@never_cache
@login_required
def reporte_devoluciones_por_proveedor(request):
    """
    📊 NUEVA FUNCIÓN: Reporte de devoluciones agrupadas por proveedor
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    try:
        from datetime import timedelta
        
        # Parámetros de fecha
        hoy = timezone.now().date()
        hace_90_dias = hoy - timedelta(days=90)
        
        # Devoluciones a proveedores
        devoluciones_proveedor = Devolucion.objects.filter(
            tipo='proveedor',
            estado='procesada',
            fecha_procesamiento__date__gte=hace_90_dias
        ).select_related('factura_origen__proveedor', 'producto')
        
        # Agrupar por proveedor
        proveedores_stats = {}
        for devolucion in devoluciones_proveedor:
            if devolucion.factura_origen and devolucion.factura_origen.proveedor:
                proveedor = devolucion.factura_origen.proveedor
                if proveedor.id not in proveedores_stats:
                    proveedores_stats[proveedor.id] = {
                        'proveedor': proveedor,
                        'devoluciones': [],
                        'total_devuelto': 0,
                        'nota_credito_total': 0,
                        'productos_count': 0
                    }
                
                proveedores_stats[proveedor.id]['devoluciones'].append(devolucion)
                proveedores_stats[proveedor.id]['total_devuelto'] += devolucion.cantidad
                proveedores_stats[proveedor.id]['nota_credito_total'] += devolucion.nota_credito_proveedor
                proveedores_stats[proveedor.id]['productos_count'] += 1
        
        # Ordenar por nota de crédito total
        proveedores_ordenados = sorted(
            proveedores_stats.values(),
            key=lambda x: x['nota_credito_total'],
            reverse=True
        )
        
        context = {
            'proveedores_stats': proveedores_ordenados,
            'fecha_desde': hace_90_dias,
            'fecha_hasta': hoy,
            'total_proveedores': len(proveedores_stats),
            'total_nota_credito': sum(p['nota_credito_total'] for p in proveedores_stats.values())
        }
        
        return render(request, 'core/facturas/reporte_devoluciones_proveedor.html', context)
        
    except Exception as e:
        messages.error(request, f"Error generando reporte: {str(e)}")
        return redirect('facturas_dashboard')

@never_cache
@login_required
def reporte_devoluciones_por_proveedor(request):
    """
    📊 NUEVA FUNCIÓN: Reporte de devoluciones agrupadas por proveedor
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    try:
        from datetime import timedelta
        
        # Parámetros de fecha
        hoy = timezone.now().date()
        hace_90_dias = hoy - timedelta(days=90)
        
        # Devoluciones a proveedores
        devoluciones_proveedor = Devolucion.objects.filter(
            tipo='proveedor',
            estado='procesada',
            fecha_procesamiento__date__gte=hace_90_dias
        ).select_related('factura_origen__proveedor', 'producto')
        
        # Agrupar por proveedor
        proveedores_stats = {}
        for devolucion in devoluciones_proveedor:
            if devolucion.factura_origen and devolucion.factura_origen.proveedor:
                proveedor = devolucion.factura_origen.proveedor
                if proveedor.id not in proveedores_stats:
                    proveedores_stats[proveedor.id] = {
                        'proveedor': proveedor,
                        'devoluciones': [],
                        'total_devuelto': 0,
                        'nota_credito_total': 0,
                        'productos_count': 0
                    }
                
                proveedores_stats[proveedor.id]['devoluciones'].append(devolucion)
                proveedores_stats[proveedor.id]['total_devuelto'] += devolucion.cantidad
                proveedores_stats[proveedor.id]['nota_credito_total'] += devolucion.nota_credito_proveedor
                proveedores_stats[proveedor.id]['productos_count'] += 1
        
        # Ordenar por nota de crédito total
        proveedores_ordenados = sorted(
            proveedores_stats.values(),
            key=lambda x: x['nota_credito_total'],
            reverse=True
        )
        
        context = {
            'proveedores_stats': proveedores_ordenados,
            'fecha_desde': hace_90_dias,
            'fecha_hasta': hoy,
            'total_proveedores': len(proveedores_stats),
            'total_nota_credito': sum(p['nota_credito_total'] for p in proveedores_stats.values())
        }
        
        return render(request, 'core/facturas/reporte_devoluciones_proveedor.html', context)
        
    except Exception as e:
        messages.error(request, f"Error generando reporte: {str(e)}")
        return redirect('facturas_dashboard')

@never_cache
@login_required
def reporte_devoluciones_por_proveedor(request):
    """
    📊 NUEVA FUNCIÓN: Reporte de devoluciones agrupadas por proveedor
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    try:
        from datetime import timedelta
        
        # Parámetros de fecha
        hoy = timezone.now().date()
        hace_90_dias = hoy - timedelta(days=90)
        
        # Devoluciones a proveedores
        devoluciones_proveedor = Devolucion.objects.filter(
            tipo='proveedor',
            estado='procesada',
            fecha_procesamiento__date__gte=hace_90_dias
        ).select_related('factura_origen__proveedor', 'producto')
        
        # Agrupar por proveedor
        proveedores_stats = {}
        for devolucion in devoluciones_proveedor:
            if devolucion.factura_origen and devolucion.factura_origen.proveedor:
                proveedor = devolucion.factura_origen.proveedor
                if proveedor.id not in proveedores_stats:
                    proveedores_stats[proveedor.id] = {
                        'proveedor': proveedor,
                        'devoluciones': [],
                        'total_devuelto': 0,
                        'nota_credito_total': 0,
                        'productos_count': 0
                    }
                
                proveedores_stats[proveedor.id]['devoluciones'].append(devolucion)
                proveedores_stats[proveedor.id]['total_devuelto'] += devolucion.cantidad
                proveedores_stats[proveedor.id]['nota_credito_total'] += devolucion.nota_credito_proveedor
                proveedores_stats[proveedor.id]['productos_count'] += 1
        
        # Ordenar por nota de crédito total
        proveedores_ordenados = sorted(
            proveedores_stats.values(),
            key=lambda x: x['nota_credito_total'],
            reverse=True
        )
        
        context = {
            'proveedores_stats': proveedores_ordenados,
            'fecha_desde': hace_90_dias,
            'fecha_hasta': hoy,
            'total_proveedores': len(proveedores_stats),
            'total_nota_credito': sum(p['nota_credito_total'] for p in proveedores_stats.values())
        }
        
        return render(request, 'core/facturas/reporte_devoluciones_proveedor.html', context)
        
    except Exception as e:
        messages.error(arequest, f"Error generando reporte: {str(e)}")
        return redirect('facturas_dashboaard')



# ========================================================================================
# 🔧 FUNCIÓN AUXILIAR PARA DEBUGGING DEL SISTEMA COMPLETO
# ========================================================================================

@never_cache
@login_required
def debug_sistema_facturas(request):
    """
    🧪 NUEVA FUNCIÓN: Debug completo del sistema de facturas y devoluciones
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden("Solo superuser")
    
    try:
        debug_info = {
            'facturas': {
                'total': FacturaCompra.objects.count(),
                'pendientes': FacturaCompra.objects.filter(estado='pendiente').count(),
                'recibidas': FacturaCompra.objects.filter(estado='recibida').count(),
                'sin_aplicar': FacturaCompra.objects.filter(
                    estado='recibida', inventario_actualizado=False
                ).count(),
            },
            'detalles_factura': {
                'total': DetalleFacturaCompra.objects.count(),
                'aplicados': DetalleFacturaCompra.objects.filter(aplicado_inventario=True).count(),
                'con_producto': DetalleFacturaCompra.objects.filter(producto__isnull=False).count(),
                'sin_producto': DetalleFacturaCompra.objects.filter(producto__isnull=True).count(),
            },
            'inventario_tracking': {
                'total': InventarioFactura.objects.count(),
                'con_stock': InventarioFactura.objects.filter(cantidad_actual__gt=0).count(),
                'sin_stock': InventarioFactura.objects.filter(cantidad_actual=0).count(),
            },
            'devoluciones': {
                'total': Devolucion.objects.count(),
                'cliente': Devolucion.objects.filter(tipo='cliente').count(),
                'inventario': Devolucion.objects.filter(tipo='inventario').count(),
                'proveedor': Devolucion.objects.filter(tipo='proveedor').count(),
                'sin_origen': Devolucion.objects.filter(
                    venta_origen__isnull=True, factura_origen__isnull=True
                ).count(),
            },
            'productos': {
                'total': Producto.objects.count(),
                'con_stock': Producto.objects.filter(cantidad__gt=0).count(),
                'sin_stock': Producto.objects.filter(cantidad=0).count(),
                'con_tracking': Producto.objects.filter(
                    historiales_factura__isnull=False
                ).distinct().count(),
            }
        }
        
        # Problemas detectados
        problemas = []
        
        if debug_info['facturas']['sin_aplicar'] > 0:
            problemas.append(f"{debug_info['facturas']['sin_aplicar']} facturas recibidas sin aplicar al inventario")
        
        if debug_info['detalles_factura']['sin_prodaucto'] > 0:
            problemas.append(f"{debug_info['detalles_factura']['sin_producto']} detalles sin enlazar a productos")
        
        if debug_info['devoluciones']['sin_origen'] > 0:
            problemas.append(f"{debug_info['devoluciones']['sin_origen']} devoluciones sin origen definido")
        
        debug_info['problemas'] = problemas
        debug_info['sistema_saludable'] = len(problemas) == 0
        
        return JsonResponse({
            'success': True,
            'debug_info': debug_info,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@never_cache
@login_required
def devolver_desde_factura(request, detalle_id):
    """
    🔄 Devolución directa desde factura al proveedor (solo admin)
    """
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Solo administradores pueden devolver al proveedor")
    
    detalle = get_object_or_404(
        DetalleFacturaCompra.objects.select_related(
            'factura', 'factura__proveedor', 'producto'
        ), 
        id=detalle_id
    )
    
    # Validaciones
    if not detalle.producto:
        messages.error(request, "El producto debe estar enlazado al inventario para poder devolverlo")
        return redirect('factura_detalle', pk=detalle.factura.pk)
    
    if detalle.factura.estado != 'recibida':
        messages.error(request, "Solo se pueden hacer devoluciones de facturas recibidas")
        return redirect('factura_detalle', pk=detalle.factura.pk)
    
    if request.method == 'POST':
        try:
            cantidad = int(request.POST.get('cantidad', 0))
            razon = request.POST.get('razon', 'defectuoso')
            observaciones = request.POST.get('observaciones', '')
            
            # Validar cantidad
            if cantidad <= 0 or cantidad > detalle.cantidad:
                messages.error(
                    request,
                    f"Cantidad inválida. Máximo disponible: {detalle.cantidad} unidades"
                )
                return redirect('factura_detalle', pk=detalle.factura.pk)
            
            # Crear y procesar devolución inmediatamente
            devolucion = Devolucion.objects.create(
                producto=detalle.producto,
                cantidad=cantidad,
                tipo='proveedor',
                razon=razon,
                observaciones=observaciones or f'Devolución directa desde factura {detalle.factura.numero_factura}',
                solicitada_por=request.user,
                factura_origen=detalle.factura,
                estado='procesada',  # Directo a procesada
                autorizada_por=request.user,
                fecha_autorizacion=timezone.now(),
                fecha_procesamiento=timezone.now()
            )
            
            messages.success(
                request,
                f'Producto "{detalle.nombre_producto}" devuelto al proveedor {detalle.factura.proveedor.nombre}. '
                f'Cantidad: {cantidad} unidades. '
                f'Nota de crédito esperada: ${devolucion.nota_credito_proveedor:,.0f} COP'
            )
            
        except Exception as e:
            print(f"Error en devolución desde factura: {e}")
            messages.error(request, f"Error al procesar la devolución: {str(e)}")
    
    return redirect('factura_detalle', pk=detalle.factura.pk)
# ========================================================================================
# 🔧 CORRECCIÓN PARA LA FUNCIÓN productos_listar QUE ESTÁ DUPLICADA
# ========================================================================================
# Esta función estaba duplicada en tu views.py, mantener solo UNA versión

# ELIMINAR la función productos_listar duplicada que está al final de tu views.py (después de la línea 5168)
# Y mantener solo la que está en la sección de productos (líneas 1088-1174)hd