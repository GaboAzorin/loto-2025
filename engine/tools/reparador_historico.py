import pandas as pd
import os
import sys
import time
from datetime import datetime, timedelta

# --- GESTIÓN DE RUTAS (INTELIGENTE) ---
# Calculamos la carpeta actual (engine/tools)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Agregamos la carpeta de modelos al path (engine/models)
# Asumiendo que estamos en engine/tools, subimos uno (..) y entramos a models
sys.path.append(os.path.join(current_dir, '..', 'models')) 
# Respaldo por si lo guardas en engine/scrapers
sys.path.append(os.path.join(current_dir, '..', '..', 'engine', 'models'))

try:
    from oraculo_neural import OraculoNeural
except ImportError:
    print("❌ Error Crítico: No encuentro 'oraculo_neural.py'.")
    print("   Asegúrate de guardar este script en 'engine/tools/' o ajustar las rutas.")
    sys.exit(1)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ajustamos para llegar a la raíz del proyecto desde engine/tools
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
    if not os.path.exists(SIMULACIONES_FILE):
        return None
    
    try:
        df = pd.read_csv(SIMULACIONES_FILE)
        # Filtramos por Juego y por Algoritmo Neural
        filtro = (df['juego'] == juego) & (df['algoritmo'] == 'oraculo_neural_v3')
        datos_neural = df[filtro]
        
        if datos_neural.empty:
            return None
        
        # El sorteo más antiguo que intentó predecir
        min_sorteo = datos_neural['sorteo_objetivo'].min()
        return int(min_sorteo)
    except Exception:
        return None

