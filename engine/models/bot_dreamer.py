import pandas as pd
import json
import os
import pytz
import time
import sys
import numpy as np
import math
from datetime import datetime, timedelta

try:
    from oraculo_neural import OraculoNeural
except ImportError:
    OraculoNeural = None
    print("⚠️ Módulo OraculoNeural no disponible (¿Falta sklearn?).")

# Aseguramos que Python encuentre el módulo analizador_forense
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.append(current_dir)

try:
    from analizador_forense import LotoForense 
except ImportError:
    LotoForense = None
    print("⚠️ ADVERTENCIA: No se pudo importar LotoForense. El bot funcionará a media capacidad.")

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
FILE_SIMULACIONES = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
FILE_GENOME = os.path.join(DATA_DIR, "loto_genome.json")

TZ_CHILE = pytz.timezone('America/Santiago')

# --- REGLAS DE NEGOCIO (HORARIOS) ---
HORARIOS = {
    "LOTO":   {"dias": [1, 3, 6],       "horas": [21]},
    "LOTO3":  {"dias": [0,1,2,3,4,5,6], "horas": [14, 18, 21]},
    "LOTO4":  {"dias": [0,1,2,3,4,5,6], "horas": [14, 21]},
    "RACHA":  {"dias": [0,1,2,3,4,5,6], "horas": [15, 22]}
}

MULTIVERSO_CONFIG = {
    "LOTO":   {"csv": "LOTO_HISTORIAL_MAESTRO.csv", "algos_extra": True},
    "LOTO3":  {"csv": "LOTO3_MAESTRO.csv",          "algos_extra": False}, 
    "LOTO4":  {"csv": "LOTO4_MAESTRO.csv",          "algos_extra": False}, 
    "RACHA":  {"csv": "RACHA_MAESTRO.csv",          "algos_extra": False}  
}

def calcular_proximo_sorteo_real(game_id, csv_name):
    """
    Algoritmo Crononauta:
    1. Lee el último sorteo conocido del CSV (Ancla temporal).
    2. Simula el paso del tiempo sorteo a sorteo según las reglas horarias.
    3. Se detiene cuando encuentra el PRIMER sorteo que ocurre en el futuro respecto a 'ahora'.
    """
    path = os.path.join(DATA_DIR, csv_name)
    ahora = datetime.now(TZ_CHILE)
    
    # 1. Obtener Ancla (Último dato real disponible)
    try:
        if not os.path.exists(path): raise Exception("No CSV")
        df = pd.read_csv(path)
        if df.empty: raise Exception("CSV Vacío")
        
        last_row = df.iloc[-1]
        last_id = int(last_row['sorteo'])
        
        # Parseo robusto de fecha (soporta ISO y formato local)
        fecha_str = str(last_row['fecha']).replace('T', ' ').split('.')[0]
        try:
            last_date_naive = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
        except:
            last_date_naive = datetime.strptime(fecha_str, "%d-%m-%Y %H:%M:%S")
            
        # Localizar a Chile
        cursor_tiempo = TZ_CHILE.localize(last_date_naive)
        cursor_id = last_id
        
    except:
        # Si no hay datos, asumimos sorteo #0 y empezamos a buscar desde ayer
        # print(f"   ⚠️ Sin historial para {game_id}. Iniciando desde cero.")
        cursor_tiempo = ahora - timedelta(days=1)
        cursor_id = 0

    # 2. Simulación hacia el Futuro (Bridging the Gap)
    reglas = HORARIOS[game_id]
    safety_break = 0
    
    # Avanzamos en el tiempo virtualmente hasta alcanzar el presente
    while cursor_tiempo <= ahora and safety_break < 1000:
        safety_break += 1
        encontrado_siguiente = False
        
        # Revisamos los próximos 3 días buscando el siguiente slot de sorteo
        for dias_extra in [0, 1, 2, 3]: 
            check_date = cursor_tiempo.date() + timedelta(days=dias_extra)
            dia_semana = check_date.weekday()
            
            if dia_semana not in reglas['dias']: continue
            
            for hora in sorted(reglas['horas']):
                # Crear timestamp del slot candidato
                candidato = TZ_CHILE.localize(datetime(check_date.year, check_date.month, check_date.day, hora, 0, 0))
                
                # Si este candidato es ESTRICTAMENTE posterior al cursor actual
                if candidato > cursor_tiempo:
                    cursor_tiempo = candidato
                    cursor_id += 1
                    encontrado_siguiente = True
                    break 
            
            if encontrado_siguiente: break
    
    return cursor_id

