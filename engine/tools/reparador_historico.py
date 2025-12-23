import pandas as pd
import os
import sys
import time
from datetime import datetime, timedelta

# --- GESTIÓN DE RUTAS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, '..', 'models')) 
sys.path.append(os.path.join(current_dir, '..', '..', 'engine', 'models'))

try:
    from oraculo_neural import OraculoNeural
except ImportError:
    print("❌ Error Crítico: No encuentro 'oraculo_neural.py'.")
    sys.exit(1)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data') 
SIMULACIONES_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")

MAESTROS = {
    "LOTO": "LOTO_HISTORIAL_MAESTRO.csv",
    "LOTO3": "LOTO3_MAESTRO.csv",
    "LOTO4": "LOTO4_MAESTRO.csv",
    "RACHA": "RACHA_MAESTRO.csv"
}

def encontrar_punto_partida(juego):
    """Busca la primera vez que el Oráculo Neural intentó predecir algo en la historia."""
    if not os.path.exists(SIMULACIONES_FILE): return None
    try:
        df = pd.read_csv(SIMULACIONES_FILE)
        filtro = (df['juego'] == juego) & (df['algoritmo'] == 'oraculo_neural_v3')
        datos_neural = df[filtro]
        if datos_neural.empty: return None
        return int(datos_neural['sorteo_objetivo'].min())
    except: return None

def guardar_prediccion(fila_dict):
    """Guarda la fila y ORDENA el CSV cronológicamente por ID."""
    if os.path.exists(SIMULACIONES_FILE):
        df_final = pd.read_csv(SIMULACIONES_FILE)
        # Concatenamos la nueva fila
        df_final = pd.concat([df_final, pd.DataFrame([fila_dict])], ignore_index=True)
    else:
        df_final = pd.DataFrame([fila_dict])
    
    # --- LA MAGIA DEL ORDENAMIENTO ---
    # Convertimos ID a numérico por si acaso y ordenamos
    df_final['id'] = pd.to_numeric(df_final['id'], errors='coerce')
    df_final = df_final.sort_values(by='id', ascending=True)
    # ---------------------------------

    df_final.to_csv(SIMULACIONES_FILE, index=False)

