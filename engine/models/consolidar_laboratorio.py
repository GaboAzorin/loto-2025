import os
import json
import glob

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
QUEUE_DIR = os.path.join(DATA_DIR, 'queue')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'dashboard_data.json')

def consolidar():
    predicciones = []
    # Buscamos todos los JSONs generados por el bot_dreamer
    archivos = glob.glob(os.path.join(QUEUE_DIR, "prediccion_*.json"))
    
    for archivo in archivos:
        with open(archivo, 'r', encoding='utf-8') as f:
            predicciones.append(json.load(f))
            
    # Guardamos todo en un solo punto de entrada para el HTML
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(predicciones, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Laboratorio actualizado con {len(predicciones)} predicciones reales.")

if __name__ == "__main__":
    consolidar()