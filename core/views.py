# 🔥 IMPORTS CORREGIDOS - Agregar al inicio de views.py

import decimal
from django import forms
from django.db.models import Q, F, Sum, Count, Avg  # ✅ Agregamos Count y Avg
from decimal import Decimal, InvalidOperation
from django.utils.timezone import now
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import F, Sum
from django.http import FileResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
from datetime import date, timedelta  # ✅ Agregamos timedelta
from django.http import JsonResponse

# Imports de modelos y formularios
from .models import (Gasto, PagoBartender, Perfil, Producto, MovimientoContable, 
                     Categoria, Mesa, Venta, DetalleVenta, Notificacion, Deuda,
                     PagoCompartido, PagoMixto, Devolucion)

from .forms import (GastoForm, PagoBartenderForm, DevolucionForm, ProductoForm, 
                    CategoriaForm, RegistroForm, MesaForm)


# ========================================================================================
# AUTENTICACIÓN Y USUARIOS
# ========================================================================================

@never_cache
def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST, request.FILES)
        if form.is_valid():
            usuario = form.save()
            Perfil.objects.create(
                user=usuario,
                telefono=form.cleaned_data['telefono'],
                avatar=form.cleaned_data.get('avatar'),
                rol=form.cleaned_data['rol']
            )
            return redirect('login')
    else:
        form = RegistroForm()
    return render(request, 'core/registro.html', {'form': form})


@never_cache
def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            perfil = Perfil.objects.get(user=usuario)
            return redirect('admin_dashboard' if perfil.rol == 'admin' else 'inicio')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})


@never_cache
def custom_logout(request):
    logout(request)
    return redirect('login')


@never_cache
@login_required
def perfil(request):
    perfil = Perfil.objects.get(user=request.user)
    return render(request, 'core/perfil.html', {'perfil': perfil})


class PerfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


@never_cache
@login_required
def perfil_editar(request):
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
    if request.method == 'POST':
        request.user.delete()
        return redirect('registro')
    return render(request, 'core/cuenta_eliminar.html')


# ========================================================================================
# DASHBOARD Y ROLES
# ========================================================================================

@never_cache
@login_required
def seguimiento_mesas(request):
    """Vista de seguimiento de mesas con manejo seguro de datos corruptos"""
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")

    try:
        from decimal import Decimal, InvalidOperation
        
        # 🔥 OBTENER MESAS CON MANEJO SEGURO DE VENTAS
        mesas_data = []
        mesas_base = Mesa.objects.all().order_by('numero')
        
        for mesa in mesas_base:
            try:
                # 🔥 OBTENER LA ÚLTIMA VENTA DE FORMA SEGURA
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
                
                # 🔥 CREAR OBJETO MESA SEGURO
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
        
        from django.contrib import messages
        messages.error(request, f"Error al cargar el seguimiento de mesas: {str(e)}")
        
        # 🔥 CONTEXTO DE EMERGENCIA
        context = {
            'mesas_seguras': [],
            'total_mesas': 0,
            'mesas_activas': 0,
            'mesas_con_venta': 0,
            'error_message': f'Error al cargar los datos: {str(e)}'
        }
        
        return render(request, 'core/mesas/seguimiento_mesas.html', context)

@never_cache
@login_required
def admin_dashboard(request):
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return redirect('inicio')

    notificaciones_nuevas = Notificacion.objects.filter(leido=False).count()

    context = {
        'total_usuarios': User.objects.count(),
        'total_productos': Producto.objects.count(),
        'total_ventas': Venta.objects.count(),
        'total_movimientos': MovimientoContable.objects.count(),
        'notificaciones_nuevas': notificaciones_nuevas,
    }

    return render(request, 'core/admin_dashboard.html', context)


@never_cache
@login_required
def inicio(request):
    perfil = Perfil.objects.get(user=request.user)
    if perfil.rol != 'bartender':
        return redirect('admin_dashboard')
    return render(request, 'core/inicio.html')


@never_cache
@login_required
def asignar_roles(request):
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")

    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        # NUEVA FUNCIONALIDAD: CREAR USUARIO
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
        
        # FUNCIONALIDADES EXISTENTES
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
# CRUD CATEGORÍAS
# ========================================================================================

@never_cache
@login_required
def categorias_listar(request):
    categorias = Categoria.objects.all()
    return render(request, 'core/categorias/listar.html', {'categorias': categorias})


@never_cache
@login_required
def categoria_crear(request):
    form = CategoriaForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('categorias_listar')
    return render(request, 'core/categorias/formulario.html', {'form': form, 'titulo': 'Crear'})


@never_cache
@login_required
def categoria_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    form = CategoriaForm(request.POST or None, instance=categoria)
    if form.is_valid():
        form.save()
        return redirect('categorias_listar')
    return render(request, 'core/categorias/formulario.html', {'form': form, 'titulo': 'Editar'})


@never_cache
@login_required
def categoria_eliminar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        return redirect('categorias_listar')
    return render(request, 'core/categorias/confirmar_eliminar.html', {'categoria': categoria})


# ========================================================================================
# CRUD PRODUCTOS
# ========================================================================================

@never_cache
@login_required
def productos_bartender(request):
    perfil = Perfil.objects.get(user=request.user)
    if perfil.rol != 'bartender':
        return redirect('productos_listar')
    productos = Producto.objects.all()
    return render(request, 'core/productos/listar_bartender.html', {'productos': productos})


@never_cache
@login_required
def productos_listar(request):
    productos = Producto.objects.all()
    return render(request, 'core/productos/listar.html', {'productos': productos})


