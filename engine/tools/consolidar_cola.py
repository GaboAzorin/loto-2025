import os
import json
import pandas as pd
import sys
import glob

# 1. Configuración de Rutas Relativas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(BASE_DIR, '..', '..', 'data'))
QUEUE_DIR = os.path.join(DATA_DIR, 'queue')
CSV_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")

# 2. Inyección de rutas para encontrar el módulo 'models'
# Esto permite que este script vea a 'consolidar_laboratorio.py'
MODELS_DIR = os.path.normpath(os.path.join(BASE_DIR, '..', 'models'))
if MODELS_DIR not in sys.path:
    sys.path.append(MODELS_DIR)

def consolidar():
    print("🧹 INICIANDO CONSOLIDACIÓN DE COLA Y LIMPIEZA...")
    
    # 3. Buscar archivos JSON en la cola
    pattern = os.path.join(QUEUE_DIR, "prediccion_*.json")
    ticket_files = glob.glob(pattern)
    
    if not ticket_files:
        print("   💤 La cola está vacía. Nada que procesar.")
        return

    print(f"   📄 Encontrados {len(ticket_files)} tickets nuevos.")

    # 4. Leer todos los tickets de la carpeta /queue
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

    # 5. Cargar CSV Maestro existente o crear uno nuevo
    if os.path.exists(CSV_FILE):
        try:
            df_maestro = pd.read_csv(CSV_FILE)
        except Exception:
            df_maestro = pd.DataFrame()
    else:
        df_maestro = pd.DataFrame()

    # 6. Concatenar y asegurar que no haya duplicados por ID
    df_nuevos = pd.DataFrame(nuevas_filas)
    
    cols_orden = ['id', 'fecha_generacion', 'juego', 'numeros', 'sorteo_objetivo', 
                  'estado', 'aciertos', 'score_afinidad', 'hora_dia', 'algoritmo']
    
    for c in cols_orden:
        if c not in df_nuevos.columns: df_nuevos[c] = 0
        if c not in df_maestro.columns and not df_maestro.empty: df_maestro[c] = 0

    df_final = pd.concat([df_maestro, df_nuevos], ignore_index=True)
    df_final.drop_duplicates(subset=['id'], keep='last', inplace=True)

    # 7. Guardar cambios en el CSV
    df_final.to_csv(CSV_FILE, index=False)
    print(f"   💾 CSV Actualizado. Total registros en base de datos: {len(df_final)}")

    # 8. Borrar archivos procesados de la cola
    for tf in procesados:
        try:
            os.remove(tf)
        except OSError as e:
            print(f"   ⚠️ No se pudo borrar {tf}: {e}")
            
    # 9. --- EL CIERRE DEL CÍRCULO ---
    # Llamamos a la lógica híbrida para que el dashboard sepa que 
    # ahora debe leer estos datos desde el CSV y no desde los archivos borrados.
    print("📢 Notificando al laboratorio para refrescar dashboard...")
    try:
        from consolidar_laboratorio import ejecutar_consolidacion_hibrida
        ejecutar_consolidacion_hibrida()
    except Exception as e:
        print(f"   ⚠️ No se pudo actualizar el dashboard automáticamente: {e}")
    # --------------------------------

    print("✨ CONSOLIDACIÓN Y LIMPIEZA FINALIZADA.")

if __name__ == "__main__":
    consolidar()