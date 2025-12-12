import pandas as pd
import json
import os
import pytz
import time
import numpy as np
from datetime import datetime, timedelta

# Importamos el cerebro
from analizador_forense import LotoForense 

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
FILE_SIMULACIONES = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
FILE_GENOME = os.path.join(DATA_DIR, "loto_genome.json") # <--- NUEVA CONEXIÓN

TZ_CHILE = pytz.timezone('America/Santiago')

# --- DEFINICIÓN DE HORARIOS ESTRICTOS (REGLAS DE NEGOCIO) ---
# Días: 0=Lun, 1=Mar, 2=Mié, 3=Jue, 4=Vie, 5=Sáb, 6=Dom
HORARIOS = {
    "LOTO":   {"dias": [1, 3, 6],       "horas": [21]},
    "LOTO3":  {"dias": [0,1,2,3,4,5,6], "horas": [14, 18, 21]},
    "LOTO4":  {"dias": [0,1,2,3,4,5,6], "horas": [14, 21]},
    "RACHA":  {"dias": [0,1,2,3,4,5,6], "horas": [15, 22]}
}

# Configuración de Archivos y Algoritmos
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
    
    # 1. Obtener Ancla (Último dato real)
    try:
        if not os.path.exists(path): raise Exception("No CSV")
        df = pd.read_csv(path)
        if df.empty: raise Exception("CSV Vacío")
        
        last_row = df.iloc[-1]
        last_id = int(last_row['sorteo'])
        
        # Parseo robusto de fecha
        fecha_str = str(last_row['fecha']).replace('T', ' ').split('.')[0]
        try:
            # Intentar formato ISO primero
            last_date_naive = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
        except:
            # Fallback dd-mm-yyyy
            last_date_naive = datetime.strptime(fecha_str, "%d-%m-%Y %H:%M:%S")
            
        # Localizar a Chile
        cursor_tiempo = TZ_CHILE.localize(last_date_naive)
        cursor_id = last_id
        
    except:
        # Si no hay datos, asumimos sorteo #1 y empezamos a buscar desde ayer
        print(f"   ⚠️ Sin historial para {game_id}. Iniciando desde cero.")
        cursor_tiempo = ahora - timedelta(days=1)
        cursor_id = 0

    # 2. Simulación hacia el Futuro (Bridging the Gap)
    reglas = HORARIOS[game_id]
    safety_break = 0
    
    while cursor_tiempo <= ahora and safety_break < 1000:
        safety_break += 1
        encontrado_siguiente = False
        # Revisamos el día actual y el siguiente
        for dias_extra in [0, 1, 2, 3]: # Miramos hasta 3 días adelante
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
    """Carga el aprendizaje del pasado (Entrenador Cognitivo)"""
    if os.path.exists(FILE_GENOME):
        try:
            with open(FILE_GENOME, 'r') as f:
                return json.load(f)
        except: return None
    return None

def validar_cognitivamente(numeros, genoma, game_id):
    """
    Filtra predicciones basándose en el aprendizaje histórico.
    Retorna True si la jugada respeta el ADN ganador.
    """
    # Por ahora, el genoma es experto en LOTO clásico (suma y pares)
    # LOTO3 y LOTO4 tienen lógicas distintas, así que pasan siempre por ahora
    if game_id != "LOTO" or not genoma: return True
    
    try:
        morph = genoma.get('morphology', {})
        
        # 1. Filtro de Rango de Suma
        rango_suma = morph.get('ideal_sum_range')
        if rango_suma and isinstance(rango_suma, list):
            suma = sum(numeros)
            # Damos un pequeño margen de error (+- 5) al rango aprendido para no ser tan rígidos
            if suma < (rango_suma[0] - 5) or suma > (rango_suma[1] + 5):
                return False
        
        # 2. Filtro de Paridad (Opcional)
        ideal_pares = morph.get('ideal_even_count')
        if ideal_pares is not None and isinstance(ideal_pares, int):
            pares = len([n for n in numeros if n % 2 == 0])
            # Aceptamos si está a +1 o -1 de distancia del ideal
            if abs(pares - ideal_pares) > 1:
                return False
                
        return True
    except:
        return True

def soñar():
    print("💤 --- INICIANDO BOT SOÑADOR MULTIVERSO v11.0 (COGNITIVO) ---")
    
    ahora = datetime.now(TZ_CHILE)
    dia_semana = ahora.weekday()
    hora_actual = ahora.hour
    base_id = int(time.time())
    
    nuevas_filas = []
    pesos_voto = obtener_pesos_inteligentes()
    genoma = cargar_genoma() # <--- Cargamos Inteligencia

    if genoma:
        print("   🧠 Cortex cargado: El bot aplicará filtros de aprendizaje histórico.")
    
    for game_id, config in MULTIVERSO_CONFIG.items():
        print(f"🌌 Universo: {game_id}")
        
        # 1. Calcular Objetivo Inteligente
        objetivo = calcular_proximo_sorteo_real(game_id, config['csv'])
        print(f"   🎯 Objetivo Crononauta: #{objetivo}")

        # 2. Instanciar Cerebro
        try:
            forense = LotoForense(game_id=game_id, target_day=dia_semana)
        except Exception as e:
            print(f"❌ Error forense {game_id}: {e}")
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
                # --- AQUÍ OCURRE LA MAGIA COGNITIVA ---
                # Intentamos generar hasta 20 veces una jugada que respete el Genoma
                pred = funcion()
                intentos = 0
                max_intentos = 20 if game_id == "LOTO" else 1
                
                while intentos < max_intentos:
                    if validar_cognitivamente(pred, genoma, game_id):
                        break # La jugada es válida según la historia
                    pred = funcion() # Reintentar
                    intentos += 1
                
                # Guardamos la predicción (sea perfecta o "best effort")
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
                
                # Simulación Interna para Consenso (También aplicamos filtro aquí para purificar el consenso)
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
            n_bolas = forense.rules['n']
            ranking = sorted(bolsa_pesos_consenso, key=bolsa_pesos_consenso.get, reverse=True)
            top_consenso = sorted(ranking[:n_bolas])
            
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

    # Guardado
    if nuevas_filas:
        guardar(nuevas_filas)

def guardar(filas):
    cols = ['id', 'fecha_generacion', 'juego', 'numeros', 'sorteo_objetivo', 'estado', 'aciertos', 'score_afinidad', 'hora_dia', 'algoritmo']
    try:
        df_new = pd.DataFrame(filas)
        if os.path.exists(FILE_SIMULACIONES):
            df_old = pd.read_csv(FILE_SIMULACIONES)
            if 'juego' not in df_old.columns: df_old['juego'] = 'LOTO'
            df_final = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_final = df_new
        df_final.to_csv(FILE_SIMULACIONES, index=False, columns=cols)
        print(f"\n💾 Éxito: {len(filas)} jugadas guardadas.")
    except Exception as e:
        print(f"❌ Error Guardado: {e}")

if __name__ == "__main__":
    soñar()