import pandas as pd
import json
import os
import pytz
import time
import sys
import numpy as np
from datetime import datetime, timedelta

# Aseguramos que Python encuentre el módulo analizador_forense
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.append(current_dir)

# Intentamos importar, si falla (porque no estamos en la carpeta correcta), no explotamos
try:
    from analizador_forense import LotoForense 
except ImportError:
    LotoForense = None

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
FILE_SIMULACIONES = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
FILE_GENOME = os.path.join(DATA_DIR, "loto_genome.json")

TZ_CHILE = pytz.timezone('America/Santiago')

# --- REGLAS DE NEGOCIO ---
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
    Algoritmo Crononauta: Determina el ID exacto del próximo sorteo basado en el último registrado.
    """
    path = os.path.join(DATA_DIR, csv_name)
    ahora = datetime.now(TZ_CHILE)
    
    try:
        if not os.path.exists(path): raise Exception("No CSV")
        df = pd.read_csv(path)
        if df.empty: raise Exception("CSV Vacío")
        
        last_row = df.iloc[-1]
        last_id = int(last_row['sorteo'])
        
        # Parseo de fecha flexible
        fecha_str = str(last_row['fecha']).replace('T', ' ').split('.')[0]
        try:
            last_date_naive = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
        except:
            last_date_naive = datetime.strptime(fecha_str, "%d-%m-%Y %H:%M:%S")
            
        cursor_tiempo = TZ_CHILE.localize(last_date_naive)
        cursor_id = last_id
        
    except:
        # Inicio en frío (sin historial)
        cursor_tiempo = ahora - timedelta(days=1)
        cursor_id = 0

    # Simulación temporal hacia el futuro
    reglas = HORARIOS[game_id]
    safety_break = 0
    
    while cursor_tiempo <= ahora and safety_break < 1000:
        safety_break += 1
        encontrado_siguiente = False
        # Miramos el futuro cercano (hoy + 3 días)
        for dias_extra in [0, 1, 2, 3]: 
            check_date = cursor_tiempo.date() + timedelta(days=dias_extra)
            dia_semana = check_date.weekday()
            
            if dia_semana not in reglas['dias']: continue
            
            for hora in sorted(reglas['horas']):
                candidato = TZ_CHILE.localize(datetime(check_date.year, check_date.month, check_date.day, hora, 0, 0))
                
                if candidato > cursor_tiempo:
                    cursor_tiempo = candidato
                    cursor_id += 1
                    encontrado_siguiente = True
                    break 
            
            if encontrado_siguiente: break
    
    return cursor_id

def obtener_pesos_inteligentes():
    pesos = {'forense': 1.0, 'gaussiano': 1.0, 'delta': 1.0, 'markov': 1.0}
    if os.path.exists(FILE_SIMULACIONES):
        try:
            df = pd.read_csv(FILE_SIMULACIONES)
            auditado = df[df['estado'] == 'AUDITADO']
            if not auditado.empty:
                ranking = auditado.groupby('algoritmo')['score_afinidad'].mean()
                for algo_name, score in ranking.items():
                    key = algo_name.split('_')[0]
                    if key in pesos:
                        pesos[key] = max(0.2, score / 50.0)
        except: pass
    return pesos

def cargar_genoma():
    if os.path.exists(FILE_GENOME):
        try:
            with open(FILE_GENOME, 'r') as f:
                return json.load(f)
        except: pass
    return {}

def validar_cognitivamente(numeros, genoma, game_id):
    """
    Filtra predicciones basándose en la morfología específica del juego (Lóbulos).
    """
    if not genoma: return True
    
    try:
        # --- CAMBIO CRÍTICO: Acceso por Lóbulo ---
        todas_morfologias = genoma.get('morphology', {})
        # Buscamos la memoria específica de ESTE juego. Si no hay, {} (Tabula Rasa)
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
    print("💤 --- INICIANDO BOT SOÑADOR MULTIVERSO v11.5 (LÓBULOS) ---")
    
    if LotoForense is None:
        print("❌ CRÍTICO: No se pudo importar LotoForense. Abortando sueño.")
        return

    ahora = datetime.now(TZ_CHILE)
    dia_semana = ahora.weekday()
    hora_actual = ahora.hour
    base_id = int(time.time())
    
    nuevas_filas = []
    pesos_voto = obtener_pesos_inteligentes()
    genoma = cargar_genoma()

    if genoma:
        print("   🧠 Cortex cargado: Filtros morfológicos activos por juego.")
    
    for game_id, config in MULTIVERSO_CONFIG.items():
        # Verificamos si estamos en hora de jugar para este juego
        # (Opcional: Si quieres que sueñe siempre, comenta el 'continue')
        # reglas = HORARIOS[game_id]
        # if dia_semana not in reglas['dias']: continue
        
        print(f"🌌 Universo: {game_id}")
        
        # 1. Calcular Objetivo Inteligente
        objetivo = calcular_proximo_sorteo_real(game_id, config['csv'])
        print(f"   🎯 Objetivo Crononauta: #{objetivo}")

        # 2. Instanciar Cerebro
        try:
            forense = LotoForense(game_id=game_id, target_day=dia_semana)
        except Exception as e:
            print(f"   ⚠️ Error instanciando Forense para {game_id}: {e}")
            continue

        # 3. Definir Algoritmos
        mis_algoritmos = [('forense_biometrico', forense.predict_weighted)]
        if config['algos_extra']:
            mis_algoritmos.extend([
                ('gaussiano_tactico', forense.predict_gaussian),
                ('delta_tactico',     forense.predict_delta),
                ('markov_chain',      forense.predict_markov)
            ])

        # 4. Ejecución
        bolsa_pesos_consenso = {} 

        for i, (nombre, funcion) in enumerate(mis_algoritmos):
            try:
                # Generación con Reintentos Cognitivos
                # Ahora aplicamos reintentos a TODOS los juegos (no solo Loto)
                intentos = 0
                max_intentos = 30 # Intentamos 30 veces encajar en el perfil morfológico
                
                pred = funcion()
                while intentos < max_intentos:
                    if validar_cognitivamente(pred, genoma, game_id):
                        break 
                    pred = funcion()
                    intentos += 1
                
                # Guardamos la predicción
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
                
                # Aporte al Consenso (Solo si es válida cognitivamente)
                # Esto purifica el consenso: solo entran votos de jugadas "inteligentes"
                peso = pesos_voto.get(nombre.split('_')[0], 1.0)
                simulaciones_validas = 0
                intentos_consenso = 0
                
                while simulaciones_validas < 5 and intentos_consenso < 30:
                    sim = funcion()
                    if validar_cognitivamente(sim, genoma, game_id):
                        for num in sim:
                            bolsa_pesos_consenso[num] = bolsa_pesos_consenso.get(num, 0) + peso
                        simulaciones_validas += 1
                    intentos_consenso += 1

            except Exception as e:
                print(f"   ⚠️ Error en {nombre}: {e}")

        # 5. Generar Consenso
        try:
            if bolsa_pesos_consenso:
                n_bolas = forense.rules['n']
                ranking = sorted(bolsa_pesos_consenso, key=bolsa_pesos_consenso.get, reverse=True)
                top_consenso = sorted(ranking[:n_bolas])
                
                # Loto 3 respeta orden de llegada si es necesario, pero usualmente se muestra ordenado
                if game_id != "LOTO3": 
                     top_consenso.sort()
                
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
                print(f"   🤝 CONSENSO: {top_consenso}")
        except: pass

    # Guardado Final
    if nuevas_filas:
        cols = ['id', 'fecha_generacion', 'juego', 'numeros', 'sorteo_objetivo', 'estado', 'aciertos', 'score_afinidad', 'hora_dia', 'algoritmo']
        try:
            df_new = pd.DataFrame(nuevas_filas)
            if os.path.exists(FILE_SIMULACIONES):
                df_old = pd.read_csv(FILE_SIMULACIONES)
                if 'juego' not in df_old.columns: df_old['juego'] = 'LOTO'
                df_final = pd.concat([df_old, df_new], ignore_index=True)
            else:
                df_final = df_new
            
            # Asegurar que todas las columnas existan
            for col in cols:
                if col not in df_final.columns: df_final[col] = 0
                
            df_final.to_csv(FILE_SIMULACIONES, index=False, columns=cols)
            print(f"\n💾 Éxito: {len(nuevas_filas)} sueños registrados en el CSV.")
        except Exception as e:
            print(f"❌ Error Guardado CSV: {e}")
    else:
        print("💤 No hubo actividad onírica en este ciclo.")

if __name__ == "__main__":
    soñar()