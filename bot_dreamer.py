import pandas as pd
import os
import pytz
from collections import Counter
from datetime import datetime, timedelta
from analizador_forense import LotoForense

# --- CONFIGURACIÓN ---
FILE_SIMULACIONES = "LOTO_SIMULACIONES.csv"
FILE_MAESTRO = "LOTO_HISTORIAL_MAESTRO.csv"
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
    print("💤 --- INICIANDO BOT SOÑADOR PENTA-MODELO (CONSENSO ROBUSTO) v6.1 ---")
    
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

    # 1. GENERACIÓN INDIVIDUAL (4 Filas)
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
    print("🗳️  Iniciando votación masiva (10 rondas por algoritmo)...")
    super_bolsa_votos = []
    
    try:
        # Hacemos 10 pasadas por cada uno de los 4 algoritmos
        for _, funcion_generadora in algoritmos:
            for _ in range(10):
                try:
                    # Generamos predicción interna (no se guarda en CSV, solo suma votos)
                    voto = funcion_generadora()
                    super_bolsa_votos.extend(voto)
                except: pass
        
        # Contar frecuencia de cada número en la super bolsa (Total ~240 números)
        conteo = Counter(super_bolsa_votos)
        comunes = conteo.most_common(6)
        numeros_consenso = sorted([num for num, freq in comunes])
        
        # Relleno de seguridad si no hay suficientes números (muy raro con 40 rondas)
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
        print(f"🤝 CONSENSO ROBUSTO (40 rondas): {numeros_consenso}")

    except Exception as e:
        print(f"❌ Error generando consenso: {e}")

    # 3. Guardar Todo
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