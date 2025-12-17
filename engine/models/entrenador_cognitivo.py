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

# FACTOR DE OLVIDO (0.3 = Mantiene historia pero se adapta rápido)
ALPHA = 0.3 

def cargar_genoma():
    if os.path.exists(GENOMA_FILE):
        try:
            with open(GENOMA_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {"algo_ranking": {}, "last_processed": {}, "morphology": {}}

def analizar_adn_ganador(juego_filtro=None, sorteo_limite=None):
    """
    Entrena el cerebro creando LÓBULOS COMPLETOS:
    - Rankings de algoritmos separados por juego.
    - Morfología (Suma/Pares) separada por juego.
    """
    print(f"🧠 ENTRENADOR: Analizando patrones{' para ' + juego_filtro if juego_filtro else ''}...")
    
    if not os.path.exists(SIMULACIONES_FILE):
        return

    df = pd.read_csv(SIMULACIONES_FILE)
    df = df[df['estado'] == 'AUDITADO'].copy() # Solo aprendemos de éxitos/fracasos confirmados
    
    if juego_filtro:
        df = df[df['juego'] == juego_filtro]
    
    if sorteo_limite:
        df = df[df['sorteo_objetivo'] <= int(sorteo_limite)]

    if len(df) == 0:
        return

    # Cargar cerebro
    genoma = cargar_genoma()
    ranking_global = genoma.get("algo_ranking", {})
    
    # Migración de estructura antigua (si ranking es plano, lo reiniciamos)
    if ranking_global and not isinstance(next(iter(ranking_global.values()), {}), dict):
        print("   ⚠️ Detectada estructura antigua de ranking. Reiniciando para segmentación por lóbulos...")
        ranking_global = {}

    if "morphology" not in genoma: genoma["morphology"] = {}

    # Identificamos qué juegos hay en la data
    juegos_en_lote = df['juego'].unique()

    for juego_id in juegos_en_lote:
        # --- A. APRENDIZAJE DE ALGORITMOS (POR LÓBULO) ---
        df_juego = df[df['juego'] == juego_id]
        
        # Calculamos el score promedio de cada algoritmo EN ESTE JUEGO
        nuevo_ranking = df_juego.groupby('algoritmo')['score_afinidad'].mean().to_dict()
        
        # Recuperamos el ranking previo de este juego (o vacío)
        ranking_juego = ranking_global.get(juego_id, {})
        
        for algo, nuevo_score in nuevo_ranking.items():
            score_antiguo = ranking_juego.get(algo, nuevo_score)
            # EMA: (Antiguo * 0.7) + (Nuevo * 0.3)
            ranking_juego[algo] = round((score_antiguo * (1 - ALPHA)) + (nuevo_score * ALPHA), 2)
        
        ranking_global[juego_id] = ranking_juego

        # --- B. ANÁLISIS MORFOLÓGICO (POR LÓBULO) ---
        exitosas = df_juego[df_juego['score_afinidad'] >= 50].tail(50)
        
        memoria_morf = genoma["morphology"].get(juego_id, {
            "ideal_sum_range": [0, 999], 
            "ideal_even_count": -1
        })

        if len(exitosas) > 0:
            sumas = []
            pares = []
            for _, row in exitosas.iterrows():
                try:
                    nums = json.loads(row['numeros'])
                    sumas.append(sum(nums))
                    pares.append(len([n for n in nums if n % 2 == 0]))
                except: pass
            
            if sumas:
                memoria_morf["ideal_sum_range"] = [int(np.percentile(sumas, 25)), int(np.percentile(sumas, 75))]
            if pares:
                memoria_morf["ideal_even_count"] = int(round(np.mean(pares)))
            
            genoma["morphology"][juego_id] = memoria_morf
            print(f"   🧬 Lóbulo {juego_id} actualizado.")

    # --- GUARDAR ---
    ahora_chile = datetime.utcnow() - timedelta(hours=3)
    
    genoma["metadata"] = {
        "updated_at": ahora_chile.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "FULL_LOBOTOMY_V2", # Marca de la nueva arquitectura
        "casos_estudiados": len(df)
    }
    genoma["algo_ranking"] = ranking_global
    
    if "last_processed" not in genoma: genoma["last_processed"] = {}
    if juego_filtro and sorteo_limite:
        genoma["last_processed"][juego_filtro] = int(sorteo_limite)

    with open(GENOMA_FILE, 'w', encoding='utf-8') as f:
        json.dump(genoma, f, indent=2)
    
    print(f"   💾 Cerebro re-entrenado y guardado.")

if __name__ == "__main__":
    analizar_adn_ganador()