def reparar_historia_inteligente(juego):
    print(f"\n🛠️  INICIANDO REPARACIÓN DE LÍNEA TEMPORAL: {juego}")
    
    sorteo_inicio = encontrar_punto_partida(juego)
    if sorteo_inicio is None:
        print(f"⚠️ No hay historial previo para {juego}. Saltando directo al futuro.")
        sorteo_inicio = 9999999 

    archivo_maestro = os.path.join(DATA_DIR, MAESTROS[juego])
    if not os.path.exists(archivo_maestro): return

    df_maestro = pd.read_csv(archivo_maestro)
    df_maestro = df_maestro.sort_values('sorteo', ascending=True).reset_index(drop=True)
    
    # === FASE 1: REPARAR EL PASADO ===
    sorteos_a_reparar = sorted(df_maestro[df_maestro['sorteo'] >= sorteo_inicio]['sorteo'].unique())
    total = len(sorteos_a_reparar)
    
    oraculo = OraculoNeural(juego)
    
    if total > 0:
        print(f"    📅 Se reconstruirán {total} sorteos históricos.")
        for i, sorteo_target in enumerate(sorteos_a_reparar):
            progreso = f"[{i+1}/{total}]"
            
            # Cálculo de fecha simulada (5 mins después del anterior)
            idx_list = df_maestro.index[df_maestro['sorteo'] == sorteo_target].tolist()
            fecha_simulada = datetime.now()
            fecha_target_dt = datetime.now()
            
            if idx_list:
                idx = idx_list[0]
                try: fecha_target_dt = datetime.strptime(df_maestro.iloc[idx]['fecha'], '%Y-%m-%d %H:%M:%S')
                except: pass

                if idx > 0:
                    try:
                        dt_anterior = datetime.strptime(df_maestro.iloc[idx-1]['fecha'], '%Y-%m-%d %H:%M:%S')
                        fecha_simulada = dt_anterior + timedelta(minutes=5)
                    except: pass
                else:
                    fecha_simulada = fecha_target_dt - timedelta(days=2)

            fecha_sim_str = fecha_simulada.strftime('%Y-%m-%d %H:%M:%S')
            
            # ID Retroactivo basado en la fecha simulada
            id_retroactivo = int(fecha_simulada.timestamp())

            # Borrar anterior
            if os.path.exists(SIMULACIONES_FILE):
                df_sim = pd.read_csv(SIMULACIONES_FILE)
                filtro_borrar = (df_sim['juego'] == juego) & (df_sim['sorteo_objetivo'] == sorteo_target) & (df_sim['algoritmo'] == 'oraculo_neural_v3')
                if not df_sim[filtro_borrar].empty:
                    df_sim = df_sim[~filtro_borrar]
                    df_sim.to_csv(SIMULACIONES_FILE, index=False)
            
            # Predecir
            print(f"{progreso} ⏳ Reconstruyendo #{sorteo_target} (Fecha Sim: {fecha_sim_str})...", end=" ")
            try:
                oraculo.entrenar(sorteo_limite=sorteo_target)
                prediccion = oraculo.predecir(fecha_objetivo=fecha_target_dt)
                if prediccion:
                    print(f"✅ Pred: {prediccion}")
                    guardar_prediccion({
                        'id': id_retroactivo, # Se guardará en su posición correcta por fecha
                        'fecha_generacion': fecha_sim_str,
                        'juego': juego,
                        'numeros': str(prediccion),
                        'sorteo_objetivo': sorteo_target,
                        'estado': 'PENDIENTE', 
                        'aciertos': 0, 'score_afinidad': 0.0,
                        'hora_dia': fecha_simulada.hour,
                        'algoritmo': 'oraculo_neural_v3'
                    })
                else: print("⚠️ Sin predicción.")
            except Exception as e: print(f"❌ Error: {e}")

    # === FASE 2: PREDECIR EL FUTURO ===
    print(f"\n🚀 PROYECTANDO EL PRÓXIMO SORTEO (FUTURO INMEDIATO)...")
    
    if not df_maestro.empty:
        ultimo_sorteo_real = df_maestro.iloc[-1]
        id_ultimo = int(ultimo_sorteo_real['sorteo'])
        fecha_ultimo_str = ultimo_sorteo_real['fecha']
        
        sorteo_futuro = id_ultimo + 1
        
        try:
            dt_ultimo = datetime.strptime(fecha_ultimo_str, '%Y-%m-%d %H:%M:%S')
            fecha_gen_futura = dt_ultimo + timedelta(minutes=5)
        except:
            fecha_gen_futura = datetime.now()
            
        fecha_gen_str = fecha_gen_futura.strftime('%Y-%m-%d %H:%M:%S')
        id_futuro = int(fecha_gen_futura.timestamp())
        
        print(f"    🎯 Objetivo: Sorteo #{sorteo_futuro}")
        print(f"    🕒 Momento de Simulación: {fecha_gen_str}")

        # Limpieza preventiva
        if os.path.exists(SIMULACIONES_FILE):
            df_sim = pd.read_csv(SIMULACIONES_FILE)
            filtro_borrar = (df_sim['juego'] == juego) & (df_sim['sorteo_objetivo'] == sorteo_futuro) & (df_sim['algoritmo'] == 'oraculo_neural_v3')
            if not df_sim[filtro_borrar].empty:
                df_sim = df_sim[~filtro_borrar]
                df_sim.to_csv(SIMULACIONES_FILE, index=False)

        print(f"    🧠 Entrenando con toda la historia disponible...")
        try:
            oraculo.entrenar(sorteo_limite=sorteo_futuro)
            prediccion_futura = oraculo.predecir(fecha_objetivo=datetime.now())
            
            if prediccion_futura:
                print(f"    🔮 PREDICCIÓN PARA JUGAR AHORA (#{sorteo_futuro}): {prediccion_futura}")
                guardar_prediccion({
                    'id': id_futuro,
                    'fecha_generacion': fecha_gen_str,
                    'juego': juego,
                    'numeros': str(prediccion_futura),
                    'sorteo_objetivo': sorteo_futuro,
                    'estado': 'PENDIENTE', 
                    'aciertos': 0, 'score_afinidad': 0.0,
                    'hora_dia': fecha_gen_futura.hour,
                    'algoritmo': 'oraculo_neural_v3'
                })
                print("    ✅ Guardada y ordenada en el CSV.")
            else:
                print("    ⚠️ El oráculo no habló.")
        except Exception as e:
            print(f"    ❌ Error en el futuro: {e}")

    print(f"\n✨ PROCESO TERMINADO.")

if __name__ == "__main__":
    # CONFIGURACIÓN
    JUEGO_A_REPARAR = "LOTO3"
    
    reparar_historia_inteligente(JUEGO_A_REPARAR)