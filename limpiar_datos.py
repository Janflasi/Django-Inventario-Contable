# 🔥 SCRIPT PARA LIMPIAR DATOS CORRUPTOS EN VENTAS
# Ejecutar como: python manage.py shell < limpiar_datos_corruptos.py

from core.models import Venta, MovimientoContable
from decimal import Decimal, InvalidOperation
from django.db import transaction

def limpiar_ventas_corruptas():
    """
    Identifica y limpia ventas con datos corruptos en el campo 'total'
    """
    print("🔍 Iniciando análisis de ventas corruptas...")
    
    ventas_corruptas = []
    ventas_procesadas = 0
    ventas_corregidas = 0
    
    # Obtener todas las ventas
    todas_las_ventas = Venta.objects.all()
    total_ventas = todas_las_ventas.count()
    print(f"📊 Analizando {total_ventas} ventas en total...")
    
    for venta in todas_las_ventas:
        ventas_procesadas += 1
        
        # Mostrar progreso cada 100 ventas
        if ventas_procesadas % 100 == 0:
            print(f"📈 Progreso: {ventas_procesadas}/{total_ventas} ventas procesadas...")
        
        try:
            # Intentar acceder al campo total
            total_actual = venta.total
            
            # Intentar convertir a Decimal
            if total_actual is not None:
                total_decimal = Decimal(str(total_actual))
                
                # Verificar que sea un número válido
                if total_decimal < 0:
                    print(f"⚠️ Venta #{venta.id}: Total negativo detectado: {total_decimal}")
                    ventas_corruptas.append({
                        'venta': venta,
                        'problema': 'total_negativo',
                        'valor_actual': total_actual
                    })
                    
        except (InvalidOperation, ValueError, TypeError, OverflowError) as e:
            print(f"❌ Venta #{venta.id}: Datos corruptos detectados: {e}")
            ventas_corruptas.append({
                'venta': venta,
                'problema': 'conversion_error',
                'valor_actual': venta.total,
                'error': str(e)
            })
    
    print(f"\n📋 RESUMEN DEL ANÁLISIS:")
    print(f"   • Ventas procesadas: {ventas_procesadas}")
    print(f"   • Ventas corruptas encontradas: {len(ventas_corruptas)}")
    
    if len(ventas_corruptas) > 0:
        print(f"\n🔧 REPARANDO VENTAS CORRUPTAS...")
        
        with transaction.atomic():
            for item in ventas_corruptas:
                venta = item['venta']
                problema = item['problema']
                
                try:
                    if problema == 'total_negativo':
                        # Convertir totales negativos a 0
                        print(f"🔄 Corrigiendo venta #{venta.id}: {item['valor_actual']} → 0.00")
                        venta.total = Decimal('0.00')
                        venta.save()
                        ventas_corregidas += 1
                        
                    elif problema == 'conversion_error':
                        # Intentar recuperar el total de los detalles de venta
                        total_desde_detalles = Decimal('0.00')
                        
                        for detalle in venta.detalles.all():
                            try:
                                subtotal = detalle.cantidad * detalle.precio_unitario
                                total_desde_detalles += subtotal
                            except:
                                continue
                        
                        if total_desde_detalles > 0:
                            print(f"🔄 Corrigiendo venta #{venta.id}: Recuperado desde detalles: {total_desde_detalles}")
                            venta.total = total_desde_detalles
                        else:
                            print(f"🔄 Corrigiendo venta #{venta.id}: Sin detalles válidos, estableciendo en 0.00")
                            venta.total = Decimal('0.00')
                        
                        # Usar update para evitar el método save() problemático
                        Venta.objects.filter(id=venta.id).update(total=venta.total)
                        ventas_corregidas += 1
                        
                except Exception as e:
                    print(f"❌ Error al corregir venta #{venta.id}: {e}")
                    # Si no se puede corregir, establecer en 0
                    try:
                        Venta.objects.filter(id=venta.id).update(total=Decimal('0.00'))
                        print(f"🔄 Venta #{venta.id} establecida en 0.00 como fallback")
                        ventas_corregidas += 1
                    except Exception as e2:
                        print(f"❌ Error crítico en venta #{venta.id}: {e2}")
        
        print(f"\n✅ REPARACIÓN COMPLETADA:")
        print(f"   • Ventas corregidas: {ventas_corregidas}")
        print(f"   • Ventas que no pudieron corregirse: {len(ventas_corruptas) - ventas_corregidas}")
        
    else:
        print(f"\n✅ ¡Excelente! No se encontraron ventas corruptas.")
    
    return len(ventas_corruptas), ventas_corregidas

def verificar_movimientos_contables():
    """
    Verifica que los movimientos contables tengan montos válidos
    """
    print(f"\n🔍 Verificando movimientos contables...")
    
    movimientos_corruptos = []
    movimientos_procesados = 0
    
    for movimiento in MovimientoContable.objects.all():
        movimientos_procesados += 1
        
        try:
            monto_decimal = Decimal(str(movimiento.monto))
            if monto_decimal < 0:
                print(f"⚠️ Movimiento #{movimiento.id}: Monto negativo: {monto_decimal}")
        except (InvalidOperation, ValueError, TypeError) as e:
            print(f"❌ Movimiento #{movimiento.id}: Datos corruptos: {e}")
            movimientos_corruptos.append(movimiento)
    
    print(f"📊 Movimientos procesados: {movimientos_procesados}")
    print(f"📊 Movimientos corruptos: {len(movimientos_corruptos)}")
    
    return len(movimientos_corruptos)

def main():
    """
    Función principal de limpieza
    """
    print("🚀 INICIANDO LIMPIEZA DE DATOS CORRUPTOS")
    print("=" * 50)
    
    # Limpiar ventas
    ventas_corruptas, ventas_corregidas = limpiar_ventas_corruptas()
    
    # Verificar movimientos contables
    movimientos_corruptos = verificar_movimientos_contables()
    
    print(f"\n🎯 RESUMEN FINAL:")
    print(f"   • Ventas corruptas encontradas: {ventas_corruptas}")
    print(f"   • Ventas corregidas: {ventas_corregidas}")
    print(f"   • Movimientos corruptos: {movimientos_corruptos}")
    
    if ventas_corregidas > 0:
        print(f"\n✅ Se han corregido {ventas_corregidas} ventas. ")
        print(f"   Ahora deberías poder usar los filtros sin errores.")
    
    print(f"\n🔧 Para ejecutar este script:")
    print(f"   1. Guarda este código en un archivo: limpiar_datos.py")
    print(f"   2. Ejecuta: python manage.py shell < limpiar_datos.py")
    print(f"   3. O en el shell de Django: exec(open('limpiar_datos.py').read())")

if __name__ == "__main__":
    main()

# Para ejecutar directamente en el shell de Django:
# exec(open('limpiar_datos_corruptos.py').read())