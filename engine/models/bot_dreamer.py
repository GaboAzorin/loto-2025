import pandas as pd
import os
import pytz
import time
from datetime import datetime

# Importamos el cerebro polimórfico
from analizador_forense import LotoForense 

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
FILE_SIMULACIONES = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")

TZ_CHILE = pytz.timezone('America/Santiago')

# Días de sorteo principales (Martes=1, Jueves=3, Domingo=6)
DIAS_SORTEO_LOTO = [1, 3, 6] 
HORA_CIERRE = 21 

# Configuración del Multiverso
MULTIVERSO_CONFIG = {
    "LOTO":   {"csv": "LOTO_HISTORIAL_MAESTRO.csv", "algos_extra": True, "dias": DIAS_SORTEO_LOTO},
    "LOTO3":  {"csv": "LOTO3_MAESTRO.csv",          "algos_extra": False, "dias": [0,1,2,3,4,5,6]}, 
    "LOTO4":  {"csv": "LOTO4_MAESTRO.csv",          "algos_extra": False, "dias": [0,1,2,3,4,5,6]}, 
    "RACHA":  {"csv": "RACHA_MAESTRO.csv",          "algos_extra": False, "dias": [0,1,2,3,4,5,6]}  
}

def calcular_sorteo_objetivo(csv_name, dias_juego):
    """Calcula el ID del próximo sorteo evitando los ya cerrados."""
    path = os.path.join(DATA_DIR, csv_name)
    ahora = datetime.now(TZ_CHILE)
    
    ultimo_id = 0
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            if not df.empty: ultimo_id = int(df['sorteo'].max())
        except: pass
    
    if ultimo_id == 0: return 1

    # Si es día de sorteo y ya pasó la hora, el "próximo" no es mañana, es el subsiguiente
    # (Asumiendo que el scraper aún no baja el de hoy)
    es_dia_sorteo = ahora.weekday() in dias_juego
    paso_hora = ahora.hour >= HORA_CIERRE
    
    if es_dia_sorteo and paso_hora:
        return ultimo_id + 2
        
    return ultimo_id + 1

def obtener_pesos_inteligentes():
    """Feedback Loop: Ajusta el peso del voto según aciertos pasados."""
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
                        # Normalización: 50% score = peso 1.0. 
                        pesos[key] = max(0.2, score / 50.0)
        except: pass
    return pesos

def soñar():
    print("💤 --- INICIANDO BOT SOÑADOR MULTIVERSO (LITE) ---")
    
    ahora = datetime.now(TZ_CHILE)
    dia_semana = ahora.weekday()
    hora_actual = ahora.hour
    base_id = int(time.time())
    
    nuevas_filas = []
    pesos_voto = obtener_pesos_inteligentes()
    
    for game_id, config in MULTIVERSO_CONFIG.items():
        print(f"🌌 Procesando Universo: {game_id}")
        
        try:
            forense = LotoForense(game_id=game_id, target_day=dia_semana)
        except Exception as e:
            print(f"❌ Error forense {game_id}: {e}")
            continue

        objetivo = calcular_sorteo_objetivo(config['csv'], config['dias'])

        # --- DEFINICIÓN DE ALGORITMOS ---
        mis_algoritmos = [('forense_biometrico', forense.predict_weighted)]
        if config['algos_extra']:
            mis_algoritmos.extend([
                ('gaussiano_tactico', forense.predict_gaussian),
                ('delta_tactico',     forense.predict_delta),
                ('markov_chain',      forense.predict_markov)
            ])

        # --- EJECUCIÓN ---
        bolsa_pesos_consenso = {} 

        for i, (nombre, funcion) in enumerate(mis_algoritmos):
            try:
                # 1. Generación Unitaria
                pred = funcion()
                
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
                print(f"   🤖 {nombre}: {pred}")

                # 2. Aporte al Consenso (5 rondas internas)
                peso = pesos_voto.get(nombre.split('_')[0], 1.0)
                for _ in range(5):
                    sim = funcion()
                    for num in sim:
                        bolsa_pesos_consenso[num] = bolsa_pesos_consenso.get(num, 0) + peso

            except Exception as e:
                print(f"   ⚠️ Error en {nombre}: {e}")

        # --- GENERAR CONSENSO MERITOCRÁTICO ---
        try:
            n_bolas = forense.rules['n']
            ranking = sorted(bolsa_pesos_consenso, key=bolsa_pesos_consenso.get, reverse=True)
            top_consenso = sorted(ranking[:n_bolas])
            
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