import pandas as pd
import os
import pytz
from datetime import datetime
from analizador_forense import LotoForense

# --- CONFIGURACIÓN ---
FILE_SIMULACIONES = "LOTO_SIMULACIONES.csv"
FILE_MAESTRO = "LOTO_HISTORIAL_MAESTRO.csv"
TZ_CHILE = pytz.timezone('America/Santiago')

def soñar():
    print("💤 --- INICIANDO BOT SOÑADOR v1.0 ---")
    
    # 1. Instanciar Forense (Cargará biometría JSON automáticamente si existe)
    try:
        forense = LotoForense(FILE_MAESTRO)
    except Exception as e:
        print(f"❌ Error fatal iniciando forense: {e}")
        return

    # 2. Determinar el sorteo objetivo (Next Draw)
    try:
        if os.path.exists(FILE_MAESTRO):
            df_maestro = pd.read_csv(FILE_MAESTRO)
            ultimo_sorteo = df_maestro['sorteo'].max()
            proximo_sorteo = int(ultimo_sorteo) + 1
        else:
            print("⚠️ No existe archivo maestro. Asumiendo sorteo inicial 1.")
            proximo_sorteo = 1
    except Exception as e:
        print(f"⚠️ Error leyendo maestro: {e}. Default: 0")
        proximo_sorteo = 0

    # 3. Generar Predicción Biométrica
    # Usamos la lógica 'predict_numbers' que acabamos de agregar a la clase
    try:
        numeros_predichos = forense.predict_numbers("LOTO", n=6)
        numeros_fmt = str(numeros_predichos) # Formato lista "[1, 2, 3...]"
    except Exception as e:
        print(f"❌ Error generando predicción: {e}")
        return
    
    # 4. Preparar la data para guardar
    ahora = datetime.now(TZ_CHILE)
    nueva_fila = {
        'id': int(ahora.timestamp()),
        'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
        'numeros': numeros_fmt,
        'sorteo_objetivo': proximo_sorteo,
        'estado': 'PENDIENTE',
        'aciertos': 0,
        'score_afinidad': 0.0,
        'hora_dia': ahora.hour, # Dato clave para tu análisis de "mejor hora"
        'algoritmo': 'forense_biometrico_v1'
    }
    
    # 5. Guardar/Append en LOTO_SIMULACIONES.csv
    try:
        if os.path.exists(FILE_SIMULACIONES):
            df_sim = pd.read_csv(FILE_SIMULACIONES)
            df_new = pd.DataFrame([nueva_fila])
            df_sim = pd.concat([df_sim, df_new], ignore_index=True)
        else:
            df_sim = pd.DataFrame([nueva_fila])
            
        df_sim.to_csv(FILE_SIMULACIONES, index=False)
        print(f"✨ ÉXITO: Predicción guardada para Sorteo {proximo_sorteo}")
        print(f"   🔢 Números: {numeros_fmt}")
        print(f"   🕒 Hora: {ahora.strftime('%H:%M')}")
        
    except Exception as e:
        print(f"❌ Error guardando CSV: {e}")

if __name__ == "__main__":
    soñar()