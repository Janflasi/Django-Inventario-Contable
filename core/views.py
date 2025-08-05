import decimal
from django import forms
from django.db.models import Q
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
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
from datetime import date
from django.http import JsonResponse
from .models import Gasto, PagoBartender  # Asegúrate de importar estos modelos
from .forms import GastoForm, PagoBartenderForm, DevolucionForm

from .forms import ProductoForm, CategoriaForm, RegistroForm, MesaForm
from .models import (Perfil, Producto, MovimientoContable, Categoria,
                     Mesa, Venta, DetalleVenta, Notificacion, Deuda,
                     PagoCompartido, PagoMixto, Devolucion)



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
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")

    mesas = Mesa.objects.all().prefetch_related('ventas')
    return render(request, 'core/mesas/seguimiento_mesas.html', {'mesas': mesas})


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
    form = ProductoForm(request.POST or None, instance=producto)
    if form.is_valid():
        form.save()
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
    """Versión simplificada que usa el método seguro del modelo"""
    hoy = now().date()
    usuario = request.user
    
    try:
        # 🔥 OBTENER VENTAS CON MÉTODO SEGURO
        ventas_del_dia = []
        total_del_dia = 0
        
        # Usar SQL directa para obtener IDs
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM core_venta 
                WHERE date(fecha) = %s AND cerrada = 1 AND mesero_id = %s
                ORDER BY fecha DESC
            """, [hoy.strftime('%Y-%m-%d'), usuario.id])
            
            venta_ids = [row[0] for row in cursor.fetchall()]
        
        # Procesar cada venta individualmente
        for venta_id in venta_ids:
            try:
                venta = Venta.objects.get(id=venta_id)
                total_seguro = float(venta.total) if venta.total else 0
                
                ventas_del_dia.append({
                    'id': venta.id,
                    'mesa': venta.mesa,
                    'total': total_seguro,
                    'fecha': venta.fecha
                })
                
                total_del_dia += total_seguro
                
            except Exception as e:
                print(f"Error procesando venta {venta_id}: {e}")
                continue
        
        # Si es POST, generar PDF
        if request.method == 'POST':
            try:
                buffer = io.BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter
                
                p.setFont("Helvetica-Bold", 14)
                p.drawString(200, height - 40, f"Cierre de Caja - {usuario.username}")
                p.setFont("Helvetica", 12)
                p.drawString(40, height - 80, f"Fecha: {hoy.strftime('%d/%m/%Y')}")
                p.drawString(40, height - 100, f"Total ventas del día: ${total_del_dia:,.0f} COP")
                
                y = height - 140
                p.setFont("Helvetica-Bold", 11)
                p.drawString(40, y, "Ventas realizadas:")
                y -= 20
                
                p.setFont("Helvetica", 10)
                for venta in ventas_del_dia:
                    mesa_texto = f"Mesa {venta['mesa'].numero}" if venta['mesa'] else "Sin mesa"
                    p.drawString(50, y, f"Venta #{venta['id']} - {mesa_texto} - ${venta['total']:,.0f} COP")
                    y -= 15
                    if y < 60:
                        p.showPage()
                        y = height - 60
                
                p.showPage()
                p.save()
                buffer.seek(0)
                
                return FileResponse(
                    buffer, 
                    as_attachment=True, 
                    filename=f'cierre_caja_{usuario.username}_{hoy}.pdf'
                )
                
            except Exception as e:
                messages.error(request, f"Error generando PDF: {str(e)}")
                return redirect('cerrar_caja_dia')
        
        # Renderizar template
        context = {
            'ventas': ventas_del_dia,
            'total': int(total_del_dia),
            'fecha': hoy,
        }
        
        return render(request, 'core/caja/cerrar_caja_dia.html', context)
        
    except Exception as e:
        print(f"ERROR GENERAL: {e}")
        import traceback
        traceback.print_exc()
        
        # Contexto de error
        messages.error(request, "Error al cargar las ventas. Algunos datos pueden estar corruptos.")
        context = {
            'ventas': [],
            'total': 0,
            'fecha': hoy,
        }
        
        return render(request, 'core/caja/cerrar_caja_dia.html', context)











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
    """API para obtener cantidad de devoluciones pendientes"""
    if request.user.perfil.rol != 'admin':
        return JsonResponse({'error': 'Acceso denegado'}, status=403)
    
    pendientes = Devolucion.objects.filter(estado='pendiente').count()
    return JsonResponse({'pendientes': pendientes})



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
    """Vista ultra-segura de ventas para administradores"""
    perfil = request.user.perfil
    if perfil.rol != 'admin':
        return HttpResponseForbidden("Acceso denegado")

    try:
        # Obtener parámetros de filtro
        filtro_fecha = request.GET.get('filtro_fecha', 'hoy')
        filtro_metodo = request.GET.get('filtro_metodo', 'todos')
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_fin = request.GET.get('fecha_fin')
        buscar_mesa = request.GET.get('buscar_mesa')
        buscar_mesero = request.GET.get('buscar_mesero')

        # Query MUY básica - evitamos problemas de decimales
        from django.db import connection
        
        # Usamos SQL cruda para evitar el problema de decimales
        with connection.cursor() as cursor:
            sql = """
                SELECT id, fecha, total, metodo_pago, cerrada, mesa_id, mesero_id
                FROM core_venta 
                WHERE cerrada = 1 
                AND total IS NOT NULL 
                AND CAST(total AS TEXT) != '' 
                AND CAST(total AS TEXT) != 'None'
                ORDER BY fecha DESC 
                LIMIT 100
            """
            cursor.execute(sql)
            ventas_raw = cursor.fetchall()

        # Convertir a objetos más seguros
        ventas_seguras = []
        total_efectivo = 0
        total_transferencia = 0
        total_credito = 0
        total_mixto = 0
        total_compartido = 0
        
        for venta_data in ventas_raw:
            try:
                # Obtener objetos relacionados de forma segura
                try:
                    mesa = Mesa.objects.get(id=venta_data[5]) if venta_data[5] else None
                except:
                    mesa = None
                
                try:
                    mesero = User.objects.get(id=venta_data[6]) if venta_data[6] else None
                except:
                    mesero = None

                # Obtener total de forma segura
                total_venta = 0
                try:
                    total_venta = float(venta_data[2]) if venta_data[2] else 0
                except:
                    total_venta = 0

                # Crear objeto seguro
                venta_segura = {
                    'id': venta_data[0],
                    'fecha': venta_data[1],
                    'total': total_venta,
                    'metodo_pago': venta_data[3] or 'efectivo',
                    'cerrada': venta_data[4],
                    'mesa': mesa,
                    'mesero': mesero,
                    'get_metodo_pago_display': dict(Venta.METODO_PAGO_CHOICES).get(venta_data[3], venta_data[3])
                }
                ventas_seguras.append(venta_segura)
                
                # Sumar por método de pago
                metodo = venta_data[3] or 'efectivo'
                if metodo == 'efectivo':
                    total_efectivo += total_venta
                elif metodo == 'transferencia':
                    total_transferencia += total_venta
                elif metodo == 'credito':
                    total_credito += total_venta
                elif metodo == 'mixto':
                    total_mixto += total_venta
                elif metodo == 'compartido':
                    total_compartido += total_venta
                    
            except Exception as e:
                print(f"Error procesando venta {venta_data[0]}: {e}")
                continue

        # Aplicar filtros básicos en Python (más seguro)
        if filtro_metodo != 'todos':
            ventas_filtradas = []
            total_efectivo = 0
            total_transferencia = 0
            total_credito = 0
            total_mixto = 0
            total_compartido = 0
            
            for v in ventas_seguras:
                if v['metodo_pago'] == filtro_metodo:
                    ventas_filtradas.append(v)
                    # Recalcular totales con filtro
                    if v['metodo_pago'] == 'efectivo':
                        total_efectivo += v['total']
                    elif v['metodo_pago'] == 'transferencia':
                        total_transferencia += v['total']
                    elif v['metodo_pago'] == 'credito':
                        total_credito += v['total']
                    elif v['metodo_pago'] == 'mixto':
                        total_mixto += v['total']
                    elif v['metodo_pago'] == 'compartido':
                        total_compartido += v['total']
            
            ventas_seguras = ventas_filtradas
        
        if buscar_mesa:
            try:
                numero_mesa = int(buscar_mesa)
                ventas_seguras = [v for v in ventas_seguras if v['mesa'] and v['mesa'].numero == numero_mesa]
            except:
                pass

        # Estadísticas básicas
        total_ventas = len(ventas_seguras)
        monto_total = sum(v['total'] for v in ventas_seguras)

        # Paginación simple
        from django.core.paginator import Paginator
        
        # Crear objetos mock para paginación
        class VentaMock:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        ventas_mock = [VentaMock(v) for v in ventas_seguras]
        paginator = Paginator(ventas_mock, 20)
        page_number = request.GET.get('page', 1)
        ventas_paginadas = paginator.get_page(page_number)

        # Meseros disponibles (de forma segura)
        try:
            meseros_disponibles = User.objects.filter(perfil__rol='bartender').order_by('username')[:10]
        except:
            meseros_disponibles = []

        # 🔥 ENVIAR NÚMEROS COMO ENTEROS PARA QUE EL TEMPLATE LOS FORMATEE
        context = {
            'ventas': ventas_paginadas,
            'total_ventas': total_ventas,
            'monto_total': int(monto_total) if monto_total else 0,  # 🔥 COMO ENTERO
            'meseros_disponibles': meseros_disponibles,
            
            # Totales por método de pago - COMO ENTEROS 🔥
            'total_efectivo': int(total_efectivo) if total_efectivo else 0,
            'total_transferencia': int(total_transferencia) if total_transferencia else 0,
            'total_credito': int(total_credito) if total_credito else 0,
            'total_mixto': int(total_mixto) if total_mixto else 0,
            'total_compartido': int(total_compartido) if total_compartido else 0,
            
            # Filtros aplicados
            'filtro_fecha': filtro_fecha,
            'filtro_metodo': filtro_metodo,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'buscar_mesa': buscar_mesa,
            'buscar_mesero': buscar_mesero,
            
            # Opciones para filtros
            'metodos_pago': Venta.METODO_PAGO_CHOICES,
        }
        
        return render(request, 'core/ventas/admin_ventas.html', context)
        
    except Exception as e:
        print(f"ERROR EN ADMIN_VENTAS: {e}")
        import traceback
        traceback.print_exc()
        
        # Si todo falla, contexto completamente vacío pero funcional
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
            'filtro_fecha': 'hoy',
            'filtro_metodo': 'todos',
            'fecha_inicio': None,
            'fecha_fin': None,
            'buscar_mesa': None,
            'buscar_mesero': None,
            'metodos_pago': Venta.METODO_PAGO_CHOICES,
        }
        
        return render(request, 'core/ventas/admin_ventas.html', context)