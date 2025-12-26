import os
import json
import pandas as pd
import sys
import glob

# Configuración de Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
QUEUE_DIR = os.path.join(DATA_DIR, 'queue')
CSV_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")

def consolidar():
    print("🧹 INICIANDO CONSOLIDACIÓN DE COLA...")
    
    # 1. Buscar archivos JSON en la cola
    pattern = os.path.join(QUEUE_DIR, "prediccion_*.json")
    ticket_files = glob.glob(pattern)
    
    if not ticket_files:
        print("   💤 La cola está vacía. Nada que hacer.")
        return

    print(f"   📄 Encontrados {len(ticket_files)} tickets pendientes.")

    # 2. Leer todos los tickets
    nuevas_filas = []
    procesados = []
    
    for tf in ticket_files:
        try:
            with open(tf, 'r', encoding='utf-8') as f:
                data = json.load(f)
                nuevas_filas.append(data)
                procesados.append(tf)
        except Exception as e:
            print(f"   ❌ Error leyendo {tf}: {e}")

    if not nuevas_filas:
        return

    # 3. Cargar CSV Maestro existente
    if os.path.exists(CSV_FILE):
        try:
            df_maestro = pd.read_csv(CSV_FILE)
        except Exception:
            df_maestro = pd.DataFrame()
    else:
        df_maestro = pd.DataFrame()

    # 4. Concatenar y Deduplicar
    df_nuevos = pd.DataFrame(nuevas_filas)
    
    # Asegurar columnas consistentes
    cols_orden = ['id', 'fecha_generacion', 'juego', 'numeros', 'sorteo_objetivo', 
                  'estado', 'aciertos', 'score_afinidad', 'hora_dia', 'algoritmo']
    
    # Rellenar columnas faltantes en el maestro o en los nuevos
    for c in cols_orden:
        if c not in df_nuevos.columns: df_nuevos[c] = 0
        if c not in df_maestro.columns and not df_maestro.empty: df_maestro[c] = 0

    # Concatenar
    df_final = pd.concat([df_maestro, df_nuevos], ignore_index=True)
    
    # Eliminar duplicados exactos de ID por si acaso
    df_final.drop_duplicates(subset=['id'], keep='last', inplace=True)

    # 5. Guardar CSV Maestro
    df_final.to_csv(CSV_FILE, index=False)
    print(f"   💾 CSV Actualizado. Total filas: {len(df_final)}")

    # 6. Borrar tickets procesados (CRÍTICO)
    for tf in procesados:
        try:
            os.remove(tf)
        except OSError as e:
            print(f"   ⚠️ No se pudo borrar {tf}: {e}")
            
    print("✨ CONSOLIDACIÓN FINALIZADA.")

if __name__ == "__main__":
    consolidar()