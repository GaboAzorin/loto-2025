import pandas as pd
import json
import os
import numpy as np
from datetime import datetime

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
SIMULACIONES_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
GENOMA_FILE = os.path.join(DATA_DIR, "loto_genome.json")

def analizar_adn_ganador():
    print("🧠 INICIANDO ENTRENAMIENTO COGNITIVO...")
    
    if not os.path.exists(SIMULACIONES_FILE):
        print("⚠️ No hay simulaciones para entrenar.")
        return

    df = pd.read_csv(SIMULACIONES_FILE)
    
    # 1. FILTRADO: Solo aprendemos de los mejores
    # Consideramos "Exitosas" las jugadas auditadas con score > 40 (o que tengan aciertos > 3)
    exitosas = df[
        (df['estado'] == 'AUDITADO') & 
        ((df['score_afinidad'] >= 40.0) | (df['aciertos'] >= 3))
    ].copy()

    if len(exitosas) < 5:
        print("📉 Aún no hay suficientes casos de éxito para aprender patrones profundos.")
        return

    print(f"🧬 Analizando ADN de {len(exitosas)} casos de éxito...")

    # --- A. APRENDIZAJE TEMPORAL (Golden Hours) ---
    # ¿A qué hora se generaron las mejores predicciones?
    hot_hours = exitosas['hora_dia'].value_counts(normalize=True).to_dict()
    
    # --- B. EFICACIA DE ALGORITMOS ---
    # ¿Qué algoritmo está rindiendo mejor realmente?
    algo_performance = exitosas.groupby('algoritmo')['score_afinidad'].mean().to_dict()

    # --- C. ANÁLISIS MORFOLÓGICO (ADN de los números) ---
    # Vamos a ver qué características tienen los números ganadores
    sumas_exitosas = []
    pares_exitosos = []
    
    for _, row in exitosas.iterrows():
        try:
            numeros = json.loads(row['numeros']) # Convertir string a lista
            if isinstance(numeros, list) and len(numeros) > 0:
                sumas_exitosas.append(sum(numeros))
                pares = len([n for n in numeros if n % 2 == 0])
                pares_exitosos.append(pares)
        except: pass
    
    # Calcular rangos ideales
    rango_suma = "UNKNOWN"
    balance_paridad = "UNKNOWN"
    
    if sumas_exitosas:
        p25 = np.percentile(sumas_exitosas, 25)
        p75 = np.percentile(sumas_exitosas, 75)
        rango_suma = [int(p25), int(p75)]
    
    if pares_exitosos:
        promedio_pares = int(np.round(np.mean(pares_exitosos)))
        balance_paridad = promedio_pares # Ej: 3 significa 3 pares (y 3 impares en Loto)

    # --- CONSTRUCCIÓN DEL GENOMA ---
    genoma = {
        "metadata": {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "casos_estudiados": len(exitosas)
        },
        "golden_hours": {str(k): round(v, 4) for k, v in hot_hours.items()}, # Horas donde la IA es más fuerte
        "algo_ranking": {k: round(v, 2) for k, v in algo_performance.items()}, # Pesos de algoritmos
        "morphology": {
            "ideal_sum_range": rango_suma,
            "ideal_even_count": balance_paridad
        }
    }

    # Guardar Conocimiento
    with open(GENOMA_FILE, 'w', encoding='utf-8') as f:
        json.dump(genoma, f, indent=2)
    
    print("💡 APRENDIZAJE COMPLETADO. Nuevo genoma generado.")
    print(f"   🕒 Horas Doradas detectadas: {list(hot_hours.keys())[:3]}")
    print(f"   ⚖️ Rango de Suma Ideal: {rango_suma}")

if __name__ == "__main__":
    analizar_adn_ganador()