import pandas as pd
import os
import time
import json
import juez_implacable        # Importamos tus módulos existentes
import entrenador_cognitivo   # Importamos el entrenador modificado

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
GENOMA_FILE = os.path.join(DATA_DIR, "loto_genome.json")

# Definir qué archivos maestros leer
JUEGOS = {
    "LOTO3": "LOTO3_MAESTRO.csv",
    "RACHA": "RACHA_MAESTRO.csv",
    "LOTO":  "LOTO_HISTORIAL_MAESTRO.csv",
    "LOTO4": "LOTO4_MAESTRO.csv"
}

def obtener_ultimo_procesado(juego):
    if not os.path.exists(GENOMA_FILE): return 0
    try:
        with open(GENOMA_FILE, 'r') as f:
            data = json.load(f)
            return data.get("last_processed", {}).get(juego, 0)
    except: return 0

def reconstruir_linea_tiempo():
    print("⏳ INICIANDO RECONSTRUCCIÓN TEMPORAL SECUENCIAL...")
    
    for juego, archivo in JUEGOS.items():
        path = os.path.join(DATA_DIR, archivo)
        if not os.path.exists(path): continue
        
        # 1. Leer sorteos reales disponibles
        df_real = pd.read_csv(path)
        if 'sorteo' not in df_real.columns: continue
        
        # Ordenar por sorteo (antiguo a nuevo)
        df_real = df_real.sort_values('sorteo', ascending=True)
        todos_sorteos = df_real['sorteo'].unique()
        
        # 2. Ver dónde nos quedamos la última vez
        ultimo_id = obtener_ultimo_procesado(juego)
        
        # 3. Identificar sorteos "nuevos" (futuro no procesado)
        nuevos = [s for s in todos_sorteos if s > ultimo_id]
        
        if not nuevos:
            print(f"✅ {juego}: Todo al día (Último: {ultimo_id})")
            continue
            
        print(f"\n🌀 {juego}: Detectados {len(nuevos)} sorteos nuevos para digerir secuencialmente.")
        print(f"   Rango: {min(nuevos)} -> {max(nuevos)}")
        
        # 4. BUCLE DE VIAJE EN EL TIEMPO
        for sorteo_actual in nuevos:
            print(f"\n   >>> Procesando Sorteo {sorteo_actual}...")
            
            # A. FASE JUEZ: Auditar SOLO hasta este sorteo
            # (El juez por defecto audita todo lo que encuentra en el maestro, 
            #  así que funcionará bien porque el sorteo ya está en el CSV).
            #  Para ser más eficiente, podríamos modificar el juez para filtrar, 
            #  pero correrlo completo no daña la lógica, solo gasta CPU.
            juez_implacable.juzgar() 
            
            # B. FASE ENTRENADOR: Aprender de este hito
            # Aquí es clave pasarle el 'sorteo_limite' para que no vea el futuro si hubiera más datos
            entrenador_cognitivo.analizar_adn_ganador(juego_filtro=juego, sorteo_limite=sorteo_actual)
            
            # Pequeña pausa para asegurar escritura en disco
            time.sleep(0.5)
            
    print("\n✨ RECONSTRUCCIÓN FINALIZADA. El sistema está sincronizado.")

if __name__ == "__main__":
    reconstruir_linea_tiempo()