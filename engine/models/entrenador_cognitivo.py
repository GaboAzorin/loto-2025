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

# FACTOR DE OLVIDO (0.3 = Balance ideal entre historia y tendencia reciente)
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
    Entrena el cerebro separando la morfología por juego (Lóbulos Independientes).
    """
    print(f"🧠 ENTRENADOR: Analizando patrones{' para ' + juego_filtro if juego_filtro else ''}...")
    
    if not os.path.exists(SIMULACIONES_FILE):
        return

    df = pd.read_csv(SIMULACIONES_FILE)
    
    # Filtrar solo lo auditado
    df = df[df['estado'] == 'AUDITADO'].copy()
    
    if juego_filtro:
        df = df[df['juego'] == juego_filtro]
    
    if sorteo_limite:
        df = df[df['sorteo_objetivo'] <= int(sorteo_limite)]

    if len(df) == 0:
        return

    # Cargar cerebro actual
    genoma = cargar_genoma()
    ranking_actual = genoma.get("algo_ranking", {})
    
    # Asegurar que existe la estructura de morfología
    if "morphology" not in genoma: genoma["morphology"] = {}

    # --- 1. APRENDIZAJE DE ALGORITMOS (GLOBAL) ---
    # Mantenemos el ranking global por ahora, ya que el Consenso domina en todos.
    nuevo_ranking = df.groupby('algoritmo')['score_afinidad'].mean().to_dict()
    
    for algo, nuevo_score in nuevo_ranking.items():
        score_antiguo = ranking_actual.get(algo, nuevo_score)
        # EMA: Suavizado exponencial
        ranking_actual[algo] = round((score_antiguo * (1 - ALPHA)) + (nuevo_score * ALPHA), 2)

    # --- 2. ANÁLISIS MORFOLÓGICO POR LÓBULOS (JUEGO POR JUEGO) ---
    # Identificamos qué juegos están presentes en este lote de datos
    juegos_en_lote = df['juego'].unique()

    for juego_id in juegos_en_lote:
        # Filtramos las simulaciones EXITOSAS de ESTE juego específico
        # Criterio de éxito: Score > 50 (Alta afinidad)
        exitosas = df[(df['juego'] == juego_id) & (df['score_afinidad'] >= 50)].tail(50)
        
        # Recuperamos la memoria anterior de este juego (o creamos una nueva)
        memoria_juego = genoma["morphology"].get(juego_id, {
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
                    # Contamos pares
                    pares.append(len([n for n in nums if n % 2 == 0]))
                except: pass
            
            # Actualizamos la morfología SOLO para este juego
            if sumas:
                # Rango intercuartil (elimina extremos locos)
                memoria_juego["ideal_sum_range"] = [int(np.percentile(sumas, 25)), int(np.percentile(sumas, 75))]
            
            if pares:
                # Promedio redondeado
                memoria_juego["ideal_even_count"] = int(round(np.mean(pares)))
            
            # Guardamos en el lóbulo correspondiente
            genoma["morphology"][juego_id] = memoria_juego
            print(f"   🧬 Lóbulo {juego_id} actualizado: Suma {memoria_juego['ideal_sum_range']}, Pares {memoria_juego['ideal_even_count']}")

    # --- CALCULAR HORA ---
    # Definido dentro de la función para seguridad
    ahora_chile = datetime.utcnow() - timedelta(hours=3)

    # --- GUARDAR GENOMA ---
    genoma["metadata"] = {
        "updated_at": ahora_chile.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "INCREMENTAL_EMA_LOBOTOMIZED", # Marca de la nueva versión
        "casos_estudiados": len(df)
    }
    genoma["algo_ranking"] = ranking_actual
    
    # last_processed management
    if "last_processed" not in genoma: genoma["last_processed"] = {}
    if juego_filtro and sorteo_limite:
        genoma["last_processed"][juego_filtro] = int(sorteo_limite)

    with open(GENOMA_FILE, 'w', encoding='utf-8') as f:
        json.dump(genoma, f, indent=2)
    
    lider = max(ranking_actual, key=ranking_actual.get) if ranking_actual else "None"
    print(f"   💾 Cerebro guardado. Líder Global: {lider}")

if __name__ == "__main__":
    analizar_adn_ganador()