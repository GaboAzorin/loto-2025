import os
import json
import glob
import pandas as pd

# Configuración de rutas robusta
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(BASE_DIR, '..', '..', 'data'))
QUEUE_DIR = os.path.join(DATA_DIR, 'queue')
CSV_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
# El dashboard suele estar en la raíz o nivel superior para el HTML
OUTPUT_FILE = os.path.normpath(os.path.join(BASE_DIR, '..', '..', 'dashboard_data.json'))

def ejecutar_consolidacion_hibrida():
    print("🔄 Actualizando Dashboard (Híbrido CSV + Queue)...")
    todas_las_predicciones = []
    ids_vistos = set()

    # 1. Cargar Pendientes desde el CSV Maestro
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if not df.empty:
                # Filtrar solo pendientes
                pendientes = df[df['estado'] == 'PENDIENTE'].to_dict(orient='records')
                for p in pendientes:
                    todas_las_predicciones.append(p)
                    ids_vistos.add(str(p['id']))
        except Exception as e:
            print(f"   ⚠️ Error en CSV: {e}")

    # 2. Cargar lo que esté en la Queue (aún no procesado por consolidar_cola.py)
    archivos_json = glob.glob(os.path.join(QUEUE_DIR, "prediccion_*.json"))
    for archi in archivos_json:
        try:
            with open(archi, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if str(data.get('id')) not in ids_vistos:
                    todas_las_predicciones.append(data)
                    ids_vistos.add(str(data.get('id')))
        except Exception as e:
            print(f"   ⚠️ Error en JSON {archi}: {e}")

    # 3. Guardar el resultado final
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(todas_las_predicciones, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Dashboard listo con {len(todas_las_predicciones)} registros.")

if __name__ == "__main__":
    ejecutar_consolidacion_hibrida()