@never_cache
@login_required
def producto_crear(request):
    form = ProductoForm(request.POST or None)
    if form.is_valid():
        producto = form.save()
        
        # ✅ NUEVA FUNCIONALIDAD: Registrar inversión como gasto
        if producto.precio_costo > 0:
            MovimientoContable.objects.create(
                tipo='gasto',
                concepto=f'Inversión en producto: {producto.nombre} (x{producto.cantidad})',
                monto=producto.precio_costo * producto.cantidad,  # Costo total de la inversión
                usuario=request.user
            )
            messages.success(request, f'Producto "{producto.nombre}" creado. Inversión de ${producto.precio_costo * producto.cantidad:,.0f} COP registrada como gasto.')
        else:
            messages.success(request, f'Producto "{producto.nombre}" creado correctamente.')
        
        return redirect('productos_listar')
    return render(request, 'core/productos/formulario.html', {'form': form, 'titulo': 'Crear'})


@never_cache
@login_required
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    # 🔥 GUARDAR CANTIDAD ORIGINAL ANTES DE EDITAR
    cantidad_original = producto.cantidad
    
    form = ProductoForm(request.POST or None, instance=producto)
    if form.is_valid():
        producto_editado = form.save()
        
        # ✅ NUEVA FUNCIONALIDAD: Detectar si se aumentó la cantidad (surtir inventario)
        cantidad_nueva = producto_editado.cantidad
        if cantidad_nueva > cantidad_original:
            diferencia = cantidad_nueva - cantidad_original
            
            # Calcular la inversión adicional
            if producto_editado.precio_costo > 0:
                inversion_adicional = producto_editado.precio_costo * diferencia
                
                # Registrar como gasto/egreso
                MovimientoContable.objects.create(
                    tipo='gasto',
                    concepto=f'Surtir inventario: {producto_editado.nombre} (+{diferencia} unidades)',
                    monto=inversion_adicional,
                    usuario=request.user
                )
                
                messages.success(request, f'Producto "{producto_editado.nombre}" actualizado. Inversión adicional de ${inversion_adicional:,.0f} COP registrada como gasto (surtir +{diferencia} unidades).')
            else:
                messages.success(request, f'Producto "{producto_editado.nombre}" actualizado correctamente.')
        else:
            messages.success(request, f'Producto "{producto_editado.nombre}" actualizado correctamente.')
        
        return redirect('productos_listar')
    return render(request, 'core/productos/formulario.html', {'form': form})

@never_cache
@login_required
def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        return redirect('productos_listar')
    return render(request, 'core/productos/confirmar_eliminar.html', {'producto': producto})


# ========================================================================================
# CRUD MESAS Y VENTAS
# ========================================================================================

@never_cache
@login_required
def mesas_listar(request):
    mesas = Mesa.objects.all()
    return render(request, 'core/mesas/mesas_alistar.html', {'mesas': mesas})


@never_cache
@login_required
def mesas_activas(request):
    mesas = Mesa.objects.filter(activa=True)
    return render(request, 'core/mesas/mesas_activas.html', {'mesas': mesas})


@never_cache
@login_required
def mesa_crear(request):
    form = MesaForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('mesas_listar')
    return render(request, 'core/mesas/mesa_form.html', {'form': form, 'titulo': 'Crear Mesa'})


@never_cache
@login_required
def mesa_editar(request, pk):
    mesa = get_object_or_404(Mesa, pk=pk)
    form = MesaForm(request.POST or None, instance=mesa)
    if form.is_valid():
        form.save()
        return redirect('mesas_listar')
    return render(request, 'core/mesas/mesa_form.html', {'form': form, 'titulo': 'Editar Mesa'})


@never_cache
@login_required
def mesa_eliminar(request, pk):
    mesa = get_object_or_404(Mesa, pk=pk)
    if request.method == 'POST':
        mesa.delete()
        return redirect('mesas_listar')
    return render(request, 'core/mesas/mesa_confirmar_eliminar.html', {'mesa': mesa})


@never_cache
@login_required
def venta_mesa(request, mesa_id):
    mesa = get_object_or_404(Mesa, id=mesa_id)
    venta, _ = Venta.objects.get_or_create(mesa=mesa, cerrada=False, defaults={'mesero': request.user})
    productos = Producto.objects.filter(cantidad__gt=0)
    detalles = venta.detalles.select_related('producto')
    total = detalles.aggregate(total=Sum(F('cantidad') * F('precio_unitario')))['total'] or 0

    if request.method == 'POST':
        producto_id = request.POST.get('producto')
        cantidad = int(request.POST.get('cantidad'))
        producto = get_object_or_404(Producto, id=producto_id)

        if cantidad > producto.cantidad:
            messages.error(request, "No hay suficiente stock disponible.")
            return redirect('venta_mesa', mesa_id=mesa.id)

        detalle, creado = DetalleVenta.objects.get_or_create(
            venta=venta,
            producto=producto,
            defaults={'cantidad': cantidad, 'precio_unitario': producto.precio}
        )

        if not creado:
            detalle.cantidad += cantidad
            detalle.save()

        producto.cantidad -= cantidad
        producto.save()

        venta.total = venta.detalles.aggregate(total=Sum(F('cantidad') * F('precio_unitario')))['total'] or 0
        venta.save()
        return redirect('venta_mesa', mesa_id=mesa.id)

    return render(request, 'core/mesas/venta_mesa.html', {
        'mesa': mesa,
        'venta': venta,
        'productos': productos,
        'detalles': detalles,
        'total': total
    })


@never_cache
@login_required
def eliminar_detalle(request, detalle_id):
    detalle = get_object_or_404(DetalleVenta, id=detalle_id)
    producto = detalle.producto
    producto.cantidad += detalle.cantidad
    producto.save()

    venta = detalle.venta
    detalle.delete()
    venta.total = venta.detalles.aggregate(total=Sum(F('cantidad') * F('precio_unitario')))['total'] or 0
    venta.save()
    return redirect('venta_mesa', mesa_id=venta.mesa.id)


