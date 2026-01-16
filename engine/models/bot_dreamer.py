import pandas as pd
import glob
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

def clean_for_json(obj):
    """Sustituye NaNs por None para generar un JSON válido"""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(i) for i in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj

# Aseguramos que Python encuentre el módulo analizador_forense
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.append(current_dir)

try:
    from analizador_forense import LotoForense 
except ImportError:
    LotoForense = None
    print("⚠️ ADVERTENCIA: No se pudo importar LotoForense. El bot funcionará a media capacidad.")

try:
    from meta_learner import MetaLearner
except ImportError:
    MetaLearner = None
    print("⚠️ MetaLearner no disponible. Usando pesos lineales.")

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
    
    return cursor_id, cursor_tiempo

def cargar_genoma():
    """Carga el archivo JSON del cerebro"""
    if os.path.exists(FILE_GENOME):
        try:
            with open(FILE_GENOME, 'r') as f:
                return json.load(f)
        except: pass
    return {}

def obtener_pesos_del_lobulo(game_id, genoma, hora=None):
    """
    NIVEL 2: Sensibilidad Horaria.
    Busca rankings específicos para la hora actual; si no existen, usa el ranking global.
    """
    pesos = {}
    
    # Intentamos obtener el ranking específico de la hora (ej: "21")
    # Si no existe la llave 'algo_ranking_hourly', cae al ranking global por defecto
    ranking_juego = genoma.get("algo_ranking_hourly", {}).get(game_id, {}).get(str(hora), {})
    
    if not ranking_juego:
        # Fallback al ranking global si no hay datos horarios aún
        ranking_juego = genoma.get("algo_ranking", {}).get(game_id, {})
    
    if ranking_juego:
        for algo_name, score in ranking_juego.items():
            # Escala logarítmica para suavizar diferencias
            pesos[algo_name] = max(0.5, math.log(max(1, score) + 1))
    
    return pesos

def validar_cognitivamente(numeros, genoma, game_id, factor_tolerancia=1.0):
    if not genoma or not numeros: return True, 0.0, "OK"
    
    try:
        morph = genoma.get('morphology', {}).get(game_id, {})
        if not morph: return True, 0.0, "OK"
        
        nums = sorted(numeros)
        desviacion_acumulada = 0.0
        
        # 1. Validación de Suma (Diferencia cuadrática para penalizar extremos)
        rango_suma = morph.get('ideal_sum_range', [0, 999])
        suma_actual = sum(nums)
        if suma_actual < rango_suma[0]:
            desviacion_acumulada += (rango_suma[0] - suma_actual) * 3 # Penalización agresiva
        elif suma_actual > rango_suma[1]:
            desviacion_acumulada += (suma_actual - rango_suma[1]) * 3

        # 2. Métricas de Proporción
        metricas = {
            "ideal_even_count": len([n for n in nums if n % 2 == 0]),
            "ideal_consecutivos": sum(1 for i in range(len(nums)-1) if nums[i+1] == nums[i] + 1),
            "ideal_primos": len([n for n in nums if n in {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41}])
        }

        for clave, valor_real in metricas.items():
            ideal = morph.get(clave, -1)
            if ideal != -1:
                desviacion_acumulada += abs(valor_real - ideal) * 5 # Peso alto a la morfología

        # --- 🟢 MEJORA: Umbral dinámico por juego ---
        # LOTO3 necesita rigor (umbral 10), LOTO puede ser más flexible (umbral 40)
        umbrales = {"LOTO3": 8, "LOTO4": 20, "RACHA": 30, "LOTO": 40}
        umbral_base = umbrales.get(game_id, 30)
        
        umbral_veto = umbral_base * factor_tolerancia
        pasa_filtro = desviacion_acumulada < umbral_veto

        return pasa_filtro, round(desviacion_acumulada, 2), "OK"
    except Exception as e:
        return True, 999.0, f"ERROR: {e}"

def calcular_nivel_confianza(bolsa_pesos, n_objetivo):
    """
    NIVEL 1: Filtro de Confianza.
    Mide la fuerza del consenso basado en la concentración de votos.
    """
    if not bolsa_pesos: return 0.0
    
    # Sumamos todos los pesos entregados por los algoritmos
    total_pesos_repartidos = sum(bolsa_pesos.values())
    
    # Obtenemos los pesos de los 'n' números más votados (el top del consenso)
    ranking_pesos = sorted(bolsa_pesos.values(), reverse=True)
    pesos_consenso_top = sum(ranking_pesos[:n_objetivo])
    
    # La confianza es el % de votos que se concentraron en los números ganadores
    confianza = (pesos_consenso_top / total_pesos_repartidos) * 100
    return round(confianza, 2)

