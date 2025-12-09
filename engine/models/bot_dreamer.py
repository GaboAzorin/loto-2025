import pandas as pd
import os
import pytz
import ast
from collections import Counter
from datetime import datetime, timedelta
# Nota: Asegúrate de que la importación de analizador_forense funcione. 
# Si están en la misma carpeta engine/, esto está bien:
from analizador_forense import LotoForense 

# --- CONFIGURACIÓN DE RUTAS ROBÚSTA ---
# 1. Obtenemos la ruta de ESTE archivo (bot_dreamer.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 2. Asumimos que data/ está al mismo nivel que la carpeta engine/ (es decir, subimos un nivel)
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')

# 3. Construimos las rutas finales
FILE_SIMULACIONES = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
FILE_MAESTRO = os.path.join(DATA_DIR, "LOTO_HISTORIAL_MAESTRO.csv")

TZ_CHILE = pytz.timezone('America/Santiago')

# Días de sorteo: Martes (1), Jueves (3), Domingo (6)
DIAS_SORTEO = [1, 3, 6] 
HORA_CIERRE_SORTEO = 21 

def calcular_sorteo_real(df_maestro):
    """
    Calcula el ID del próximo sorteo REAL.
    Versión Blindada v3.1: Usa Pandas para parsear fechas y maneja mejor los saltos.
    """
    ahora = datetime.now(TZ_CHILE)
    print(f"🕒 [DEBUG] Hora Bot (Chile): {ahora}") 
    
    try:
        # 1. Obtener datos del último sorteo con PANDAS
        ultimo_row = df_maestro.iloc[-1]
        ultimo_id = int(ultimo_row['sorteo'])
        
        # Pandas detecta automáticamente si es YYYY-MM-DD o DD-MM-YYYY
        fecha_dt = pd.to_datetime(ultimo_row['fecha'], dayfirst=True)
        
        # Convertir a datetime de Python y asignar zona horaria
        ultima_fecha = fecha_dt.to_pydatetime()
        if ultima_fecha.tzinfo is None:
            ultima_fecha = TZ_CHILE.localize(ultima_fecha)
        else:
            ultima_fecha = ultima_fecha.astimezone(TZ_CHILE)
            
        print(f"📅 [DEBUG] Último sorteo leído: #{ultimo_id} fecha: {ultima_fecha}") 

    except Exception as e:
        print(f"⚠️ Error crítico leyendo fechas del maestro: {e}")
        # FALLBACK
        max_id = int(df_maestro['sorteo'].max())
        if ahora.hour >= 21 and ahora.weekday() in DIAS_SORTEO:
             return max_id + 2 
        return max_id + 1

    # 2. Algoritmo de Viaje en el Tiempo
    simulacion_fecha = ultima_fecha
    sorteo_virtual_id = ultimo_id
    
    dias_simulados = 0
    while dias_simulados < 30: 
        dias_simulados += 1
        simulacion_fecha += timedelta(days=1)
        
        cierre_sorteo = simulacion_fecha.replace(hour=HORA_CIERRE_SORTEO, minute=0, second=0, microsecond=0)
        
        if simulacion_fecha.weekday() in DIAS_SORTEO:
            sorteo_virtual_id += 1
            if ahora < cierre_sorteo:
                print(f"✅ [TARGET] Objetivo fijado: #{sorteo_virtual_id} (Cierra: {cierre_sorteo})") 
                return sorteo_virtual_id
            print(f"⏭️ [SKIP] El sorteo #{sorteo_virtual_id} ya cerró. Buscando siguiente...") 
    
    return ultimo_id + 1