@never_cache
@login_required
def finalizar_venta(request, venta_id):
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
            Deuda.objects.create(
                venta=venta,
                nombre_cliente=nombre,
                telefono_cliente=telefono,
                monto_adeudado=venta.total
            )

        venta.cerrada = True
        venta.save()
        messages.success(request, f"Venta de la mesa {venta.mesa.numero} finalizada.")
        return redirect('mesas_listar')

    return redirect('venta_mesa', mesa_id=venta.mesa.id)


# ========================================================================================
# NUEVAS FUNCIONES PARA PAGOS COMPARTIDOS Y MIXTOS
# ========================================================================================

@never_cache
@login_required
def pago_compartido(request, venta_id):
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
    venta = get_object_or_404(Venta, id=venta_id)

    if request.method == 'POST':
        efectivo = float(request.POST.get('monto_efectivo', 0))
        transferencia = float(request.POST.get('monto_transferencia', 0))
        total_pagado = efectivo + transferencia

        if total_pagado < venta.total:
            messages.error(request, "El total pagado es menor al monto de la venta.")
            return redirect('pago_mixto', venta_id=venta.id)

        vuelto = total_pagado - float(venta.total)
        
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


# ========================================================================================
# CONTABILIDAD Y CIERRE DE CAJA
# ========================================================================================
@never_cache
@login_required
def cerrar_caja_dia(request):
    """Vista optimizada para mostrar el cierre de caja del día"""
    hoy = now().date()
    usuario = request.user
    
    try:
        # 🔥 QUERY OPTIMIZADA - Una sola consulta con select_related
        ventas_del_dia = Venta.objects.filter(
            fecha__date=hoy,
            cerrada=True,
            mesero=usuario
        ).select_related('mesa').prefetch_related('detalles__producto').order_by('fecha')
        
        # 🔥 ESTADÍSTICAS BÁSICAS CON AGGREGATE
        estadisticas = ventas_del_dia.aggregate(
            total_ventas=Count('id'),
            monto_total=Sum('total'),
            promedio_venta=Avg('total')
        )
        
        # 🔥 PRODUCTOS VENDIDOS CON QUERY OPTIMIZADA
        productos_vendidos = DetalleVenta.objects.filter(
            venta__fecha__date=hoy,
            venta__cerrada=True,
            venta__mesero=usuario
        ).select_related('producto', 'venta__mesa').values(
            'venta__id',
            'venta__mesa__numero',
            'venta__fecha',
            'producto__nombre',
            'cantidad',
            'precio_unitario'
        ).annotate(
            subtotal=F('cantidad') * F('precio_unitario')
        ).order_by('venta__fecha')
        
        # 🔥 PREPARAR DATOS PARA EL TEMPLATE
        ventas_procesadas = []
        total_del_dia = Decimal('0.00')
        
        for venta in ventas_del_dia:
            try:
                # Convertir total de forma segura
                total_venta = Decimal(str(venta.total)) if venta.total else Decimal('0.00')
                
                # Calcular hora en Colombia (UTC-5)
                hora_colombia = (venta.fecha - timedelta(hours=5)).strftime('%H:%M')
                
                # Obtener detalles de la venta
                detalles_venta = []
                for detalle in venta.detalles.all():
                    detalle_info = {
                        'nombre': detalle.producto.nombre if detalle.producto else "Producto eliminado",
                        'cantidad': detalle.cantidad,
                        'precio_unitario': float(detalle.precio_unitario),
                        'subtotal': float(detalle.cantidad * detalle.precio_unitario)
                    }
                    detalles_venta.append(detalle_info)
                
                # Información de la venta
                venta_info = {
                    'id': venta.id,
                    'mesa': venta.mesa,
                    'total': float(total_venta),
                    'total_formateado': f"${int(total_venta):,}".replace(',', '.'),
                    'fecha': venta.fecha,
                    'hora': hora_colombia,
                    'metodo_pago': venta.get_metodo_pago_display(),
                    'detalles': detalles_venta
                }
                
                ventas_procesadas.append(venta_info)
                total_del_dia += total_venta
                
            except Exception as e:
                print(f"Error procesando venta {venta.id}: {e}")
                continue
        
        # 🔥 FORMATEAR DATOS PARA EL TEMPLATE
        context = {
            'ventas': ventas_procesadas,
            'productos_vendidos': list(productos_vendidos),
            'total': int(total_del_dia),
            'total_formateado': f"${int(total_del_dia):,}".replace(',', '.'),
            'fecha': hoy,
            'total_ventas': len(ventas_procesadas),
            'total_productos': productos_vendidos.count(),
            'bartender': usuario.username,
            'promedio_venta': int(total_del_dia / len(ventas_procesadas)) if len(ventas_procesadas) > 0 else 0,
            'hora_actual': now().strftime('%H:%M'),
            'fecha_formateada': hoy.strftime('%d/%m/%Y'),
        }
        
        return render(request, 'core/caja/cerrar_caja_dia.html', context)
        
    except Exception as e:
        print(f"ERROR EN CERRAR_CAJA_DIA: {e}")
        import traceback
        traceback.print_exc()
        
        messages.error(request, f"Error al cargar el cierre de caja: {str(e)}")
        
        # Context de emergencia
        context = {
            'ventas': [],
            'productos_vendidos': [],
            'total': 0,
            'total_formateado': '$0',
            'fecha': hoy,
            'total_ventas': 0,
            'total_productos': 0,
            'bartender': usuario.username,
            'promedio_venta': 0,
            'hora_actual': now().strftime('%H:%M'),
            'fecha_formateada': hoy.strftime('%d/%m/%Y'),
            'error_message': f'Error al cargar los datos: {str(e)}'
        }
        
        return render(request, 'core/caja/cerrar_caja_dia.html', context)