def cargar_genoma():
    """Carga el archivo JSON del cerebro"""
    if os.path.exists(FILE_GENOME):
        try:
            with open(FILE_GENOME, 'r') as f:
                return json.load(f)
        except: pass
    return {}

def obtener_pesos_del_lobulo(game_id, genoma):
    """
    Extrae los pesos de confianza usando escala Logarítmica.
    Evita que un solo golpe de suerte (score 1000) rompa la democracia.
    """
    # Peso base mínimo para que todos tengan voz
    pesos = {'forense': 1.0, 'gaussiano': 1.0, 'delta': 1.0, 'markov': 1.0}
    
    if not genoma: return pesos
    
    ranking_lobulo = genoma.get("algo_ranking", {}).get(game_id, {})
    
    if ranking_lobulo and isinstance(ranking_lobulo, dict):
        for algo_name, score in ranking_lobulo.items():
            key = algo_name.split('_')[0]
            if key in pesos:
                # --- CORRECCIÓN LOGARÍTMICA ---
                # Score 0 -> log(1) = 0 -> Peso 0.5 (Mínimo)
                # Score 10 -> log(11) ≈ 2.4 
                # Score 100 -> log(101) ≈ 4.6
                # Score 1000 -> log(1001) ≈ 6.9
                # Esto comprime la escala: El mejor es 3x más fuerte que el promedio, no 100x.
                peso_log = math.log(max(1, score) + 1)
                
                # Asignamos peso con un piso de 0.5 para no silenciar totalmente a nadie
                pesos[key] = max(0.5, peso_log)
                
    return pesos

def validar_cognitivamente(numeros, genoma, game_id):
    """
    Filtro Pentadimensional V4: Ahora con Primos, Múltiplos y Deltas.
    """
    if not genoma or not numeros: return True
    
    try:
        morph = genoma.get('morphology', {}).get(game_id, {})
        if not morph: return True
        
        nums = sorted(numeros)
        
        # Helper para validación con tolerancia
        def validar_conteo(key, valor_real, tolerancia=1.2):
            ideal = morph.get(key, -1)
            if ideal == -1: return True
            return abs(valor_real - ideal) <= tolerancia

        # 1. Suma
        rango_suma = morph.get('ideal_sum_range')
        if rango_suma and isinstance(rango_suma, list):
            suma = sum(nums)
            if suma < (rango_suma[0] * 0.8) or suma > (rango_suma[1] * 1.2): return False

        # 2. Métricas Clásicas
        if not validar_conteo("ideal_even_count", len([n for n in nums if n % 2 == 0]), 1.5): return False
        
        cons = sum(1 for i in range(len(nums)-1) if nums[i+1] == nums[i] + 1)
        if not validar_conteo("ideal_consecutivos", cons, 1.2): return False # Tolerancia estricta en cluster
        
        limite = 4 if game_id == "LOTO3" else (10 if game_id == "RACHA" else 21)
        bajos = len([n for n in nums if n <= limite])
        if not validar_conteo("ideal_bajos_altos", bajos, 1.5): return False
        
        last_digits = len(set([n % 10 for n in nums]))
        if not validar_conteo("ideal_terminaciones", last_digits, 1.2): return False

        # 3. MÉTRICAS NUEVAS (V4)
        # A. Primos
        PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41}
        cnt_primos = len([n for n in nums if n in PRIMOS])
        if not validar_conteo("ideal_primos", cnt_primos, 1.5): return False

        # B. Múltiplos de 3
        cnt_mult3 = len([n for n in nums if n > 0 and n % 3 == 0])
        if not validar_conteo("ideal_multiples_3", cnt_mult3, 1.5): return False

        # C. Delta Promedio (Solo si hay más de 1 número)
        if len(nums) > 1:
            diffs = [nums[i+1] - nums[i] for i in range(len(nums)-1)]
            avg_diff = sum(diffs) / len(diffs)
            # Tolerancia un poco más amplia (2.5) porque la varianza es alta
            if not validar_conteo("ideal_avg_delta", avg_diff, 2.5): return False

        return True

    except Exception:
        return True # Fail-open

