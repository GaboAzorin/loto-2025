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
    Extrae los pesos reales del genoma. 
    Si un algoritmo no existe, nace con peso 1.0 (Probatoria).
    """
    pesos = {}
    ranking_juego = genoma.get("algo_ranking", {}).get(game_id, {})
    
    # Extraemos todos los algoritmos registrados para ese juego
    if ranking_juego:
        for algo_name, score in ranking_juego.items():
            # Aplicamos escala logarítmica para evitar el 'Efecto Dictador'
            pesos[algo_name] = max(0.5, math.log(max(1, score) + 1))
    
    return pesos

def validar_cognitivamente(numeros, genoma, game_id, factor_tolerancia=1.0):
    """
    Filtro Pentadimensional con Tolerancia Dinámica.
    factor_tolerancia: 1.0 para normal, >1.0 para permitir modelos experimentales.
    """
    if not genoma or not numeros: return True, "OK"
    
    try:
        morph = genoma.get('morphology', {}).get(game_id, {})
        if not morph: return True, "OK"
        
        nums = sorted(numeros)
        
        # Helper con tolerancia expandible
        def validar_conteo(key, valor_real, tol_base=1.2):
            ideal = morph.get(key, -1)
            if ideal == -1: return True
            return abs(valor_real - ideal) <= (tol_base * factor_tolerancia)

        # 1. Suma (Relajamos los límites un 20% extra si el factor es > 1)
        rango_suma = morph.get('ideal_sum_range')
        if rango_suma and isinstance(rango_suma, list):
            suma = sum(nums)
            mult_inf = 0.8 / factor_tolerancia
            mult_sup = 1.2 * factor_tolerancia
            if suma < (rango_suma[0] * mult_inf) or suma > (rango_suma[1] * mult_sup):
                return False, "SUMA"

        # 2. Métricas
        if not validar_conteo("ideal_even_count", len([n for n in nums if n % 2 == 0]), 1.5): return False, "PARES"
        
        cons = sum(1 for i in range(len(nums)-1) if nums[i+1] == nums[i] + 1)
        if not validar_conteo("ideal_consecutivos", cons, 1.2): return False, "CONSEC"
        
        limite = 4 if game_id == "LOTO3" else (10 if game_id == "RACHA" else 21)
        bajos = len([n for n in nums if n <= limite])
        if not validar_conteo("ideal_bajos_altos", bajos, 1.5): return False, "BAJOS"
        
        last_digits = len(set([n % 10 for n in nums]))
        if not validar_conteo("ideal_terminaciones", last_digits, 1.2): return False, "TERM"

        # 3. Métricas V4
        PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41}
        cnt_primos = len([n for n in nums if n in PRIMOS])
        if not validar_conteo("ideal_primos", cnt_primos, 1.5): return False, "PRIMOS"

        if len(nums) > 1:
            avg_diff = sum([nums[i+1] - nums[i] for i in range(len(nums)-1)]) / (len(nums)-1)
            if not validar_conteo("ideal_avg_delta", avg_diff, 2.5): return False, "DELTA"

        return True, "OK"

    except Exception:
        return True, "FAIL_SAFE"

def soñar():
    print("💤 --- INICIANDO BOT SOÑADOR: LÓBULOS ESPECIALIZADOS v12.4 ---")
    
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
        
        # A. Obtener pesos reales para este juego (Ranking Local)
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
                    # FIX: Desempaquetar la tupla para evitar la trampa del booleano
                    ok, _ = validar_cognitivamente(pred, genoma, game_id)
                    if ok: break 
                    pred = funcion()
                    intentos += 1
                
                # Registrar Predicción Individual
                alg_name_trad = f"{nombre}_v1"
                nuevas_filas.append({
                    'id': base_id + i + (len(nuevas_filas)*100),
                    'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
                    'juego': game_id,
                    'numeros': str(pred),
                    'sorteo_objetivo': objetivo,
                    'estado': 'PENDIENTE',
                    'aciertos': 0, 'score_afinidad': 0.0,
                    'hora_dia': hora_actual,
                    'algoritmo': alg_name_trad
                })
                print(f"   🔹 {nombre}: {pred}")
                
                # E. Voto para el Consenso (Ponderado por Ranking Local real)
                peso = pesos_voto.get(alg_name_trad, 1.0)
                
                # Simulamos N veces para robustecer el consenso
                validas = 0; reintentos = 0
                while validas < 5 and reintentos < 30:
                    sim = funcion()
                    ok_sim, _ = validar_cognitivamente(sim, genoma, game_id)
                    if ok_sim:
                        for num in sim:
                            bolsa_pesos_consenso[num] = bolsa_pesos_consenso.get(num, 0) + peso
                        validas += 1
                    reintentos += 1
                    
            except Exception as e:
                print(f"   ⚠️ Error en {nombre}: {e}")

        # --- BLOQUE: ORÁCULO NEURAL (MACHINE LEARNING) ---
        if OraculoNeural:
            for v in ["v3", "v4"]:
                try:
                    oracle = OraculoNeural(game_id, version=v)
                    # La v4 recibe un "Permiso de Innovación" (50% más de tolerancia)
                    f_tol = 1.5 if v == "v4" else 1.0 
                    
                    intentos = 0; pred_ml = None
                    reproches = {} # Para saber por qué falla (Trazabilidad)

                    while intentos < 30:
                        candidato = oracle.predecir(fecha_objetivo=datetime.now(TZ_CHILE), estocastico=True)
                        if candidato and len(candidato) == forense.rules['n']:
                            ok, motivo = validar_cognitivamente(candidato, genoma, game_id, factor_tolerancia=f_tol)
                            if ok:
                                pred_ml = candidato
                                break
                            else:
                                reproches[motivo] = reproches.get(motivo, 0) + 1
                        intentos += 1
                    
                    if pred_ml:
                        alg_name_ml = f'oraculo_neural_{v}'
                        nuevas_filas.append({
                            'id': base_id + (444 if v=="v4" else 888) + (len(nuevas_filas)*10),
                            'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
                            'juego': game_id,
                            'numeros': str(sorted(pred_ml)),
                            'sorteo_objetivo': objetivo,
                            'estado': 'PENDIENTE',
                            'aciertos': 0, 'score_afinidad': 0.0,
                            'hora_dia': hora_actual,
                            'algoritmo': alg_name_ml
                        })
                        
                        # FIX: Sincronización con el mérito real del Genoma
                        peso_ia = pesos_voto.get(alg_name_ml, 1.0) 
                        for num in pred_ml:
                            bolsa_pesos_consenso[num] = bolsa_pesos_consenso.get(num, 0) + peso_ia
                        
                        print(f"   🔹 {alg_name_ml}: {pred_ml} (OK tras {intentos} intentos)")
                    else:
                        print(f"   ❌ {v} SILENCIADO. Motivos: {reproches}")

                except Exception as e:
                    print(f"   ⚠️ Fallo en ML {v}: {e}")
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
    import uuid
    QUEUE_DIR = os.path.join(DATA_DIR, 'queue')
    os.makedirs(QUEUE_DIR, exist_ok=True)

    if nuevas_filas:
        print(f"📦 Generando {len(nuevas_filas)} tickets para la cola de procesamiento...")
        
        for fila in nuevas_filas:
            file_id = str(uuid.uuid4())
            filename = f"prediccion_{file_id}.json"
            filepath = os.path.join(QUEUE_DIR, filename)
            
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(fila, f, ensure_ascii=False, indent=2)
                # print(f"   -> Ticket guardado: {filename}")
            except Exception as e:
                print(f"   ❌ Error guardando ticket {filename}: {e}")

    print("\n✨ PROCESO DEL SOÑADOR TERMINADO (Datos en cola).")

if __name__ == "__main__":
    soñar()