@never_cache
@login_required
def generar_factura_html(request):
    """Generar factura HTML optimizada para cierre de caja"""
    hoy = now().date()
    usuario = request.user
    
    try:
        # 🔥 REUTILIZAR LA LÓGICA OPTIMIZADA
        ventas_del_dia = Venta.objects.filter(
            fecha__date=hoy,
            cerrada=True,
            mesero=usuario
        ).select_related('mesa').prefetch_related('detalles__producto')
        
        # 🔥 ESTADÍSTICAS RÁPIDAS
        estadisticas = ventas_del_dia.aggregate(
            total_ventas=Count('id'),
            monto_total=Sum('total')
        )
        
        # 🔥 PRODUCTOS VENDIDOS SIMPLIFICADO
        productos_vendidos = DetalleVenta.objects.filter(
            venta__fecha__date=hoy,
            venta__cerrada=True,
            venta__mesero=usuario
        ).select_related('producto', 'venta__mesa').annotate(
            subtotal=F('cantidad') * F('precio_unitario'),
            hora_venta=F('venta__fecha')
        ).order_by('venta__fecha')
        
        # 🔥 PREPARAR DATOS SIMPLIFICADOS
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
        
        # 🔥 CONTEXT SIMPLIFICADO PARA FACTURA
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
            'empresa_nombre': 'Mi Bar & Restaurant',  # Cambiar por tu nombre
            'empresa_direccion': 'Tu dirección aquí',
            'empresa_telefono': 'Tu teléfono aquí',
        }
        
        return render(request, 'core/caja/factura_imprimible.html', context)
        
    except Exception as e:
        print(f"ERROR EN GENERAR_FACTURA_HTML: {e}")
        messages.error(request, f"Error al generar la factura: {str(e)}")
        return redirect('cerrar_caja_dia')


# 🔥 FUNCIÓN ADICIONAL: RESUMEN RÁPIDO DEL DÍA (AJAX)
@never_cache
@login_required
def resumen_dia_ajax(request):
    """API AJAX para obtener resumen rápido del día"""
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Solo peticiones AJAX'}, status=400)
    
    try:
        hoy = now().date()
        usuario = request.user
        
        # 🔥 QUERY SÚPER OPTIMIZADA
        resumen = Venta.objects.filter(
            fecha__date=hoy,
            cerrada=True,
            mesero=usuario
        ).aggregate(
            total_ventas=Count('id'),
            monto_total=Sum('total'),
            promedio_venta=Avg('total')
        )
        
        # 🔥 VENTAS POR MÉTODO DE PAGO
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


# 🔥 FUNCIÓN ADICIONAL: COMPARACIÓN CON DÍAS ANTERIORES
@never_cache
@login_required
def comparacion_dias(request):
    """Comparar ventas del día actual con días anteriores"""
    try:
        hoy = now().date()
        usuario = request.user
        
        # 🔥 VENTAS DE LOS ÚLTIMOS 7 DÍAS
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
def generar_factura_html(request):
    """Generar una factura HTML descargable para cierre de caja"""
    hoy = now().date()
    usuario = request.user
    
    try:
        # Obtener los mismos datos que cerrar_caja_dia
        ventas_del_dia = []
        total_del_dia = 0
        productos_vendidos = []
        
        ventas = Venta.objects.filter(
            fecha__date=hoy,
            cerrada=True,
            mesero=usuario
        ).select_related('mesa').prefetch_related('detalles__producto').order_by('fecha')
        
        for venta in ventas:
            try:
                total_seguro = float(venta.total) if venta.total else 0
                from datetime import timedelta
                hora_colombia = venta.fecha - timedelta(hours=5)
                
                venta_info = {
                    'id': venta.id,
                    'mesa': venta.mesa,
                    'total': total_seguro,
                    'fecha': venta.fecha,
                    'hora': hora_colombia.strftime('%H:%M'),
                    'metodo_pago': venta.get_metodo_pago_display(),
                    'detalles': []
                }
                
                for detalle in venta.detalles.all():
                    producto_detalle = {
                        'nombre': detalle.producto.nombre if detalle.producto else "Producto eliminado",
                        'cantidad': detalle.cantidad,
                        'precio_unitario': float(detalle.precio_unitario),
                        'subtotal': float(detalle.cantidad * detalle.precio_unitario),
                    }
                    venta_info['detalles'].append(producto_detalle)
                    
                    productos_vendidos.append({
                        'venta_id': venta.id,
                        'mesa_numero': venta.mesa.numero if venta.mesa else 'N/A',
                        'hora': hora_colombia.strftime('%H:%M'),
                        'producto': detalle.producto.nombre if detalle.producto else "Producto eliminado",
                        'cantidad': detalle.cantidad,
                        'precio_unitario': float(detalle.precio_unitario),
                        'subtotal': float(detalle.cantidad * detalle.precio_unitario),
                    })
                
                ventas_del_dia.append(venta_info)
                total_del_dia += total_seguro
                
            except Exception as e:
                print(f"Error procesando venta {venta.id}: {e}")
                continue
        
        context = {
            'ventas': ventas_del_dia,
            'productos_vendidos': productos_vendidos,
            'total': int(total_del_dia),
            'fecha': hoy,
            'total_ventas': len(ventas_del_dia),
            'total_productos': len(productos_vendidos),
            'bartender': usuario.username,
            'promedio_venta': int(total_del_dia / len(ventas_del_dia)) if len(ventas_del_dia) > 0 else 0,
            'numero_factura': f"{hoy.strftime('%Y%m%d')}-{usuario.id:03d}",
        }
        
        # Render del template de factura
        return render(request, 'core/caja/factura_imprimible.html', context)
        
    except Exception as e:
        print(f"ERROR EN FACTURA: {e}")
        messages.error(request, "Error al generar la factura.")
        return redirect('cerrar_caja_dia')



