import pandas as pd
import json
import os
import pytz
import time
import sys
import numpy as np
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
    Extrae los pesos de confianza del ranking específico de este juego.
    Esto permite que el consenso se incline por el mejor algoritmo de CADA juego.
    """
    pesos = {'forense': 1.0, 'gaussiano': 1.0, 'delta': 1.0, 'markov': 1.0}
    
    if not genoma: return pesos
    
    # Buscamos en el lóbulo de ranking específico (Estructura anidada)
    ranking_lobulo = genoma.get("algo_ranking", {}).get(game_id, {})
    
    # Si encontramos ranking específico, ajustamos pesos
    if ranking_lobulo and isinstance(ranking_lobulo, dict):
        for algo_name, score in ranking_lobulo.items():
            key = algo_name.split('_')[0] # ej: 'forense_biometrico_v1' -> 'forense'
            if key in pesos:
                # Convertimos score (0-100) en peso (0.2 - 3.0)
                # Un score alto le da más votos en el consenso
                pesos[key] = max(0.2, score / 8.0) 
    
    return pesos

def validar_cognitivamente(numeros, genoma, game_id):
    """
    Filtra predicciones basándose en la morfología específica del juego.
    """
    if not genoma: return True
    
    try:
        # Acceso por Lóbulo Específico
        todas_morfologias = genoma.get('morphology', {})
        morph = todas_morfologias.get(game_id, {})
        
        if not morph: return True
        
        # 1. Filtro de Rango de Suma
        rango_suma = morph.get('ideal_sum_range')
        if rango_suma and isinstance(rango_suma, list) and len(rango_suma) == 2:
            suma = sum(numeros)
            # Margen de tolerancia (+- 5) para flexibilidad
            if suma < (rango_suma[0] - 5) or suma > (rango_suma[1] + 5):
                return False
        
        # 2. Filtro de Paridad
        ideal_pares = morph.get('ideal_even_count')
        if ideal_pares is not None and isinstance(ideal_pares, int) and ideal_pares != -1:
            pares = len([n for n in numeros if n % 2 == 0])
            # Margen de tolerancia (+- 1)
            if abs(pares - ideal_pares) > 1:
                return False
                
        return True
    except:
        return True

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

    # G. Guardado Seguro
    if nuevas_filas:
        cols = ['id', 'fecha_generacion', 'juego', 'numeros', 'sorteo_objetivo', 'estado', 'aciertos', 'score_afinidad', 'hora_dia', 'algoritmo']
        try:
            df_new = pd.DataFrame(nuevas_filas)
            if os.path.exists(FILE_SIMULACIONES):
                df_old = pd.read_csv(FILE_SIMULACIONES)
                if 'juego' not in df_old.columns: df_old['juego'] = 'LOTO'
                df_final = pd.concat([df_old, df_new], ignore_index=True)
            else: df_final = df_new
            
            # Rellenar columnas faltantes con 0 o default
            for c in cols: 
                if c not in df_final.columns: df_final[c] = 0
                
            df_final.to_csv(FILE_SIMULACIONES, index=False, columns=cols)
            print(f"\n💾 Guardado exitoso: {len(nuevas_filas)} predicciones.")
        except Exception as e:
            print(f"❌ Error guardando CSV: {e}")

if __name__ == "__main__":
    soñar()