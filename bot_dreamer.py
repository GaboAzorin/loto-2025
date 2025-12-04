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
    simulacion_fecha = ultima_fecha
    sorteo_virtual_id = ultimo_id

    while True:
        # Avanzamos al día siguiente
        simulacion_fecha += timedelta(days=1)
        
        # Si este día es día de sorteo (Martes, Jueves o Domingo)
        if simulacion_fecha.weekday() in DIAS_SORTEO:
            sorteo_virtual_id += 1
            
            # Definimos el momento del cierre de ese sorteo virtual
            cierre_sorteo = simulacion_fecha.replace(hour=HORA_CIERRE_SORTEO, minute=0, second=0, microsecond=0)
            
            # CRITERIO DE VERDAD:
            if ahora < cierre_sorteo:
                return sorteo_virtual_id

def soñar():
    print("💤 --- INICIANDO BOT SOÑADOR DUAL v3.0 (Time-Aware) ---")
    
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
                proximo_sorteo = int(df_maestro['sorteo'].max()) + 1
        else:
            print("⚠️ No existe archivo maestro. Iniciando en 1.")
            proximo_sorteo = 1
    except Exception as e:
        print(f"⚠️ Error calculando fechas: {e}. Default: 0")
        proximo_sorteo = 0

    nuevas_filas = []
    ahora = datetime.now(TZ_CHILE)

    # 3.A. Generar Predicción BIOMÉTRICA (Física)
    try:
        pred_bio = forense.predict_numbers("LOTO", n=6)
        nuevas_filas.append({
            'id': int(ahora.timestamp()), # ID base
            'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
            'numeros': str(pred_bio),
            'sorteo_objetivo': proximo_sorteo,
            'estado': 'PENDIENTE',
            'aciertos': 0,
            'score_afinidad': 0.0,
            'hora_dia': ahora.hour,
            'algoritmo': 'forense_biometrico_v1'
        })
        print(f"🔮 Biométrico generado: {pred_bio}")
    except Exception as e:
        print(f"❌ Error Biométrico: {e}")

    # 3.B. Generar Predicción GAUSSIANA (Estadística)
    try:
        pred_gauss = forense.predict_gaussian(n=6)
        nuevas_filas.append({
            'id': int(ahora.timestamp()) + 1, # ID base + 1 para diferenciar
            'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
            'numeros': str(pred_gauss),
            'sorteo_objetivo': proximo_sorteo,
            'estado': 'PENDIENTE',
            'aciertos': 0,
            'score_afinidad': 0.0,
            'hora_dia': ahora.hour,
            'algoritmo': 'gaussiano_tactico_v1' # Nombre diferenciado
        })
        print(f"📐 Gaussiano generado: {pred_gauss}")
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