@never_cache
@login_required
def movimientos_contables(request):
    """Vista mejorada de movimientos contables con totales"""
    
    # TOTALES GENERALES
    total_ingresos = MovimientoContable.objects.filter(tipo='ingreso').aggregate(
        total=Sum('monto'))['total'] or 0
    
    total_gastos = MovimientoContable.objects.filter(tipo='gasto').aggregate(
        total=Sum('monto'))['total'] or 0
    
    ganancia_total = total_ingresos - total_gastos
    
    # MOVIMIENTOS HOY
    hoy = now().date()
    ingresos_hoy = MovimientoContable.objects.filter(
        fecha=hoy, tipo='ingreso').aggregate(total=Sum('monto'))['total'] or 0
    
    gastos_hoy = MovimientoContable.objects.filter(
        fecha=hoy, tipo='gasto').aggregate(total=Sum('monto'))['total'] or 0
    
    # DEUDAS PENDIENTES
    deudas_pendientes = Deuda.objects.filter(pagado=False)
    total_por_cobrar = deudas_pendientes.aggregate(
        total=Sum('monto_adeudado'))['total'] or 0
    
    # VENTAS TOTALES
    ventas_totales = Venta.objects.filter(cerrada=True).aggregate(
        total=Sum('total'))['total'] or 0
    
    # ÚLTIMOS MOVIMIENTOS
    movimientos = MovimientoContable.objects.all().order_by('-fecha', '-id')[:15]
    
    context = {
        'movimientos': movimientos,
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'ganancia_total': ganancia_total,
        'ingresos_hoy': ingresos_hoy,
        'gastos_hoy': gastos_hoy,
        'total_por_cobrar': total_por_cobrar,
        'cantidad_deudores': deudas_pendientes.count(),
        'ventas_totales': ventas_totales,
    }
    
    return render(request, 'core/movimientos_contables.html', context)

# ========================================================================================
# NOTIFICACIONES
# ========================================================================================

@never_cache
@login_required
def notificar_admin(request, producto_id):
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
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Solo los administradores pueden ver notificaciones.")
    notificaciones = Notificacion.objects.all().order_by('-fecha_creacion')
    notificaciones.filter(leido=False).update(leido=True)
    return render(request, 'core/notificaciones/listar.html', {'notificaciones': notificaciones})


# ========================================================================================
# GESTIÓN DE DEUDAS
# ========================================================================================

def es_admin(user):
    return user.is_superuser or user.perfil.rol == 'admin'


@login_required
@user_passes_test(es_admin)
def ver_deudores(request):
    deudas = Deuda.objects.filter(pagado=False)
    return render(request, 'core/admin/deudores_lista.html', {'deudas': deudas})


@login_required
@user_passes_test(es_admin)
def marcar_deuda_pagada(request, deuda_id):
    deuda = get_object_or_404(Deuda, id=deuda_id)
    deuda.pagado = True
    deuda.save()
    return redirect('ver_deudores')


# Agregar al final de views.py

from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

@never_cache
@login_required
def estadisticas(request):
    """Estadísticas completas del bar"""
    hoy = timezone.now().date()
    hace_7_dias = hoy - timedelta(days=7)
    hace_30_dias = hoy - timedelta(days=30)
    
    # VENTAS POR PERÍODO
    ventas_hoy = Venta.objects.filter(fecha__date=hoy, cerrada=True).aggregate(
        total=Sum('total'), count=Count('id'))
    ventas_semana = Venta.objects.filter(fecha__date__gte=hace_7_dias, cerrada=True).aggregate(
        total=Sum('total'), count=Count('id'))
    ventas_mes = Venta.objects.filter(fecha__date__gte=hace_30_dias, cerrada=True).aggregate(
        total=Sum('total'), count=Count('id'))
    
    # PRODUCTOS MÁS VENDIDOS
    productos_top = DetalleVenta.objects.filter(venta__cerrada=True)\
        .values('producto__nombre')\
        .annotate(total_vendido=Sum('cantidad'), ingresos=Sum(F('cantidad') * F('precio_unitario')))\
        .order_by('-total_vendido')[:5]
    
    # CLIENTES FRECUENTES (por teléfono en deudas)
    clientes_frecuentes = Deuda.objects.values('telefono_cliente', 'nombre_cliente')\
        .annotate(visitas=Count('id'), total_gastado=Sum('monto_adeudado'))\
        .order_by('-visitas')[:5]
    
    # UTILIDADES POR PERÍODO  
    mov_hoy = MovimientoContable.objects.filter(fecha=hoy)
    mov_semana = MovimientoContable.objects.filter(fecha__gte=hace_7_dias)
    mov_mes = MovimientoContable.objects.filter(fecha__gte=hace_30_dias)
    
    utilidad_hoy = (mov_hoy.filter(tipo='ingreso').aggregate(Sum('monto'))['monto__sum'] or 0) - \
                   (mov_hoy.filter(tipo='gasto').aggregate(Sum('monto'))['monto__sum'] or 0)
    
    utilidad_semana = (mov_semana.filter(tipo='ingreso').aggregate(Sum('monto'))['monto__sum'] or 0) - \
                      (mov_semana.filter(tipo='gasto').aggregate(Sum('monto'))['monto__sum'] or 0)
    
    utilidad_mes = (mov_mes.filter(tipo='ingreso').aggregate(Sum('monto'))['monto__sum'] or 0) - \
                   (mov_mes.filter(tipo='gasto').aggregate(Sum('monto'))['monto__sum'] or 0)
    
    # MÉTODOS DE PAGO MÁS USADOS
    metodos_pago = Venta.objects.filter(cerrada=True)\
        .values('metodo_pago')\
        .annotate(count=Count('id'), total=Sum('total'))\
        .order_by('-count')
    
    # TOTALES PARA GRÁFICAS
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


@login_required
def recomendaciones_precio(request):
    """API para obtener recomendaciones inteligentes de precios"""
    if request.method == 'GET':
        costo = float(request.GET.get('costo', 0))
        categoria_id = request.GET.get('categoria')
        
        if costo <= 0:
            return JsonResponse({'error': 'Costo inválido'})
        
        recomendaciones = []
        
        # ANÁLISIS POR CATEGORÍA
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
        
        # ANÁLISIS GENERAL DEL INVENTARIO
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
        
        # RECOMENDACIONES ESTÁNDAR DE LA INDUSTRIA
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
        
        # ANÁLISIS DE COMPETITIVIDAD
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



