import pandas as pd
import json
import os
import numpy as np
import ast
import sys
from datetime import datetime, timedelta

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
SIMULACIONES_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
GENOMA_FILE = os.path.join(DATA_DIR, "loto_genome.json")

# --- AJUSTE DE ESTABILIDAD (AUDITORÍA v4) ---
# Bajamos ALPHA de 0.3 a 0.05 para exigir consistencia de largo plazo y evitar "golpes de suerte".
ALPHA = 0.05 

# Set de Primos para validación morfológica (V4 expandida)
PRIMOS_SET = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41}

def cargar_genoma():
    """Carga el estado actual de la inteligencia colectiva con manejo de excepciones."""
    if os.path.exists(GENOMA_FILE):
        try:
            with open(GENOMA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Validar estructura mínima
                if "algo_ranking" not in data: data["algo_ranking"] = {}
                if "morphology" not in data: data["morphology"] = {}
                if "metadata" not in data: data["metadata"] = {}
                return data
        except Exception as e:
            print(f"   ⚠️ Error leyendo genoma: {e}. Creando uno nuevo...")
    
    return {"algo_ranking": {}, "metadata": {}, "morphology": {}}

def analizar_adn_ganador():
    """
    Sincroniza el ranking de algoritmos y la morfología ideal basándose 
    en los últimos sorteos auditados por el Juez (Aprendizaje Incremental).
    """
    print("\n" + "="*60)
    print("🧠 ENTRENADOR COGNITIVO v12.4: INICIANDO CICLO DE APRENDIZAJE")
    print("="*60)
    
    if not os.path.exists(SIMULACIONES_FILE):
        print("   ❌ CRÍTICO: No existe LOTO_SIMULACIONES.csv. El cerebro no tiene qué estudiar.")
        return

    # 1. Carga de Datos
    try:
        df = pd.read_csv(SIMULACIONES_FILE)
    except Exception as e:
        print(f"   ❌ Error al abrir simulaciones: {e}")
        return

    genoma = cargar_genoma()
    
    # Determinamos desde dónde retomar el entrenamiento (Checkpoint)
    last_trained_id = genoma.get("metadata", {}).get("last_trained_id", 0)
    
    # Filtramos filas auditadas que el cerebro aún no ha procesado
    df_nuevo = df[(df['estado'] == 'AUDITADO') & (df['id'] > last_trained_id)].copy()
    
    if df_nuevo.empty:
        print(f"   💤 Checkpoint: {last_trained_id}. Sin casos nuevos para analizar.")
        return

    print(f"   📊 Analizando {len(df_nuevo)} nuevos hitos de rendimiento...")

    ranking_global = genoma["algo_ranking"]
    morph_global = genoma["morphology"]
    juegos_en_lote = df_nuevo['juego'].unique()

    # 2. PROCESAMIENTO POR JUEGO
    for juego_id in juegos_en_lote:
        print(f"\n   📍 Universo: {juego_id}")
        df_juego = df_nuevo[df_nuevo['juego'] == juego_id]
        
        # --- [A.1] RANKING GLOBAL (EMA) ---
        performance_lote = df_juego.groupby('algoritmo')['score_afinidad'].mean().to_dict()
        ranking_juego = ranking_global.get(juego_id, {})
        
        for algo, score_lote in performance_lote.items():
            score_antiguo = ranking_juego.get(algo, 1.0) 
            nuevo_valor = (score_antiguo * (1 - ALPHA)) + (score_lote * ALPHA)
            ranking_juego[algo] = round(float(nuevo_valor), 2)
        ranking_global[juego_id] = ranking_juego

        # --- [A.2] RANKING HORARIO (NIVEL 2: Sensibilidad Horaria) ---
        # Inicializamos la estructura si no existe en el genoma
        if "algo_ranking_hourly" not in genoma: genoma["algo_ranking_hourly"] = {}
        
        # Agrupamos los nuevos datos por hora y algoritmo
        perf_horaria = df_juego.groupby(['hora_dia', 'algoritmo'])['score_afinidad'].mean().unstack(fill_value=0).to_dict('index')
        
        rank_horario_juego = genoma["algo_ranking_hourly"].get(juego_id, {})

        for h, algos_en_hora in perf_horaria.items():
            h_key = str(h)
            ranking_h = rank_horario_juego.get(h_key, {})
            
            for algo, score_lote in algos_en_hora.items():
                if score_lote == 0: continue
                val_old = ranking_h.get(algo, 1.0)
                # Aplicamos el mismo ALPHA (0.05) para estabilidad de largo plazo
                val_new = (val_old * (1 - ALPHA)) + (score_lote * ALPHA)
                ranking_h[algo] = round(float(val_new), 2)
                
                # Reporte de "Especialización Horaria"
                if abs(val_new - val_old) > 0.2:
                    print(f"      🕒 Especialidad {h_key}h | {algo}: {ranking_h[algo]}")
            
            rank_horario_juego[h_key] = ranking_h
        
        genoma["algo_ranking_hourly"][juego_id] = rank_horario_juego
        
        # --- [B] ESTUDIO MORFOLÓGICO (ADN GANADOR) ---
        # Solo aprendemos morfología de los casos exitosos (aciertos >= 50%)
        # Note: Lógica dinámica de umbral de éxito
        df_exitos = df_juego[df_juego['aciertos'] >= 2] # Mínimo 2 para Loto/Racha
        if juego_id == "LOTO3": df_exitos = df_juego[df_juego['aciertos'] >= 1]

        if not df_exitos.empty:
            memoria_morf = morph_global.get(juego_id, {})
            
            def suavizar_metrica(clave, lista_valores, factor_novedad=0.1):
                if not lista_valores: return
                avg_lote = np.mean(lista_valores)
                val_old = memoria_morf.get(clave, -1)
                if val_old == -1:
                    memoria_morf[clave] = float(round(avg_lote, 2))
                else:
                    memoria_morf[clave] = float(round((val_old * (1 - factor_novedad)) + (avg_lote * factor_novedad), 2))

            # Contenedores de métricas
            pares, cons, bajos, terms, primos, mult3, deltas, sumas = [], [], [], [], [], [], [], []
            
            for _, row in df_exitos.iterrows():
                try:
                    nums = sorted(ast.literal_eval(row['numeros']))
                    sumas.append(sum(nums))
                    pares.append(len([n for n in nums if n % 2 == 0]))
                    cons.append(sum(1 for i in range(len(nums)-1) if nums[i+1] == nums[i] + 1))
                    
                    limit = 4 if juego_id == "LOTO3" else (10 if juego_id == "RACHA" else 21)
                    bajos.append(len([n for n in nums if n <= limit]))
                    terms.append(len(set([n % 10 for n in nums])))
                    primos.append(len([n for n in nums if n in PRIMOS_SET]))
                    mult3.append(len([n for n in nums if n % 3 == 0]))
                    if len(nums) > 1: deltas.append(float(np.mean(np.diff(nums))))
                except: continue

            # Actualización del Genoma
            if sumas:
                # Rango de suma ideal (Percentiles 25-75 corregidos)
                p25, p75 = np.percentile(sumas, [25, 75])
                old_range = memoria_morf.get("ideal_sum_range", [20, 200])
                memoria_morf["ideal_sum_range"] = [
                    int((old_range[0] * 0.9) + (p25 * 0.1)),
                    int((old_range[1] * 0.9) + (p75 * 0.1))
                ]

            suavizar_metrica("ideal_even_count", pares)
            suavizar_metrica("ideal_consecutivos", cons)
            suavizar_metrica("ideal_bajos_altos", bajos)
            suavizar_metrica("ideal_terminaciones", terms)
            suavizar_metrica("ideal_primos", primos)
            suavizar_metrica("ideal_multiples_3", mult3)
            suavizar_metrica("ideal_avg_delta", deltas)
            
            morph_global[juego_id] = memoria_morf
            print(f"      🧬 ADN Sincronizado para {juego_id}.")

    # 3. GUARDADO Y METADATA
    max_id = int(df_nuevo['id'].max())
    genoma["metadata"]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    genoma["metadata"]["last_trained_id"] = max_id
    genoma["metadata"]["total_estudiados"] = genoma["metadata"].get("total_estudiados", 0) + len(df_nuevo)

    with open(GENOMA_FILE, 'w', encoding='utf-8') as f:
        json.dump(genoma, f, indent=2, ensure_ascii=False)
    
    print("\n✅ CEREBRO ACTUALIZADO (Checkpoint #" + str(max_id) + ")")
    print("="*60 + "\n")

    # --- NIVEL 4: Actualización del Meta-Learner ---
    try:
        from meta_learner import MetaLearner
        ml = MetaLearner()
        ml.entrenar() 
    except Exception as e:
        print(f"   ⚠️ No se pudo actualizar el Meta-Learner: {e}")

if __name__ == "__main__":
    analizar_adn_ganador()