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

        # --- B. APRENDIZAJE MORFOLÓGICO AVANZADO (V3) ---
        # Inicializamos estructura con valores por defecto relajados
        memoria_morf = genoma["morphology"].get(juego_id, {
            "ideal_sum_range": [0, 999],
            "ideal_even_count": -1,
            "ideal_consecutivos": -1, # NUEVO
            "ideal_bajos_altos": -1,  # NUEVO (Ratio: Cantidad de bajos)
            "ideal_terminaciones": -1 # NUEVO (Cant. de terminaciones únicas)
        })

        # Filtramos jugadas exitosas (Score > 50) del lote actual
        exitosas = df_juego[df_juego['score_afinidad'] >= 50]
        
        if len(exitosas) > 0:
            sumas = []
            pares = []
            consecutivos = []
            bajos = []
            terminaciones = []
            
            # Definir frontera bajo/alto (aprox mitad del tablero)
            # Asumimos Loto clásico (41 bolas) -> Frontera 21
            limite_bajo = 21 
            if juego_id == "LOTO3": limite_bajo = 5
            elif juego_id == "RACHA": limite_bajo = 10

            for _, row in exitosas.iterrows():
                try:
                    nums = sorted(json.loads(row['numeros'])) # Importante: Ordenados
                    if not nums: continue
                    
                    # 1. Suma
                    sumas.append(sum(nums))
                    
                    # 2. Pares
                    pares.append(len([n for n in nums if n % 2 == 0]))
                    
                    # 3. Consecutivos (NUEVO)
                    cons = 0
                    for i in range(len(nums)-1):
                        if nums[i+1] == nums[i] + 1:
                            cons += 1
                    consecutivos.append(cons)
                    
                    # 4. Bajos/Altos (NUEVO) - Contamos cuántos son "bajos"
                    cnt_bajos = len([n for n in nums if n <= limite_bajo])
                    bajos.append(cnt_bajos)
                    
                    # 5. Terminaciones (NUEVO) - Uniques last digits
                    # Ej: 12, 22, 35 -> Terminaciones 2, 2, 5 -> Únicas: {2, 5} -> Count 2
                    last_digits = len(set([n % 10 for n in nums]))
                    terminaciones.append(last_digits)

                except Exception as e: pass
            
            # --- ACTUALIZACIÓN DE MEMORIA (Suavizado Exponencial) ---
            def actualizar_promedio(clave, nuevos_datos):
                if not nuevos_datos: return
                new_avg = np.mean(nuevos_datos)
                old_val = memoria_morf.get(clave, -1)
                
                if old_val == -1: 
                    memoria_morf[clave] = float(round(new_avg, 2))
                else:
                    # 20% Novedad, 80% Historia
                    memoria_morf[clave] = float(round((old_val * 0.8) + (new_avg * 0.2), 2))

            # 1. Rango de Suma (Percentiles suavizados)
            if sumas:
                p25, p75 = np.percentile(sumas, 25), np.percentile(sumas, 75)
                old_min, old_max = memoria_morf.get("ideal_sum_range", [0, 999])
                new_min = int((old_min * 0.8) + (p25 * 0.2))
                new_max = int((old_max * 0.8) + (p75 * 0.2))
                memoria_morf["ideal_sum_range"] = [new_min, new_max]

            # 2. Métricas de conteo
            actualizar_promedio("ideal_even_count", pares)
            actualizar_promedio("ideal_consecutivos", consecutivos)
            actualizar_promedio("ideal_bajos_altos", bajos)
            actualizar_promedio("ideal_terminaciones", terminaciones)
            
            genoma["morphology"][juego_id] = memoria_morf
            print(f"   🧬 Morfología evolucionada para {juego_id}")

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