@never_cache
@login_required
def gastos_dashboard(request):
    """Dashboard principal de gastos"""
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")

    # Estadísticas generales
    hoy = now().date()
    hace_30_dias = hoy - timedelta(days=30)
    
    # Gastos por categoría
    gastos_generales = Gasto.objects.all()
    pagos_bartender = PagoBartender.objects.all()
    
    # Totales
    total_gastos_generales = gastos_generales.aggregate(Sum('monto'))['monto__sum'] or 0
    total_pagos_bartender = pagos_bartender.aggregate(Sum('monto'))['monto__sum'] or 0
    total_gastos = total_gastos_generales + total_pagos_bartender
    
    # Gastos del mes actual
    gastos_mes = Gasto.objects.filter(fecha__gte=hace_30_dias).aggregate(Sum('monto'))['monto__sum'] or 0
    pagos_mes = PagoBartender.objects.filter(fecha_pago__gte=hace_30_dias).aggregate(Sum('monto'))['monto__sum'] or 0
    total_mes = gastos_mes + pagos_mes
    
    # Gastos de hoy
    gastos_hoy = Gasto.objects.filter(fecha=hoy).aggregate(Sum('monto'))['monto__sum'] or 0
    pagos_hoy = PagoBartender.objects.filter(fecha_pago=hoy).aggregate(Sum('monto'))['monto__sum'] or 0
    total_hoy = gastos_hoy + pagos_hoy
    
    # Últimos movimientos
    ultimos_gastos = Gasto.objects.all().order_by('-fecha')[:10]
    ultimos_pagos = PagoBartender.objects.all().order_by('-fecha_pago')[:10]
    
    # Bartenders para el formulario
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
    """Crear nuevo gasto general"""
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    if request.method == 'POST':
        form = GastoForm(request.POST)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.registrado_por = request.user
            gasto.save()
            messages.success(request, f'Gasto "{gasto.concepto}" registrado por ${gasto.monto:,.0f} COP')
            return redirect('gastos_dashboard')
        else:
            messages.error(request, 'Error en el formulario. Verifica los datos.')
    
    return redirect('gastos_dashboard')

@never_cache
@login_required
def crear_pago_bartender(request):
    """Crear pago a bartender"""
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    if request.method == 'POST':
        form = PagoBartenderForm(request.POST)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.pagado_por = request.user
            pago.save()
            messages.success(request, f'Pago de ${pago.monto:,.0f} COP registrado para {pago.bartender.username}')
            return redirect('gastos_dashboard')
        else:
            messages.error(request, 'Error en el formulario. Verifica los datos.')
    
    return redirect('gastos_dashboard')

@never_cache
@login_required
def eliminar_gasto(request, gasto_id):
    """Eliminar gasto general"""
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
    """Eliminar pago a bartender"""
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
# SISTEMA DE DEVOLUCIONES
# ========================================================================================

@never_cache
@login_required
def solicitar_devolucion(request):
    """Bartender solicita una devolución"""
    perfil = request.user.perfil
    if perfil.rol not in ['bartender', 'admin']:
        return HttpResponseForbidden("Acceso denegado")
    
    if request.method == 'POST':
        form = DevolucionForm(request.POST)
        if form.is_valid():
            devolucion = form.save(commit=False)
            devolucion.solicitada_por = request.user
            devolucion.save()
            
            messages.success(request, f'Solicitud de devolución enviada. Se ha solicitado devolver {devolucion.cantidad} unidades de {devolucion.producto.nombre}.')
            return redirect('mis_devoluciones')
    else:
        form = DevolucionForm()
    
    return render(request, 'core/devoluciones/solicitar.html', {'form': form})

@never_cache
@login_required
def mis_devoluciones(request):
    """Ver mis solicitudes de devolución (bartender)"""
    perfil = request.user.perfil
    if perfil.rol not in ['bartender', 'admin']:
        return HttpResponseForbidden("Acceso denegado")
    
    devoluciones = Devolucion.objects.filter(solicitada_por=request.user).order_by('-fecha_solicitud')
    
    context = {
        'devoluciones': devoluciones,
        'title': 'Mis Solicitudes de Devolución'
    }
    
    return render(request, 'core/devoluciones/mis_devoluciones.html', context)

@never_cache
@login_required
def gestionar_devoluciones(request):
    """Admin ve todas las devoluciones pendientes"""
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    devoluciones_pendientes = Devolucion.objects.filter(estado='pendiente').order_by('-fecha_solicitud')
    devoluciones_procesadas = Devolucion.objects.exclude(estado='pendiente').order_by('-fecha_solicitud')[:10]
    
    context = {
        'devoluciones_pendientes': devoluciones_pendientes,
        'devoluciones_procesadas': devoluciones_procesadas,
        'total_pendientes': devoluciones_pendientes.count()
    }
    
    return render(request, 'core/devoluciones/gestionar.html', context)

@never_cache
@login_required
def autorizar_devolucion(request, devolucion_id):
    """Admin autoriza o rechaza una devolución"""
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    devolucion = get_object_or_404(Devolucion, id=devolucion_id)
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        comentario = request.POST.get('comentario_admin', '')
        
        if accion == 'autorizar':
            devolucion.estado = 'autorizada'
            devolucion.comentario_admin = comentario
            devolucion.autorizada_por = request.user
            devolucion.save()
            
            messages.success(request, f'Devolución de {devolucion.producto.nombre} autorizada correctamente.')
            
        elif accion == 'rechazar':
            devolucion.estado = 'rechazada'
            devolucion.comentario_admin = comentario
            devolucion.autorizada_por = request.user
            devolucion.save()
            
            messages.info(request, f'Devolución de {devolucion.producto.nombre} rechazada.')
        
        return redirect('gestionar_devoluciones')
    
    return render(request, 'core/devoluciones/autorizar.html', {'devolucion': devolucion})