def soñar():
    print("💤 --- INICIANDO BOT SOÑADOR: LÓBULOS ESPECIALIZADOS v12.4 ---")

    # --- NIVEL 4: Instanciar Meta-Learner ---
    meta_cerebro = MetaLearner() if MetaLearner else None
    
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
        bolsa_pesos_consenso = {}
        top_consenso = []
        objetivo = None
        
        # A. Obtener pesos reales (Contextual Awareness: Sensibilidad Horaria)
        pesos_voto = obtener_pesos_del_lobulo(game_id, genoma, hora=hora_actual)
        print(f"   ⚖️ Pesos de confianza (basado en mérito local): {pesos_voto}")

        # B. Calcular Objetivo Crononauta (Lógica Completa)
        objetivo, fecha_sorteo = calcular_proximo_sorteo_real(game_id, config['csv'])
        print(f"   🎯 Objetivo Crononauta: #{objetivo}")
        
        # C. Instanciar Algoritmos
        try: 
            forense = LotoForense(game_id=game_id, target_day=dia_semana, genoma=genoma)
        except Exception as e:
            print(f"   ⚠️ Error instanciando Forense: {e}")
            continue

        # D. Usar los nuevos motores con Conciencia de ADN
        mis_algoritmos = [('forense_biometrico', forense.predict_weighted)]
        if config['algos_extra']:
            mis_algoritmos.extend([
                ('gaussiano_inteligente', forense.predict_smart_gaussian), # Nombre nuevo
                ('delta_dna',             forense.predict_dna_delta),      # Nombre nuevo
                ('markov_chain',          forense.predict_markov)
            ])

        for i, (nombre, funcion) in enumerate(mis_algoritmos):
            try:
                # --- CURADOR DE ÉLITE (Algoritmos Tradicionales) ---
                pool_alg = []
                for _ in range(50): 
                    candidato = funcion()
                    pasa, score_adn, _ = validar_cognitivamente(candidato, genoma, game_id)
                    if pasa:
                        pool_alg.append({'nums': candidato, 'score': score_adn})
                
                adn_info = ""
                if pool_alg:
                    ganador_alg = sorted(pool_alg, key=lambda x: x['score'])[0]
                    pred = ganador_alg['nums']
                    # Guardamos el score para el log (opcional)
                    adn_info = f"[Score ADN: {ganador_alg['score']}]"
                else:
                    # Si el algoritmo solo genera ruido, pasamos al siguiente
                    print(f"   ⚠️ {nombre}: Ningún candidato superó el filtro. Saltando.")
                    continue
                
                # Registrar Predicción Individual
                alg_name_trad = f"{nombre}_v1"
                nuevas_filas.append({
                    'id': base_id + i + (len(nuevas_filas)*100),
                    'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
                    'fecha_lanzamiento': fecha_sorteo.strftime('%d/%m/%Y %H:%M'),
                    'juego': game_id,
                    'numeros': list(pred), # Cambio: de str(pred) a list(pred)
                    'sorteo_objetivo': objetivo,
                    'estado': 'PENDIENTE',
                    'aciertos': 0, 'score_afinidad': 0.0,
                    'hora_dia': hora_actual,
                    'algoritmo': alg_name_trad,
                    'nota_especial': 'NORMAL' # Nueva línea: evita NaNs al consolidar
                })
                print(f"   🔹 {nombre}: {pred} {adn_info if 'adn_info' in locals() else ''}")
                
                # E. Voto para el Consenso (Ponderado por Ranking Local real)
                peso = pesos_voto.get(alg_name_trad, 1.0)

                # NIVEL 4: El Meta-Learner ajusta el peso si el modelo existe
                if meta_cerebro:
                    # El Meta-Learner evalúa qué tan creíble es este algoritmo ahora
                    multiplicador = meta_cerebro.predecir_confianza_real(
                        game_id, alg_name_trad, hora_actual, ganador_alg['score']
                    )
                    peso *= multiplicador
                
                # Simulamos N veces para robustecer el consenso
                validas = 0; reintentos = 0
                while validas < 5 and reintentos < 30:
                    sim = funcion()
                    ok_sim, _, _ = validar_cognitivamente(sim, genoma, game_id)
                    if ok_sim:
                        for num in sim:
                            bolsa_pesos_consenso[num] = bolsa_pesos_consenso.get(num, 0) + peso
                        validas += 1
                    reintentos += 1
                    
            except Exception as e:
                print(f"   ⚠️ Error en {nombre}: {e}")

        # --- BLOQUE: ORÁCULO NEURAL (MACHINE LEARNING) CON RESCATE DE DISIDENCIA ---
        if OraculoNeural:
            for v in ["v3", "v4"]:
                try:
                    oracle = OraculoNeural(game_id, version=v)
                    f_tol = 2.5 if v == "v4" else 1.0 
                    
                    pool_ml = []
                    reproches = {} 
                    intentos_totales = 100

                    for _ in range(intentos_totales):
                        candidato = oracle.predecir(fecha_objetivo=ahora, estocastico=True)
                        if candidato and len(candidato) == forense.rules['n']:
                            pasa, score_adn, motivo = validar_cognitivamente(candidato, genoma, game_id, factor_tolerancia=f_tol)
                            
                            # --- 🚀 MEJORA: DETECTOR DE DISIDENCIA (Solo para v4) ---
                            es_disidente = False
                            if not pasa and v == "v4" and meta_cerebro:
                                # Consultamos al Meta-Learner si este modelo tiene "luz verde" por mérito real
                                multiplicador_ml = meta_cerebro.predecir_confianza_real(
                                    game_id, f'oraculo_neural_{v}', hora_actual, score_adn
                                )
                                # Si la confianza es > 2.5, es un "Genio Incomprendido" (rompe reglas pero acierta)
                                if multiplicador_ml > 2.5:
                                    es_disidente = True
                            
                            if pasa or es_disidente:
                                pool_ml.append({
                                    'nums': candidato, 
                                    'score': score_adn,
                                    'estado_adn': "OK" if pasa else "DISIDENTE"
                                })
                            else:
                                reproches[motivo] = reproches.get(motivo, 0) + 1
                    
                    if pool_ml:
                        # 1. Selección del mejor candidato del pool basado en ADN
                        ganador_ml = sorted(pool_ml, key=lambda x: x['score'])[0]
                        pred_ml = ganador_ml['nums']
                        alg_name_ml = f'oraculo_neural_{v}'
                        
                        # 2. Cálculo de Confianza Real vía Meta-Learner
                        # Obtenemos el multiplicador de esperanza de éxito histórico
                        confianza_ml_individual = 1.0
                        if meta_cerebro:
                            confianza_ml_individual = meta_cerebro.predecir_confianza_real(
                                game_id, alg_name_ml, hora_actual, ganador_ml['score']
                            )
                        
                        # 3. Clasificación para el Dashboard (Rescate de Disidencia)
                        nota = "ALERTA_DISIDENCIA" if ganador_ml['estado_adn'] == "DISIDENTE" else "NORMAL"
                        
                        # 4. Inserción en la cola con Metadata enriquecida
                        nuevas_filas.append({
                            'id': base_id + 999 + (len(nuevas_filas)*10),
                            'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
                            'fecha_lanzamiento': fecha_sorteo.strftime('%d/%m/%Y %H:%M'),
                            'juego': game_id,
                            'numeros': list(top_consenso), # Asegurar lista
                            'sorteo_objetivo': objetivo_sorteo,
                            'estado': 'PENDIENTE',
                            'aciertos': 0, 
                            'score_afinidad': confianza_final,
                            'hora_dia': hora_actual,
                            'algoritmo': 'consenso_meritocratico_v2',
                            'nota_especial': 'NORMAL' # Nueva línea: evita NaNs al consolidar
                        })
                        
                        # 5. Voto Ponderado para el Consenso Meritocrático
                        # El Meta-Learner decide cuánto peso real tiene esta opinión hoy
                        peso_ia = pesos_voto.get(alg_name_ml, 1.0) 
                        if meta_cerebro:
                            peso_ia *= confianza_ml_individual
                        
                        # Los disidentes (v4) reciben un impulso extra de presencia si son validados por el Meta-Learner
                        multiplicador_voto = 5 if nota == "NORMAL" else 8
                        
                        for num in pred_ml:
                            bolsa_pesos_consenso[num] = bolsa_pesos_consenso.get(num, 0) + (peso_ia * multiplicador_voto)
                        
                        label_status = f"[{ganador_ml['estado_adn']}]"
                        print(f"   🔹 {alg_name_ml} (Pool: {len(pool_ml)}): {pred_ml} {label_status} [Confianza: {round(confianza_ml_individual, 2)}x]")
                    
                    else:
                        pred_ml = None
                        print(f"   ❌ {v} SILENCIADO. Motivos: {reproches}")

                except Exception as e:
                    print(f"   ⚠️ Fallo en ML {v}: {e}")
        # -------------------------------------------------------

        # F. Generar Consenso Meritocrático con Filtro de Curación
        try:
            if bolsa_pesos_consenso and objetivo: # Cambiar esta condición
                n_balls = forense.rules['n']
                
                # Reiniciamos variables locales del consenso
                ranking_bolas = sorted(bolsa_pesos_consenso, key=bolsa_pesos_consenso.get, reverse=True)
                candidato_top = sorted(ranking_bolas[:n_balls])
                
                # Importante: top_consenso debe partir vacío o con el candidato actual
                top_consenso = candidato_top
                objetivo_sorteo = objetivo
                
                # --- 🟢 ESTRATEGIA: SUEÑO CURADO ---
                top_consenso = []
                confianza_final = 0.0
                es_valida = False
                intentos_muestreo = 0
                
                # 1. Intento Determinista (Top N directo)
                ranking_bolas = sorted(bolsa_pesos_consenso, key=bolsa_pesos_consenso.get, reverse=True)
                candidato_top = sorted(ranking_bolas[:n_balls])
                pasa, score_adn, _ = validar_cognitivamente(candidato_top, genoma, game_id)
                
                if pasa:
                    top_consenso = candidato_top
                    es_valida = True
                    print(f"   ✅ Consenso Determinista validado (Score ADN: {score_adn})")
                else:
                    print(f"   ⚠️ Consenso Top-N rechazado por morfología. Iniciando Muestreo Estocástico...")
                    
                    # 2. Muestreo Estocástico: Elegimos números basados en su peso acumulado
                    # Preparamos probabilidades para np.random.choice
                    bolas_list = list(bolsa_pesos_consenso.keys())
                    pesos_list = np.array(list(bolsa_pesos_consenso.values()))
                    probabilidades = pesos_list / pesos_list.sum()

                    while intentos_muestreo < 200:
                        # Muestreamos n bolas sin repetición
                        muestreo = np.random.choice(bolas_list, size=n_balls, replace=False, p=probabilidades)
                        muestreo = sorted([int(x) for x in muestreo])
                        
                        pasa_m, score_m, _ = validar_cognitivamente(muestreo, genoma, game_id)
                        if pasa_m:
                            top_consenso = muestreo
                            es_valida = True
                            print(f"   ✨ Muestreo exitoso tras {intentos_muestreo} intentos (Score ADN: {score_m})")
                            break
                        intentos_muestreo += 1

                if not es_valida:
                    # Fallback al top si nada funcionó, pero marcamos como BAJA CONFIANZA
                    top_consenso = candidato_top
                    print(f"   🚨 ADVERTENCIA: No se halló combinación ideal. Usando fallback.")

                # Cálculo de confianza final
                confianza_final = calcular_nivel_confianza(bolsa_pesos_consenso, n_balls)
                alerta = "🔥 ALTA CONFIANZA" if (confianza_final > 25 and es_valida) else "⚠️ RUIDO DETECTADO"
                
                nuevas_filas.append({
                    'id': base_id + 999 + (len(nuevas_filas)*10),
                    'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
                    'fecha_lanzamiento': fecha_sorteo.strftime('%d/%m/%Y %H:%M'),
                    'juego': game_id,
                    'numeros': top_consenso,
                    'sorteo_objetivo': objetivo_sorteo,
                    'estado': 'PENDIENTE',
                    'aciertos': 0, 
                    'score_afinidad': confianza_final,
                    'hora_dia': hora_actual,
                    'algoritmo': 'consenso_meritocratico_v2',
                    'nota_especial': alerta
                })
                print(f"   🤝 TICKET FINAL: {top_consenso} | {alerta} ({confianza_final}%)")
        except Exception as e:
            print(f"   ❌ Error en fase de consenso: {e}")

    # G. Guardado Asíncrono (QUEUE SYSTEM)
    import uuid
    QUEUE_DIR = os.path.join(DATA_DIR, 'queue')
    os.makedirs(QUEUE_DIR, exist_ok=True)

    if nuevas_filas:
        # 1. Guardar los tickets individuales en la queue
        for fila in nuevas_filas:
            fila_limpia = clean_for_json(fila) # Sanitización final
            file_id = str(uuid.uuid4())
            filepath = os.path.join(QUEUE_DIR, f"prediccion_{file_id}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(fila_limpia, f, ensure_ascii=False, indent=2)

        # 2. ¡EL CIERRE DEL CÍRCULO! 
        print("🔄 Forzando sincronización del laboratorio...")
        try:
            from consolidar_laboratorio import ejecutar_consolidacion_hibrida
            ejecutar_consolidacion_hibrida()
            print("✅ Dashboard sincronizado correctamente.")
        except Exception as e:
            print(f"❌ Error fatal sincronizando dashboard: {e}")

    print("\n✨ PROCESO DEL SOÑADOR TERMINADO.")

if __name__ == "__main__":
    soñar()