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
hora_chile = datetime.utcnow() - timedelta(hours=3)

# FACTOR DE OLVIDO (0.1 = Memoria larga, 0.5 = Balanceado, 0.9 = Solo importa lo reciente)
ALPHA = 0.3 

def cargar_genoma():
    if os.path.exists(GENOMA_FILE):
        with open(GENOMA_FILE, 'r') as f:
            return json.load(f)
    return {"algo_ranking": {}, "last_processed": {}}

def analizar_adn_ganador(juego_filtro=None, sorteo_limite=None):
    """
    juego_filtro: (Opcional) Si queremos entrenar solo un juego específico.
    sorteo_limite: (Opcional) Entrenar SOLO hasta este sorteo (para simulación temporal).
    """
    print(f"🧠 ENTRENADOR: Analizando patrones{' para ' + juego_filtro if juego_filtro else ''}...")
    
    if not os.path.exists(SIMULACIONES_FILE):
        return

    df = pd.read_csv(SIMULACIONES_FILE)
    
    # Filtrar solo lo auditado y exitoso
    # Definimos éxito: Score > 40 o Aciertos >= 3 (ajustable por juego)
    df = df[df['estado'] == 'AUDITADO'].copy()
    
    if juego_filtro:
        df = df[df['juego'] == juego_filtro]
    
    if sorteo_limite:
        # Importante: Solo miramos hasta el sorteo indicado para no hacer trampa (look-ahead)
        df = df[df['sorteo_objetivo'] <= int(sorteo_limite)]

    if len(df) == 0:
        return

    # Cargar cerebro actual
    genoma = cargar_genoma()
    ranking_actual = genoma.get("algo_ranking", {})
    
    # --- LÓGICA DE APRENDIZAJE INCREMENTAL (EMA) ---
    # En lugar de recalcular todo de cero, vamos a ajustar los pesos
    # basándonos en el rendimiento reciente.
    
    # 1. Calcular rendimiento promedio en este lote de datos
    nuevo_ranking = df.groupby('algoritmo')['score_afinidad'].mean().to_dict()
    
    # 2. Fusionar con el conocimiento previo usando EMA
    for algo, nuevo_score in nuevo_ranking.items():
        score_antiguo = ranking_actual.get(algo, nuevo_score) # Si es nuevo, usamos su score actual
        
        # Fórmula: Nuevo = (Antiguo * (1 - Alpha)) + (Nuevo * Alpha)
        # Esto suaviza la curva. Si Alpha es bajo, el sistema es conservador.
        ranking_actual[algo] = round((score_antiguo * (1 - ALPHA)) + (nuevo_score * ALPHA), 2)

    # --- ANÁLISIS MORFOLÓGICO (ESTO SÍ PUEDE SER GLOBAL) ---
    # Para sumas y pares, mejor usar una ventana móvil de los últimos 50 éxitos
    exitosas = df[(df['score_afinidad'] >= 50)].tail(50) # Últimas 50 buenas
    
    rango_suma = genoma.get("morphology", {}).get("ideal_sum_range", "UNKNOWN")
    balance_paridad = genoma.get("morphology", {}).get("ideal_even_count", "UNKNOWN")

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
            rango_suma = [int(np.percentile(sumas, 25)), int(np.percentile(sumas, 75))]
        if pares:
            balance_paridad = int(round(np.mean(pares)))

    # --- GUARDAR ---
    genoma["metadata"] = {
        "updated_at": hora_chile.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "INCREMENTAL_EMA"
    }
    genoma["algo_ranking"] = ranking_actual
    genoma["morphology"] = {
        "ideal_sum_range": rango_suma,
        "ideal_even_count": balance_paridad
    }
    
    # Guardamos hasta qué sorteo aprendimos para cada juego
    if "last_processed" not in genoma: genoma["last_processed"] = {}
    if juego_filtro and sorteo_limite:
        genoma["last_processed"][juego_filtro] = int(sorteo_limite)

    with open(GENOMA_FILE, 'w', encoding='utf-8') as f:
        json.dump(genoma, f, indent=2)
    
    print(f"   🧬 Genoma actualizado. Líder actual: {max(ranking_actual, key=ranking_actual.get)} ({max(ranking_actual.values())} pts)")

if __name__ == "__main__":
    analizar_adn_ganador()