@never_cache
@login_required
def procesar_devolucion(request, devolucion_id):
    """Admin procesa una devolución autorizada (devuelve al inventario)"""
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")
    
    devolucion = get_object_or_404(Devolucion, id=devolucion_id)
    
    if devolucion.estado != 'autorizada':
        messages.error(request, 'Solo se pueden procesar devoluciones autorizadas.')
        return redirect('gestionar_devoluciones')
    
    if request.method == 'POST':
        # El procesamiento se hace automáticamente en el modelo cuando cambia a 'procesada'
        devolucion.estado = 'procesada'
        devolucion.save()
        
        messages.success(request, f'Devolución procesada. Se han devuelto {devolucion.cantidad} unidades de {devolucion.producto.nombre} al inventario.')
        return redirect('gestionar_devoluciones')
    
    return render(request, 'core/devoluciones/procesar.html', {'devolucion': devolucion})

@never_cache
@login_required
def devoluciones_api_pendientes(request):
    """API para obtener cantidad de devoluciones pendientes - CORREGIDA"""
    try:
        # 🔥 VERIFICAR QUE EL USUARIO TENGA PERFIL
        if not hasattr(request.user, 'perfil'):
            return JsonResponse({'error': 'Usuario sin perfil'}, status=403)
        
        # 🔥 SOLO ADMIN PUEDE VER DEVOLUCIONES PENDIENTES
        if request.user.perfil.rol != 'admin':
            return JsonResponse({'error': 'Acceso denegado - Solo administradores'}, status=403)
        
        # 🔥 CONTAR DEVOLUCIONES PENDIENTES
        pendientes = Devolucion.objects.filter(estado='pendiente').count()
        
        return JsonResponse({
            'success': True,
            'pendientes': pendientes
        })
        
    except Exception as e:
        print(f"Error en devoluciones_api_pendientes: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'pendientes': 0
        }, status=500)


# AGREGAR ESTA FUNCIÓN AL INICIO DE TU views.py (después de los imports)