def reparar_historia_inteligente(juego):
    print(f"\n🛠️  INICIANDO REPARACIÓN DE LÍNEA TEMPORAL: {juego}")
    print(f"    (Modo: Determinista + Regla de los 5 minutos + ID Retroactivo)")
    
    # 1. Detectar inicio automáticamente
    sorteo_inicio = encontrar_punto_partida(juego)
    
    if sorteo_inicio is None:
        print(f"⚠️ No encontré historial previo del Oráculo para {juego}.")
        print("   Se requiere al menos una predicción existente para saber desde dónde reparar.")
        return

    print(f"    📍 Punto de partida detectado: Sorteo #{sorteo_inicio}")
    
    # 2. Cargar Maestro
    archivo_maestro = os.path.join(DATA_DIR, MAESTROS[juego])
    if not os.path.exists(archivo_maestro):
        print(f"❌ No encuentro el maestro de {juego}")
        return

    df_maestro = pd.read_csv(archivo_maestro)
    
    # Ordenar y resetear índice es CRUCIAL para buscar el "anterior"
    df_maestro = df_maestro.sort_values('sorteo', ascending=True).reset_index(drop=True)
    
    # Filtramos los sorteos que ocurrieron DESPUÉS o IGUAL al inicio
    # Estos son los que vamos a regenerar
    sorteos_a_reparar = sorted(df_maestro[df_maestro['sorteo'] >= sorteo_inicio]['sorteo'].unique())
    
    total = len(sorteos_a_reparar)
    print(f"    📅 Se reconstruirán {total} sorteos.")

    # Instanciamos el oráculo
    oraculo = OraculoNeural(juego)

    # 3. Bucle de Reparación Cronológica
    for i, sorteo_target in enumerate(sorteos_a_reparar):
        progreso = f"[{i+1}/{total}]"
        
        # --- CÁLCULO DE FECHA SIMULADA (REGLA 5 MINUTOS) ---
        idx_target_list = df_maestro.index[df_maestro['sorteo'] == sorteo_target].tolist()
        
        fecha_simulada = datetime.now() # Fallback
        fecha_target_dt = datetime.now() # Fallback para el predecir
        
        if idx_target_list:
            idx = idx_target_list[0]
            
            # Obtener fecha real del objetivo (para pasársela al modelo y sepa si es martes/jueves)
            fecha_target_str = df_maestro.iloc[idx]['fecha']
            try:
                fecha_target_dt = datetime.strptime(fecha_target_str, '%Y-%m-%d %H:%M:%S')
            except: pass

            # Obtener fecha del sorteo ANTERIOR para simular la generación
            if idx > 0:
                fila_anterior = df_maestro.iloc[idx - 1]
                fecha_anterior_str = fila_anterior['fecha']
                try:
                    dt_anterior = datetime.strptime(fecha_anterior_str, '%Y-%m-%d %H:%M:%S')
                    # REGLA DE ORO: 5 minutos después del sorteo anterior
                    fecha_simulada = dt_anterior + timedelta(minutes=5)
                except ValueError:
                    pass
            else:
                # Si es el primerísimo sorteo del archivo (raro), restamos días arbitrarios
                fecha_simulada = fecha_target_dt - timedelta(days=2) 

        fecha_sim_str = fecha_simulada.strftime('%Y-%m-%d %H:%M:%S')
        
        # --- AJUSTE DE ID RETROACTIVO ---
        # Usamos el timestamp de la fecha simulada en lugar de time.time()
        # Esto ordena cronológicamente los IDs en el CSV
        id_retroactivo = int(fecha_simulada.timestamp())

        # ---------------------------------------------------
        
        # A. BORRAR PREDICCIÓN ANTIGUA (Limpieza quirúrgica)
        if os.path.exists(SIMULACIONES_FILE):
            df_sim = pd.read_csv(SIMULACIONES_FILE)
            filtro_borrar = (
                (df_sim['juego'] == juego) & 
                (df_sim['sorteo_objetivo'] == sorteo_target) & 
                (df_sim['algoritmo'] == 'oraculo_neural_v3')
            )
            count_borrar = df_sim[filtro_borrar].shape[0]
            if count_borrar > 0:
                df_sim = df_sim[~filtro_borrar]
                df_sim.to_csv(SIMULACIONES_FILE, index=False)
                # print(f"      🗑️  Eliminadas {count_borrar} entradas previas.")
        
        # B. ENTRENAMIENTO "TIME TRAVEL"
        print(f"{progreso} ⏳ Reconstruyendo #{sorteo_target} (Fecha Sim: {fecha_sim_str})...", end=" ")
        
        try:
            # Entrena SOLO con datos anteriores al target
            oraculo.entrenar(sorteo_limite=sorteo_target)
            
            # C. PREDICCIÓN DETERMINISTA
            # Usamos fecha_target_dt para que el modelo sepa el día de la semana correcto
            prediccion = oraculo.predecir(fecha_objetivo=fecha_target_dt)
            
            if prediccion:
                print(f"✅ Pred: {prediccion}")
                
                # D. GUARDAR RESULTADO
                nueva_fila = {
                    'id': id_retroactivo, # <--- ID CORREGIDO
                    'fecha_generacion': fecha_sim_str, # <--- LA FECHA CALCULADA (Pasado)
                    'juego': juego,
                    'numeros': str(prediccion),
                    'sorteo_objetivo': sorteo_target,
                    'estado': 'PENDIENTE', 
                    'aciertos': 0,
                    'score_afinidad': 0.0,
                    'hora_dia': fecha_simulada.hour, # <--- LA HORA CALCULADA
                    'algoritmo': 'oraculo_neural_v3'
                }
                
                # Append seguro
                if os.path.exists(SIMULACIONES_FILE):
                    df_final = pd.read_csv(SIMULACIONES_FILE)
                    df_final = pd.concat([df_final, pd.DataFrame([nueva_fila])], ignore_index=True)
                else:
                    df_final = pd.DataFrame([nueva_fila])
                
                df_final.to_csv(SIMULACIONES_FILE, index=False)
            else:
                print("⚠️ Sin predicción.")

        except Exception as e:
            print(f"\n      ❌ Error procesando {sorteo_target}: {e}")
            # time.sleep(1) # Pausa breve en caso de error

    print(f"\n✨ REPARACIÓN DE {juego} COMPLETADA EXITOSAMENTE.")

if __name__ == "__main__":
    # --- ZONA DE CONTROL MANUAL ---
    
    # CAMBIA ESTO SEGÚN LO QUE QUIERAS ARREGLAR
    # JUEGOS DISPONIBLES: "LOTO", "LOTO3", "LOTO4", "RACHA"
    
    JUEGO_A_REPARAR = "RACHA" 
    
    reparar_historia_inteligente(JUEGO_A_REPARAR)