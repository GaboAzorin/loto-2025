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
ALPHA = 0.3 

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
    
    # Obtenemos el ID de la última fila que aprendimos en la sesión anterior
    last_trained_id = metadata.get("last_trained_id", -1)
    print(f"   📅 Último ID aprendido: {last_trained_id}")

    # 2. Cargar CSV y Filtrar Novedades
    try:
        df = pd.read_csv(SIMULACIONES_FILE)
    except Exception as e:
        print(f"   ❌ Error leyendo CSV: {e}")
        return

    # FILTRO CRÍTICO: Solo AUDITADO y solo IDs nuevos
    # Esto evita la "Doble Contabilidad"
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
        # Calculamos el desempeño SOLO de este lote nuevo
        performance_lote = df_juego.groupby('algoritmo')['score_afinidad'].mean().to_dict()
        
        # Recuperamos la memoria previa
        ranking_juego = ranking_global.get(juego_id, {})
        
        for algo, score_lote in performance_lote.items():
            score_antiguo = ranking_juego.get(algo, score_lote) # Si es nuevo, nace con su score actual
            
            # FÓRMULA EMA: Actualizamos el peso sináptico
            # Nuevo = (Viejo * 0.7) + (Novedad * 0.3)
            nuevo_valor = (score_antiguo * (1 - ALPHA)) + (score_lote * ALPHA)
            ranking_juego[algo] = round(nuevo_valor, 2)
        
        ranking_global[juego_id] = ranking_juego
        print(f"   📈 Ranking actualizado para {juego_id}")

        # --- B. APRENDIZAJE MORFOLÓGICO (Estadística acumulativa) ---
        # Nota: Para morfología, a veces es útil ver un poco más de historia, 
        # pero para mantener coherencia, actualizamos con ventana móvil si es posible.
        # Aquí mantendremos una lógica simple: miramos las exitosas recientes del lote.
        
        if "morphology" not in genoma: genoma["morphology"] = {}
        memoria_morf = genoma["morphology"].get(juego_id, {"ideal_sum_range": [0, 999], "ideal_even_count": -1})

        exitosas = df_juego[df_juego['score_afinidad'] >= 50]
        
        if len(exitosas) > 0:
            sumas = []
            pares = []
            for _, row in exitosas.iterrows():
                try:
                    nums = json.loads(row['numeros'])
                    sumas.append(sum(nums))
                    pares.append(len([n for n in nums if n % 2 == 0]))
                except: pass
            
            # Actualización suave de morfología (Promedio ponderado simple con lo anterior)
            if sumas:
                # Calculamos percentiles actuales
                p25_new, p75_new = np.percentile(sumas, 25), np.percentile(sumas, 75)
                # Recuperamos rango anterior
                old_range = memoria_morf.get("ideal_sum_range", [0, 999])
                # Mezclamos (Suavizado)
                new_min = int((old_range[0] * 0.8) + (p25_new * 0.2))
                new_max = int((old_range[1] * 0.8) + (p75_new * 0.2))
                memoria_morf["ideal_sum_range"] = [new_min, new_max]

            if pares:
                new_avg = np.mean(pares)
                old_val = memoria_morf.get("ideal_even_count", -1)
                if old_val == -1: final_pares = new_avg
                else: final_pares = (old_val * 0.8) + (new_avg * 0.2)
                memoria_morf["ideal_even_count"] = int(round(final_pares))
            
            genoma["morphology"][juego_id] = memoria_morf

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