def formatear_peso_colombiano(valor):
    """
    Convierte números a formato peso colombiano: $2.224.600
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
    Solo agrega separadores de miles con puntos: 2.224.600
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
    
   
@never_cache
@login_required
def admin_ventas(request):
    """Vista ultra-robusta de ventas para administradores - Maneja datos corruptos"""
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")

    try:
        from datetime import datetime, timedelta
        from django.utils import timezone
        from django.core.paginator import Paginator
        from decimal import Decimal, InvalidOperation
        from django.db import connection
        
        # 🔥 OBTENER PARÁMETROS DE FILTRO DE FORMA SEGURA
        filtro_fecha = request.GET.get('filtro_fecha', 'hoy')
        filtro_metodo = request.GET.get('filtro_metodo', 'todos')
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_fin = request.GET.get('fecha_fin')
        buscar_mesa = request.GET.get('buscar_mesa')
        buscar_mesero = request.GET.get('buscar_mesero')

        # 🔥 APLICAR FILTROS DE FECHA SEGUROS Y CORREGIDOS
        hoy = timezone.now().date()
        print(f"DEBUG: Filtro fecha seleccionado: {filtro_fecha}")
        
        # 🔥 CONSTRUIR FILTROS USANDO VALUES() PARA EVITAR PROBLEMAS DE DECIMAL
        ventas_base = Venta.objects.filter(cerrada=True).values(
            'id', 'fecha', 'total', 'metodo_pago', 'cerrada', 
            'mesa__numero', 'mesero__username', 'mesero__first_name', 
            'mesero__last_name', 'mesero__id'
        )
        
        try:
            if filtro_fecha == 'hoy':
                ventas_base = ventas_base.filter(fecha__date=hoy)
                print(f"DEBUG: Filtrando por hoy: {hoy}")
                
            elif filtro_fecha == 'ayer':
                ayer = hoy - timedelta(days=1)
                ventas_base = ventas_base.filter(fecha__date=ayer)
                print(f"DEBUG: Filtrando por ayer: {ayer}")
                
            elif filtro_fecha == 'ultima_semana':
                hace_7_dias = hoy - timedelta(days=7)
                ventas_base = ventas_base.filter(fecha__date__gte=hace_7_dias, fecha__date__lte=hoy)
                print(f"DEBUG: Filtrando última semana: {hace_7_dias} a {hoy}")
                
            elif filtro_fecha == 'este_mes':
                primer_dia_mes = hoy.replace(day=1)
                ventas_base = ventas_base.filter(fecha__date__gte=primer_dia_mes, fecha__date__lte=hoy)
                print(f"DEBUG: Filtrando este mes: {primer_dia_mes} a {hoy}")
                
            elif filtro_fecha == 'ultimo_mes':
                hace_30_dias = hoy - timedelta(days=30)
                ventas_base = ventas_base.filter(fecha__date__gte=hace_30_dias, fecha__date__lte=hoy)
                print(f"DEBUG: Filtrando último mes: {hace_30_dias} a {hoy}")
                
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
                print(f"DEBUG: Filtrando este trimestre: {primer_dia_trimestre} a {hoy}")
                
            elif filtro_fecha == 'este_año':
                primer_dia_año = hoy.replace(month=1, day=1)
                ventas_base = ventas_base.filter(fecha__date__gte=primer_dia_año, fecha__date__lte=hoy)
                print(f"DEBUG: Filtrando este año: {primer_dia_año} a {hoy}")
                
            elif filtro_fecha == 'todas':
                print("DEBUG: Mostrando todas las ventas")
                pass
                
            elif filtro_fecha == 'personalizado' and fecha_inicio and fecha_fin:
                try:
                    inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                    fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                    ventas_base = ventas_base.filter(fecha__date__gte=inicio, fecha__date__lte=fin)
                    print(f"DEBUG: Filtrando rango personalizado: {inicio} a {fin}")
                except ValueError as e:
                    print(f"DEBUG: Error en fechas personalizadas: {e}")
                    ventas_base = ventas_base.filter(fecha__date=hoy)
            else:
                ventas_base = ventas_base.filter(fecha__date=hoy)
                print(f"DEBUG: Filtro por defecto - hoy: {hoy}")
                
        except Exception as e:
            print(f"DEBUG: Error en filtros de fecha: {e}")
            ventas_base = ventas_base.filter(fecha__date=hoy)

        # 🔥 FILTRO POR MÉTODO DE PAGO SEGURO
        if filtro_metodo != 'todos':
            metodos_validos = [choice[0] for choice in Venta.METODO_PAGO_CHOICES]
            if filtro_metodo in metodos_validos:
                ventas_base = ventas_base.filter(metodo_pago=filtro_metodo)

        # 🔥 FILTRO POR MESA SEGURO
        if buscar_mesa:
            try:
                numero_mesa = int(buscar_mesa)
                ventas_base = ventas_base.filter(mesa__numero=numero_mesa)
            except (ValueError, TypeError):
                pass

        # 🔥 FILTRO POR MESERO SEGURO
        if buscar_mesero:
            try:
                mesero_id = int(buscar_mesero)
                ventas_base = ventas_base.filter(mesero_id=mesero_id)
            except (ValueError, TypeError):
                pass

        # 🔥 LIMITAR RESULTADOS Y ORDENAR
        ventas_base = ventas_base.order_by('-fecha')[:1000]

        # 🔥 OBTENER CONTEO ANTES DE PROCESAR
        total_ventas_encontradas = len(ventas_base)
        print(f"DEBUG: Total ventas encontradas con filtros: {total_ventas_encontradas}")
        
        if total_ventas_encontradas == 0:
            print("DEBUG: No se encontraron ventas con los filtros aplicados")
        
        # 🔥 PROCESAR VENTAS DE FORMA ULTRA-SEGURA
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
                # 🔥 CONVERSIÓN ULTRA-SEGURA DEL TOTAL
                total_seguro = Decimal('0.00')
                total_raw = venta_data.get('total')
                
                try:
                    if total_raw is not None:
                        # Intentar conversión directa
                        if isinstance(total_raw, Decimal):
                            total_seguro = total_raw
                        elif isinstance(total_raw, (int, float)):
                            total_seguro = Decimal(str(total_raw))
                        elif isinstance(total_raw, str):
                            # Limpiar string de caracteres no numéricos
                            total_clean = ''.join(c for c in total_raw if c.isdigit() or c in '.-')
                            if total_clean and total_clean not in ['-', '.', '-.']:
                                total_seguro = Decimal(total_clean)
                        else:
                            # Intentar conversión forzada
                            total_seguro = Decimal(str(float(total_raw)))
                            
                except (InvalidOperation, ValueError, TypeError, OverflowError) as e:
                    print(f"DEBUG: Error convirtiendo total de venta {venta_data['id']}: {total_raw} -> {e}")
                    total_seguro = Decimal('0.00')
                    ventas_con_errores += 1

                # 🔥 HORA SEGURA (UTC-5 para Colombia)
                hora_colombia = "N/A"
                try:
                    if venta_data.get('fecha'):
                        fecha_colombia = venta_data['fecha'] - timedelta(hours=5)
                        hora_colombia = fecha_colombia.strftime('%H:%M')
                except:
                    hora_colombia = "N/A"

                # 🔥 FORMATEO SEGURO DEL TOTAL
                total_formateado = "$0"
                try:
                    if total_seguro > 0:
                        total_int = int(total_seguro)
                        total_formateado = f"${total_int:,}".replace(',', '.')
                except:
                    total_formateado = "$0"

                # 🔥 CREAR OBJETO VENTA SEGURO
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
                
                # 🔥 SUMAR TOTALES POR MÉTODO DE FORMA SEGURA
                metodo = venta_data['metodo_pago'] or 'efectivo'
                if metodo in totales_por_metodo:
                    totales_por_metodo[metodo] += total_seguro
                
            except Exception as e:
                print(f"DEBUG: Error general procesando venta {venta_data.get('id', 'N/A')}: {e}")
                ventas_con_errores += 1
                continue
        
        print(f"DEBUG: Ventas evaluadas: {ventas_evaluadas}, Ventas procesadas: {len(ventas_procesadas)}, Errores: {ventas_con_errores}")

        # 🔥 CALCULAR ESTADÍSTICAS SEGURAS
        total_ventas = len(ventas_procesadas)
        monto_total = sum(v['total'] for v in ventas_procesadas)
        
        print(f"DEBUG: Total final de ventas: {total_ventas}, Monto total: {monto_total}")

        # 🔥 PAGINACIÓN SEGURA
        paginator = Paginator(ventas_procesadas, 20)
        page_number = request.GET.get('page', 1)
        
        try:
            page_number = int(page_number)
        except (ValueError, TypeError):
            page_number = 1
            
        ventas_paginadas = paginator.get_page(page_number)

        # 🔥 OBTENER MESEROS DISPONIBLES DE FORMA SEGURA
        try:
            meseros_disponibles = User.objects.filter(
                perfil__rol='bartender'
            ).select_related('perfil').order_by('username')[:20]
        except:
            meseros_disponibles = []

        # 🔥 CONVERTIR DECIMALES A ENTEROS PARA TEMPLATES
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

        # 🔥 CONTEXTO FINAL SEGURO
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
        
        # 🔥 ADVERTENCIA SI HAY VENTAS CON ERRORES
        if ventas_con_errores > 0:
            from django.contrib import messages
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
        
        # 🔥 CONTEXTO DE EMERGENCIA COMPLETAMENTE SEGURO
        from django.contrib import messages
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