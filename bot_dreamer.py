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
HORA_CIERRE_SORTEO = 21 # Asumimos que a las 21:00 se cierra la ventana de predicción para ese día

def calcular_sorteo_real(df_maestro):
    """
    Calcula el ID del próximo sorteo REAL basándose en la fecha actual 
    y la última fecha registrada en la base de datos.
    Salva el problema de que la DB esté desactualizada.
    """
    ahora = datetime.now(TZ_CHILE)
    
    # 1. Obtener datos del último sorteo conocido
    try:
        ultimo_sorteo_row = df_maestro.iloc[-1]
        ultimo_id = int(ultimo_sorteo_row['sorteo'])
        fecha_str = ultimo_sorteo_row['fecha'] # Esperamos formato YYYY-MM-DD
        ultima_fecha = datetime.strptime(fecha_str, '%Y-%m-%d').replace(tzinfo=TZ_CHILE)
    except Exception as e:
        print(f"⚠️ Error leyendo fechas del maestro ({e}). Usando fallback simple.")
        return 0

    # 2. Viajar en el tiempo desde el último sorteo hasta hoy
    # Simula el calendario de sorteos para ver cuántos nos hemos saltado
    simulacion_fecha = ultima_fecha
    sorteo_virtual_id = ultimo_id

    # Avanzamos día por día desde la última fecha conocida hasta alcanzar el futuro
    while True:
        # Avanzamos al día siguiente
        simulacion_fecha += timedelta(days=1)
        
        # Si este día es día de sorteo (Martes, Jueves o Domingo)
        if simulacion_fecha.weekday() in DIAS_SORTEO:
            sorteo_virtual_id += 1
            
            # Definimos el momento del cierre de ese sorteo virtual
            cierre_sorteo = simulacion_fecha.replace(hour=HORA_CIERRE_SORTEO, minute=0, second=0, microsecond=0)
            
            # CRITERIO DE VERDAD:
            # Si "ahora" es ANTES del cierre de este sorteo, entonces ESTE es nuestro objetivo.
            if ahora < cierre_sorteo:
                return sorteo_virtual_id
            
            # Si "ahora" ya pasó el cierre, seguimos en el bucle buscando el siguiente.

def soñar():
    print("💤 --- INICIANDO BOT SOÑADOR v2.0 (Time-Aware) ---")
    
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
            
            if proximo_sorteo == 0:
                # Fallback por si falla la lectura de fechas
                proximo_sorteo = int(df_maestro['sorteo'].max()) + 1
        else:
            print("⚠️ No existe archivo maestro. Iniciando en 1.")
            proximo_sorteo = 1
    except Exception as e:
        print(f"⚠️ Error calculando fechas: {e}. Default: 0")
        proximo_sorteo = 0

    # 3. Generar Predicción Biométrica
    try:
        numeros_predichos = forense.predict_numbers("LOTO", n=6)
        numeros_fmt = str(numeros_predichos)
    except Exception as e:
        print(f"❌ Error generando predicción: {e}")
        return
    
    # 4. Preparar la data
    ahora = datetime.now(TZ_CHILE)
    nueva_fila = {
        'id': int(ahora.timestamp()),
        'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
        'numeros': numeros_fmt,
        'sorteo_objetivo': proximo_sorteo,
        'estado': 'PENDIENTE',
        'aciertos': 0,
        'score_afinidad': 0.0,
        'hora_dia': ahora.hour,
        'algoritmo': 'forense_biometrico_v1'
    }
    
    # 5. Guardar
    try:
        if os.path.exists(FILE_SIMULACIONES):
            df_sim = pd.read_csv(FILE_SIMULACIONES)
            # Asegurar que no escribimos headers de nuevo
            df_new = pd.DataFrame([nueva_fila])
            df_sim = pd.concat([df_sim, df_new], ignore_index=True)
        else:
            df_sim = pd.DataFrame([nueva_fila])
            
        df_sim.to_csv(FILE_SIMULACIONES, index=False)
        print(f"✨ ÉXITO: Predicción guardada para Sorteo {proximo_sorteo}")
        print(f"   📅 Fecha Generación: {nueva_fila['fecha_generacion']}")
        print(f"   🔢 Números: {numeros_fmt}")
        
    except Exception as e:
        print(f"❌ Error guardando CSV: {e}")

if __name__ == "__main__":
    soñar()