def soñar():
    print("💤 --- INICIANDO BOT SOÑADOR: LÓBULOS ESPECIALIZADOS v12.1 ---")
    
    if LotoForense is None:
        print("❌ CRÍTICO: No se pudo importar LotoForense. Abortando.")
        return

    ahora = datetime.now(TZ_CHILE)
    dia_semana = ahora.weekday()
    hora_actual = ahora.hour
    base_id = int(time.time())
    
    nuevas_filas = []
    genoma = cargar_genoma()

    if genoma:
        print("   🧠 Cortex cargado: Rankings y Morfología segmentados por juego.")

    for game_id, config in MULTIVERSO_CONFIG.items():
        print(f"🌌 Universo: {game_id}")
        
        # A. Obtener pesos específicos para este juego (Ranking Local)
        pesos_voto = obtener_pesos_del_lobulo(game_id, genoma)
        print(f"   ⚖️ Pesos de confianza (basado en mérito local): {pesos_voto}")

        # B. Calcular Objetivo Crononauta (Lógica Completa)
        objetivo = calcular_proximo_sorteo_real(game_id, config['csv'])
        print(f"   🎯 Objetivo Crononauta: #{objetivo}")
        
        # C. Instanciar Algoritmos
        try: 
            forense = LotoForense(game_id=game_id, target_day=dia_semana)
        except Exception as e:
            print(f"   ⚠️ Error instanciando Forense: {e}")
            continue

        mis_algoritmos = [('forense_biometrico', forense.predict_weighted)]
        if config['algos_extra']:
            mis_algoritmos.extend([
                ('gaussiano_tactico', forense.predict_gaussian),
                ('delta_tactico',     forense.predict_delta),
                ('markov_chain',      forense.predict_markov)
            ])

        # D. Ejecución de Algoritmos Individuales
        bolsa_pesos_consenso = {} 

        for i, (nombre, funcion) in enumerate(mis_algoritmos):
            try:
                # Reintentos Cognitivos (Rejection Sampling)
                intentos = 0
                max_intentos = 30 
                pred = funcion()
                
                while intentos < max_intentos:
                    if validar_cognitivamente(pred, genoma, game_id): break 
                    pred = funcion()
                    intentos += 1
                
                # Registrar Predicción Individual
                nuevas_filas.append({
                    'id': base_id + i + (len(nuevas_filas)*100),
                    'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
                    'juego': game_id,
                    'numeros': str(pred),
                    'sorteo_objetivo': objetivo,
                    'estado': 'PENDIENTE',
                    'aciertos': 0, 'score_afinidad': 0.0,
                    'hora_dia': hora_actual,
                    'algoritmo': f"{nombre}_v1"
                })
                print(f"   🔹 {nombre}: {pred}")
                
                # E. Voto para el Consenso (Ponderado por Ranking Local)
                key_algo = nombre.split('_')[0]
                peso = pesos_voto.get(key_algo, 1.0)
                
                # Simulamos N veces para robustecer el consenso
                validas = 0; reintentos = 0
                while validas < 5 and reintentos < 30:
                    sim = funcion()
                    if validar_cognitivamente(sim, genoma, game_id):
                        for num in sim:
                            bolsa_pesos_consenso[num] = bolsa_pesos_consenso.get(num, 0) + peso
                        validas += 1
                    reintentos += 1
                    
            except Exception as e:
                print(f"   ⚠️ Error en {nombre}: {e}")

        # --- BLOQUE NUEVO: ORÁCULO NEURAL (MACHINE LEARNING) ---
        # Este bloque corre fuera del bucle estándar porque usa una lógica distinta (predecir vs generar)