def soñar():
    print("💤 --- INICIANDO BOT SOÑADOR PENTA-MODELO (CARTA MAESTRA) v7.0 ---")
    
    try:
        forense = LotoForense(FILE_MAESTRO)
    except Exception as e:
        print(f"❌ Error fatal iniciando forense: {e}")
        return

    try:
        if os.path.exists(FILE_MAESTRO):
            df_maestro = pd.read_csv(FILE_MAESTRO)
            proximo_sorteo = calcular_sorteo_real(df_maestro)
        else:
            print("⚠️ No existe archivo maestro. Iniciando en 1.")
            proximo_sorteo = 1
    except Exception as e:
        print(f"❌ Error general fechas: {e}")
        proximo_sorteo = 0

    print(f"🎯 Sorteo Objetivo Calculado: {proximo_sorteo}")

    nuevas_filas = []
    ahora = datetime.now(TZ_CHILE)
    base_id = int(ahora.timestamp())

    # --- DEFINICIÓN DE LOS 4 GLADIADORES ---
    algoritmos = [
        ('forense_biometrico_v1', lambda: forense.predict_numbers("LOTO", n=6)),
        ('gaussiano_tactico_v1', lambda: forense.predict_gaussian(n=6)),
        ('delta_tactico_v1', lambda: forense.predict_delta(n=6)),
        ('markov_chain_v1', lambda: forense.predict_markov(n=6))
    ]

    # 1. GENERACIÓN INDIVIDUAL (4 Filas Estándar)
    for idx, (nombre_algo, funcion_generadora) in enumerate(algoritmos):
        try:
            numeros_predichos = funcion_generadora()
            numeros_fmt = str(numeros_predichos)
            
            nuevas_filas.append({
                'id': base_id + idx, 
                'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
                'numeros': numeros_fmt,
                'sorteo_objetivo': proximo_sorteo,
                'estado': 'PENDIENTE',
                'aciertos': 0,
                'score_afinidad': 0.0,
                'hora_dia': ahora.hour,
                'algoritmo': nombre_algo
            })
            print(f"🤖 {nombre_algo}: {numeros_fmt}")
            
        except Exception as e:
            print(f"❌ Error en {nombre_algo}: {e}")
    
    # 2. GENERACIÓN DE CONSENSO ROBUSTO (40 Simulaciones Internas)
    # Se ejecuta SIEMPRE para mantener el pulso cada 15 min
    print("🗳️  Iniciando votación masiva (10 rondas por algoritmo)...")
    super_bolsa_votos = []
    
    try:
        for _, funcion_generadora in algoritmos:
            for _ in range(10):
                try:
                    voto = funcion_generadora()
                    super_bolsa_votos.extend(voto)
                except: pass
        
        conteo = Counter(super_bolsa_votos)
        comunes = conteo.most_common(6)
        numeros_consenso = sorted([num for num, freq in comunes])
        
        if len(numeros_consenso) < 6:
            faltantes = 6 - len(numeros_consenso)
            extras = forense.predict_numbers("LOTO", n=6)
            for n in extras:
                if n not in numeros_consenso:
                    numeros_consenso.append(n)
                if len(numeros_consenso) == 6: break
            numeros_consenso.sort()

        nuevas_filas.append({
            'id': base_id + 99, 
            'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
            'numeros': str(numeros_consenso),
            'sorteo_objetivo': proximo_sorteo,
            'estado': 'PENDIENTE',
            'aciertos': 0,
            'score_afinidad': 0.0,
            'hora_dia': ahora.hour,
            'algoritmo': 'consenso_v1'
        })
        print(f"🤝 CONSENSO ROBUSTO: {numeros_consenso}")

    except Exception as e:
        print(f"❌ Error generando consenso: {e}")

    # 3. PROTOCOLO CARTA MAESTRA (PREMIUM)
    # Solo se ejecuta los días de sorteo entre las 20:00 y 21:00
    if ahora.weekday() in DIAS_SORTEO and ahora.hour == 20:
        print("🌟 [GOLDEN HOUR] INICIANDO CÁLCULO DE CARTA MAESTRA PREMIUM...")
        try:
            if os.path.exists(FILE_SIMULACIONES):
                df_hist = pd.read_csv(FILE_SIMULACIONES)
                
                # Filtrar SOLO las predicciones hechas para este sorteo específico
                df_target = df_hist[df_hist['sorteo_objetivo'] == proximo_sorteo]
                
                if not df_target.empty:
                    bolsa_historica = []
                    # Recolectar números de TODAS las filas (incluidas las que acabamos de generar pero no guardado aún, 
                    # aunque para simplificar leemos lo guardado y sumamos lo nuevo en memoria si quisiéramos, 
                    # pero leer el CSV es más seguro para obtener el "bulk" histórico)
                    
                    for nums_str in df_target['numeros']:
                        try:
                            n_list = ast.literal_eval(nums_str)
                            bolsa_historica.extend(n_list)
                        except: pass
                    
                    # Sumar también los de la sesión actual para tener la info más fresca
                    bolsa_historica.extend(super_bolsa_votos) 
                    
                    if bolsa_historica:
                        conteo_master = Counter(bolsa_historica)
                        comunes_master = conteo_master.most_common(6)
                        nums_master = sorted([num for num, freq in comunes_master])
                        
                        # Relleno de seguridad
                        while len(nums_master) < 6:
                            extra = forense.predict_numbers("LOTO", n=1)[0]
                            if extra not in nums_master: nums_master.append(extra)
                        nums_master.sort()

                        nuevas_filas.append({
                            'id': base_id + 777, # ID Jackpot
                            'fecha_generacion': ahora.strftime('%Y-%m-%d %H:%M:%S'),
                            'numeros': str(nums_master),
                            'sorteo_objetivo': proximo_sorteo,
                            'estado': 'PENDIENTE',
                            'aciertos': 0,
                            'score_afinidad': 0.0,
                            'hora_dia': ahora.hour,
                            'algoritmo': 'MASTER_PREMIUM_v1'
                        })
                        print(f"🏆 CARTA MAESTRA GENERADA: {nums_master}")
        except Exception as e:
            print(f"❌ Error en Carta Maestra: {e}")

    # 4. Guardar Todo
    if nuevas_filas:
        try:
            if os.path.exists(FILE_SIMULACIONES):
                df_sim = pd.read_csv(FILE_SIMULACIONES)
                df_new = pd.DataFrame(nuevas_filas)
                df_sim = pd.concat([df_sim, df_new], ignore_index=True)
            else:
                df_sim = pd.DataFrame(nuevas_filas)
                
            df_sim.to_csv(FILE_SIMULACIONES, index=False)
            print(f"✨ ÉXITO: {len(nuevas_filas)} predicciones guardadas.")
            
        except Exception as e:
            print(f"❌ Error guardando CSV: {e}")

if __name__ == "__main__":
    soñar()