import pandas as pd
import json
import os
import numpy as np
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
SIMULACIONES_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
GENOMA_FILE = os.path.join(DATA_DIR, "loto_genome.json")

# FACTOR DE OLVIDO (0.3 = El presente vale un 30%, la historia un 70%)
ALPHA = 0.05 

# Primos para V4
PRIMOS_SET = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41}

def cargar_genoma():
    if os.path.exists(GENOMA_FILE):
        try:
            with open(GENOMA_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {"algo_ranking": {}, "metadata": {}, "morphology": {}}

def analizar_adn_ganador():
    """
    Entrena el cerebro usando APRENDIZAJE INCREMENTAL.
    Solo mira las filas nuevas que ya han sido auditadas por el Juez.
    """
    print(f"🧠 ENTRENADOR: Iniciando sesión de aprendizaje incremental...")
    
    if not os.path.exists(SIMULACIONES_FILE):
        print("   ⚠️ No hay archivo de simulaciones.")
        return

    # 1. Cargar Cerebro y estado anterior
    genoma = cargar_genoma()
    ranking_global = genoma.get("algo_ranking", {})
    metadata = genoma.get("metadata", {})
    
    # BLINDAJE 1: Asegurar que last_trained_id sea int
    try:
        last_trained_id = int(metadata.get("last_trained_id", -1))
    except:
        last_trained_id = -1
        
    print(f"   📅 Último ID aprendido: {last_trained_id}")

    # 2. Cargar CSV y Filtrar Novedades
    try:
        df = pd.read_csv(SIMULACIONES_FILE)
    except Exception as e:
        print(f"   ❌ Error leyendo CSV: {e}")
        return

    if df.empty:
        print("   💤 Archivo CSV vacío.")
        return

    # BLINDAJE 2: Forzar que la columna 'id' sea numérica
    # Esto arregla el error '>' not supported between instances of 'str' and 'int'
    df['id'] = pd.to_numeric(df['id'], errors='coerce')
    df = df.dropna(subset=['id']) # Eliminamos filas con IDs corruptos

    # FILTRO CRÍTICO: Solo AUDITADO y solo IDs nuevos
    df_nuevo = df[
        (df['estado'] == 'AUDITADO') & 
        (df['id'] > last_trained_id)
    ].copy()
    
    cantidad_nuevas = len(df_nuevo)
    if cantidad_nuevas == 0:
        print("   💤 No hay lecciones nuevas. El cerebro está al día.")
        return

    print(f"   🤓 Procesando {cantidad_nuevas} nuevas lecciones...")

    # Identificamos qué juegos hay en el lote nuevo
    juegos_en_lote = df_nuevo['juego'].unique()

    # 3. Ciclo de Aprendizaje
    for juego_id in juegos_en_lote:
        df_juego = df_nuevo[df_nuevo['juego'] == juego_id]
        
        # --- A. APRENDIZAJE DE RANKING (EMA) ---
        performance_lote = df_juego.groupby('algoritmo')['score_afinidad'].mean().to_dict()
        ranking_juego = ranking_global.get(juego_id, {})
        
        for algo, score_lote in performance_lote.items():
            score_antiguo = ranking_juego.get(algo, score_lote)
            nuevo_valor = (score_antiguo * (1 - ALPHA)) + (score_lote * ALPHA)
            ranking_juego[algo] = round(nuevo_valor, 2)
        
        ranking_global[juego_id] = ranking_juego
        print(f"   📈 Ranking actualizado para {juego_id}")

        # --- B. APRENDIZAJE MORFOLÓGICO AVANZADO (V4) ---
        memoria_morf = genoma["morphology"].get(juego_id, {
            "ideal_sum_range": [0, 999],
            "ideal_even_count": -1,
            "ideal_consecutivos": -1,
            "ideal_bajos_altos": -1,
            "ideal_terminaciones": -1,
            "ideal_primos": -1,
            "ideal_multiples_3": -1,
            "ideal_avg_delta": -1
        })

        exitosas = df_juego[df_juego['score_afinidad'] >= 50]
        
        if len(exitosas) > 0:
            sumas = []
            pares = []
            consecutivos = []
            bajos = []
            terminaciones = []
            primos = []
            multiples_3 = []
            deltas = []
            
            limite_bajo = 4 if juego_id == "LOTO3" else (10 if juego_id == "RACHA" else 21)

            for _, row in exitosas.iterrows():
                try:
                    nums = sorted(json.loads(row['numeros']))
                    if not nums: continue
                    
                    # Cálculos
                    sumas.append(sum(nums))
                    pares.append(len([n for n in nums if n % 2 == 0]))
                    consecutivos.append(sum(1 for i in range(len(nums)-1) if nums[i+1] == nums[i] + 1))
                    bajos.append(len([n for n in nums if n <= limite_bajo]))
                    terminaciones.append(len(set([n % 10 for n in nums])))
                    primos.append(len([n for n in nums if n in PRIMOS_SET]))
                    multiples_3.append(len([n for n in nums if n > 0 and n % 3 == 0]))
                    
                    if len(nums) > 1:
                        diffs = [nums[i+1] - nums[i] for i in range(len(nums)-1)]
                        deltas.append(sum(diffs) / len(diffs))

                except Exception: pass
            
            # Helper de actualización
            def actualizar_promedio(clave, nuevos_datos):
                if not nuevos_datos: return
                new_avg = np.mean(nuevos_datos)
                old_val = memoria_morf.get(clave, -1)
                memoria_morf[clave] = float(round(new_avg, 2)) if old_val == -1 else float(round((old_val * 0.8) + (new_avg * 0.2), 2))

            if sumas:
                p25, p75 = np.percentile(sumas, 25), np.percentile(sumas, 75)
                old_range = memoria_morf.get("ideal_sum_range", [0, 999])
                new_min = int((old_range[0] * 0.8) + (p25 * 0.2))
                new_max = int((old_range[1] * 0.8) + (p75 * 0.2))
                memoria_morf["ideal_sum_range"] = [new_min, new_max]

            actualizar_promedio("ideal_even_count", pares)
            actualizar_promedio("ideal_consecutivos", consecutivos)
            actualizar_promedio("ideal_bajos_altos", bajos)
            actualizar_promedio("ideal_terminaciones", terminaciones)
            actualizar_promedio("ideal_primos", primos)
            actualizar_promedio("ideal_multiples_3", multiples_3)
            actualizar_promedio("ideal_avg_delta", deltas)
            
            genoma["morphology"][juego_id] = memoria_morf
            print(f"   🧬 Morfología V4 actualizada para {juego_id}")

    # 4. Guardar Cerebro Actualizado
    max_id_procesado = int(df_nuevo['id'].max())
    
    genoma["metadata"]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    genoma["metadata"]["last_trained_id"] = max_id_procesado
    genoma["metadata"]["total_casos_estudiados"] = metadata.get("total_casos_estudiados", 0) + cantidad_nuevas
    genoma["algo_ranking"] = ranking_global
    
    with open(GENOMA_FILE, 'w', encoding='utf-8') as f:
        json.dump(genoma, f, indent=2)
    
    print(f"   💾 Cerebro guardado. Checkpoint ID: {max_id_procesado}")

if __name__ == "__main__":
    analizar_adn_ganador()