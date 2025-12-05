import pandas as pd
import os
import pytz
from datetime import datetime, timedelta
from analizador_forense import LotoForense

# --- CONFIGURACIÓN ---
FILE_SIMULACIONES = "LOTO_SIMULACIONES.csv"
FILE_MAESTRO = "LOTO_HISTORIAL_MAESTRO.csv"
TZ_CHILE = pytz.timezone('America/Santiago')

# Días de sorteo: Martes (1), Jueves (3), Domingo (6)
DIAS_SORTEO = [1, 3, 6] 
HORA_CIERRE_SORTEO = 21 # Cierre a las 21:00

def calcular_sorteo_real(df_maestro):
    """
    Calcula el ID del próximo sorteo REAL.
    Versión Blindada v3.1: Usa Pandas para parsear fechas y maneja mejor los saltos.
    """
    ahora = datetime.now(TZ_CHILE)
    
    try:
        # 1. Obtener datos del último sorteo con PANDAS (Más robusto que strptime)
        ultimo_row = df_maestro.iloc[-1]
        ultimo_id = int(ultimo_row['sorteo'])
        
        # Pandas detecta automáticamente si es YYYY-MM-DD o DD-MM-YYYY
        fecha_dt = pd.to_datetime(ultimo_row['fecha'])
        
        # Convertir a datetime de Python y asignar zona horaria si no tiene
        ultima_fecha = fecha_dt.to_pydatetime()
        if ultima_fecha.tzinfo is None:
            ultima_fecha = TZ_CHILE.localize(ultima_fecha)
        else:
            ultima_fecha = ultima_fecha.astimezone(TZ_CHILE)
            
    except Exception as e:
        print(f"⚠️ Error crítico leyendo fechas del maestro: {e}")
        # FALLBACK MEJORADO: Si falla la lectura, asumimos basándonos solo en la hora actual
        # Si son más de las 21:00, asumimos que el último del CSV ya pasó hoy
        # (Esto es una medida desesperada, pero mejor que max+1 ciego)
        max_id = int(df_maestro['sorteo'].max())
        if ahora.hour >= 21 and ahora.weekday() in DIAS_SORTEO:
             return max_id + 2 # Saltamos el de hoy
        return max_id + 1

    # 2. Algoritmo de Viaje en el Tiempo
    simulacion_fecha = ultima_fecha
    sorteo_virtual_id = ultimo_id
    
    # Límite de seguridad para evitar bucles infinitos (ej: si la fecha del CSV está en el futuro)
    dias_simulados = 0
    while dias_simulados < 30: 
        dias_simulados += 1
        
        # Avanzamos al día siguiente (o evaluamos el mismo día si la hora lo amerita, 
        # pero para simplificar, la lógica de 'proximo' siempre busca hacia adelante)
        simulacion_fecha += timedelta(days=1)
        
        # Ajustamos la fecha simulada a las 21:00 de ese día
        cierre_sorteo = simulacion_fecha.replace(hour=HORA_CIERRE_SORTEO, minute=0, second=0, microsecond=0)
        
        if simulacion_fecha.weekday() in DIAS_SORTEO:
            sorteo_virtual_id += 1
            
            # CRITERIO DE VERDAD:
            # Si "ahora" es ANTES del cierre de este sorteo virtual, 
            # significa que este es el sorteo vigente que estamos esperando.
            if ahora < cierre_sorteo:
                return sorteo_virtual_id
    
    # Si salimos del loop, algo raro pasó, devolvemos fallback seguro
    return ultimo_id + 1

def soñar():
    print("💤 --- INICIANDO BOT SOÑADOR DUAL v3.1 (Robust Date) ---")
    
    # 1. Instanciar Forense
    try:
        forense = LotoForense(FILE_MAESTRO)
    except Exception as e:
        print(f"❌ Error fatal iniciando forense: {e}")
        return

    # 2. Calcular el Sorteo Objetivo REAL
    try:
        if os.path.exists(FILE_MAESTRO):
            df_maestro = pd.read_csv(FILE_MAESTRO)
            proximo_sorteo = calcular_sorteo_real(df_maestro)
        else:
            print("⚠️ No existe archivo maestro. Iniciando en 1.")
            proximo_sorteo = 1
    except Exception as e:
        print(f"❌ Error general en cálculo de fechas: {e}")
        proximo_sorteo = 0 # Esto alertará en los logs

    print(f"🎯 Sorteo Objetivo Calculado: {proximo_sorteo}")

    nuevas_filas = []
    ahora = datetime.now(TZ_CHILE)

    # 3.A. Generar Predicción BIOMÉTRICA (Física)
    try:
        pred_bio = forense.predict_numbers("LOTO", n=6)
        nuevas_filas.append({
            'id': int(ahora.timestamp()),
            'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
            'numeros': str(pred_bio),
            'sorteo_objetivo': proximo_sorteo,
            'estado': 'PENDIENTE',
            'aciertos': 0,
            'score_afinidad': 0.0,
            'hora_dia': ahora.hour,
            'algoritmo': 'forense_biometrico_v1'
        })
    except Exception as e:
        print(f"❌ Error Biométrico: {e}")

    # 3.B. Generar Predicción GAUSSIANA (Estadística)
    try:
        pred_gauss = forense.predict_gaussian(n=6)
        nuevas_filas.append({
            'id': int(ahora.timestamp()) + 1,
            'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
            'numeros': str(pred_gauss),
            'sorteo_objetivo': proximo_sorteo,
            'estado': 'PENDIENTE',
            'aciertos': 0,
            'score_afinidad': 0.0,
            'hora_dia': ahora.hour,
            'algoritmo': 'gaussiano_tactico_v1'
        })
    except Exception as e:
        print(f"❌ Error Gaussiano: {e}")
    
    # 4. Guardar Todo
    if nuevas_filas:
        try:
            if os.path.exists(FILE_SIMULACIONES):
                df_sim = pd.read_csv(FILE_SIMULACIONES)
                df_new = pd.DataFrame(nuevas_filas)
                df_sim = pd.concat([df_sim, df_new], ignore_index=True)
            else:
                df_sim = pd.DataFrame(nuevas_filas)
                
            df_sim.to_csv(FILE_SIMULACIONES, index=False)
            print(f"✨ ÉXITO: 2 predicciones guardadas para Sorteo {proximo_sorteo}")
            
        except Exception as e:
            print(f"❌ Error guardando CSV: {e}")

if __name__ == "__main__":
    soñar()