# --- BLOQUE: ORÁCULO NEURAL (MACHINE LEARNING) ---
        if OraculoNeural:
            try:
                oracle = OraculoNeural(game_id)
                fecha_target = datetime.now(TZ_CHILE)
                pred_ml = oracle.predecir(fecha_objetivo=fecha_target)
                
                # VALIDACIÓN: Chequeamos si el ML cumple las reglas de la casa
                # Solo entramos si el formato es correcto Y pasa el filtro cognitivo
                if pred_ml and len(pred_ml) == forense.rules['n']:
                    
                    if validar_cognitivamente(pred_ml, genoma, game_id): # <--- AGREGAR ESTO
                        
                        # 4.1 Guardar la jugada individual del ML
                        nuevas_filas.append({
                            'id': base_id + 888 + (len(nuevas_filas)*10),
                            'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
                            'juego': game_id,
                            'numeros': str(sorted(pred_ml)),
                            'sorteo_objetivo': objetivo,
                            'estado': 'PENDIENTE',
                            'aciertos': 0, 'score_afinidad': 0.0,
                            'hora_dia': hora_actual,
                            'algoritmo': 'oraculo_neural_v3'
                        })
                        
                        # 4.2 Votar en el Consenso
                        peso_ml = 2.0 
                        for num in pred_ml:
                             bolsa_pesos_consenso[num] = bolsa_pesos_consenso.get(num, 0) + peso_ml
                             
                        print(f"   🧠 ORÁCULO ML (Aprobado): {pred_ml}")
                    else:
                        print(f"   🚫 ORÁCULO ML (Rechazado por Morfología): {pred_ml}")

            except Exception as e:
                print(f"   ⚠️ Fallo en ML: {e}")
        # -------------------------------------------------------

        # F. Generar Consenso Meritocrático
        try:
            if bolsa_pesos_consenso:
                n = forense.rules['n']
                # Ordenamos las bolas por peso total acumulado
                ranking_bolas = sorted(bolsa_pesos_consenso, key=bolsa_pesos_consenso.get, reverse=True)
                top_consenso = sorted(ranking_bolas[:n])
                
                if game_id != "LOTO3": top_consenso.sort()
                
                nuevas_filas.append({
                    'id': base_id + 999 + (len(nuevas_filas)*10),
                    'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
                    'juego': game_id,
                    'numeros': str(top_consenso),
                    'sorteo_objetivo': objetivo,
                    'estado': 'PENDIENTE',
                    'aciertos': 0, 'score_afinidad': 0.0,
                    'hora_dia': hora_actual,
                    'algoritmo': 'consenso_meritocratico_v2'
                })
                print(f"   🤝 CONSENSO LOCAL: {top_consenso}")
        except: pass

    # G. Guardado Asíncrono (QUEUE SYSTEM)
        # En lugar de pelear por el CSV, guardamos un ticket único en la cola.
        import uuid
        
        QUEUE_DIR = os.path.join(DATA_DIR, 'queue')
        os.makedirs(QUEUE_DIR, exist_ok=True)

        if nuevas_filas:
            print(f"📦 Generando {len(nuevas_filas)} tickets para la cola de procesamiento...")
            
            for fila in nuevas_filas:
                # Generamos un ID único para el archivo
                file_id = str(uuid.uuid4())
                filename = f"prediccion_{file_id}.json"
                filepath = os.path.join(QUEUE_DIR, filename)
                
                # Guardamos el JSON individual
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(fila, f, ensure_ascii=False, indent=2)
                    print(f"   -> Ticket guardado: {filename}")
                except Exception as e:
                    print(f"   ❌ Error guardando ticket {filename}: {e}")

        print("\n✨ PROCESO DEL SOÑADOR TERMINADO (Datos en cola).")

if __name__ == "__main__":
    soñar()