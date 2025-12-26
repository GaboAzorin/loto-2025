import pandas as pd
import os
import time
from datetime import datetime, timedelta
import json
import sys

# --- GESTIÓN DE RUTAS ROBUSTA ---
# Calculamos la carpeta donde vive ESTE archivo (engine/models)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Agregamos esta carpeta al sistema para que encuentre a sus vecinos (Juez, Oráculo)
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Ahora importamos sin miedo
try:
    import juez_implacable
    import entrenador_cognitivo
    from oraculo_neural import OraculoNeural
except ImportError as e:
    print(f"❌ ERROR CRÍTICO EN RECONSTRUCTOR: No puedo importar mis dependencias.")
    print(f"   Detalle del error: {e}")
    # Relanzamos el error para que el Scraper sepa que algo grave pasó
    raise e 

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
GENOMA_FILE = os.path.join(DATA_DIR, "loto_genome.json")
SIMULACIONES_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")

# Definir qué archivos maestros leer
JUEGOS = {
    "LOTO3": "LOTO3_MAESTRO.csv",
    "RACHA": "RACHA_MAESTRO.csv",
    "LOTO":  "LOTO_HISTORIAL_MAESTRO.csv",
    "LOTO4": "LOTO4_MAESTRO.csv"
}

def obtener_ultimo_procesado(juego):
    if not os.path.exists(GENOMA_FILE): return 0
    try:
        with open(GENOMA_FILE, 'r') as f:
            data = json.load(f)
            return data.get("last_processed", {}).get(juego, 0)
    except: return 0

def obtener_punto_partida_inteligente(juego):
    """
    Busca cuál es la primera simulación registrada para este juego.
    Así evitamos recorrer 10 años de historia donde no jugamos nada.
    """
    if not os.path.exists(SIMULACIONES_FILE):
        return 0
    
    try:
        df = pd.read_csv(SIMULACIONES_FILE)
        # Filtramos por juego
        df_juego = df[df['juego'] == juego]
        
        if df_juego.empty:
            return 0
            
        # Encontramos el sorteo objetivo más antiguo que tenemos pendiente o auditado
        primer_sorteo_registrado = df_juego['sorteo_objetivo'].min()
        
        if pd.isna(primer_sorteo_registrado):
            return 0
            
        # Retornamos ese sorteo MENOS 10 (un buffer de seguridad para calentar motores)
        return int(primer_sorteo_registrado) - 10
        
    except Exception as e:
        print(f"⚠️ No se pudo calcular inicio inteligente: {e}")
        return 0

def reconstruir_linea_tiempo():
    print("⏳ INICIANDO RECONSTRUCCIÓN EXHAUSTIVA (MODO HOMOLOGACIÓN TOTAL)...")
    
    for juego, archivo in JUEGOS.items():
        path = os.path.join(DATA_DIR, archivo)
        if not os.path.exists(path): continue
        
        # 1. Leer sorteos reales disponibles
        df_real = pd.read_csv(path)
        if 'sorteo' not in df_real.columns: continue
        
        # Ordenar por sorteo (antiguo a nuevo) y RESETEAR INDICE para poder buscar el anterior por posición
        df_real = df_real.sort_values('sorteo', ascending=True).reset_index(drop=True)
        todos_sorteos = df_real['sorteo'].unique()
        
        # 2. LÓGICA DE SALTO TEMPORAL
        ultimo_procesado = obtener_ultimo_procesado(juego)
        inicio_simulaciones = obtener_punto_partida_inteligente(juego)
        
        # El punto de partida real es el MAYOR entre:
        # A) Donde quedamos la última vez (si ya procesamos cosas)
        # B) Donde empiezan mis simulaciones (para saltarnos la prehistoria)
        punto_corte = max(ultimo_procesado, inicio_simulaciones)
        
        # 3. Identificar sorteos "nuevos" (futuro no procesado)
        nuevos = [s for s in todos_sorteos if s > punto_corte]
        
        if not nuevos:
            # print(f"✅ {juego}: Todo al día.")
            continue
            
        print(f"\n🚀 {juego}: Detectados {len(nuevos)} sorteos nuevos.")
        print(f"   📅 Sincronizando desde sorteo #{min(nuevos)}...")
        
        # Instanciamos el oráculo para este juego
        oraculo = OraculoNeural(juego)

        # 4. BUCLE DE VIAJE EN EL TIEMPO
        for sorteo_actual in nuevos:
            print(f"   >>> Procesando Sorteo #{sorteo_actual}...", end=" ")

            # --- CÁLCULO DE FECHA SIMULADA (La lógica de los 5 minutos) ---
            # Buscamos la fila actual
            fila_actual_idx = df_real.index[df_real['sorteo'] == sorteo_actual].tolist()
            
            # Fecha por defecto (hoy) por si falla la lógica
            fecha_simulada = datetime.now()
            fecha_target_dt = datetime.now()

            if fila_actual_idx:
                idx = fila_actual_idx[0]
                
                # Obtener la fecha REAL del sorteo actual (para pasársela al Oráculo como target)
                fecha_target_str = df_real.iloc[idx]['fecha']
                try:
                    fecha_target_dt = datetime.strptime(fecha_target_str, '%Y-%m-%d %H:%M:%S')
                except: pass

                # Calcular fecha de generación (Sorteo Anterior + 5 min)
                if idx > 0:
                    fila_anterior = df_real.iloc[idx - 1]
                    fecha_anterior_str = fila_anterior['fecha']
                    try:
                        dt_anterior = datetime.strptime(fecha_anterior_str, '%Y-%m-%d %H:%M:%S')
                        fecha_simulada = dt_anterior + timedelta(minutes=5)
                    except ValueError:
                        pass 
            
            fecha_sim_str = fecha_simulada.strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{fecha_sim_str}]")
            # -------------------------------------------------------------
            
            # A. FASE JUEZ (Actualiza estados de apuestas pasadas)
            juez_implacable.juzgar() 
            
            # B. FASE ENTRENADOR (Actualiza heurísticos, pares, sumas)
            entrenador_cognitivo.analizar_adn_ganador(juego_filtro=juego, sorteo_limite=sorteo_actual)
            
            # C. FASE ORÁCULO NEURAL (LA LÓGICA QUE PIDES)
    
            # 1. Verificamos si ya existe una predicción del Oráculo para este sorteo
            df_sim = pd.read_csv(SIMULACIONES_FILE) if os.path.exists(SIMULACIONES_FILE) else pd.DataFrame()
            
            if not df_sim.empty and 'sorteo_objetivo' in df_sim.columns:
                # Buscamos si el oráculo ya opinó sobre este sorteo
                filtro = (df_sim['juego'] == juego) & \
                         (df_sim['sorteo_objetivo'] == sorteo_actual) & \
                         (df_sim['algoritmo'] == 'oraculo_neural_v3')
                
                if not df_sim[filtro].empty:
                    # Borramos la anterior para garantizar que sea la "pura" generada con Time Travel
                    df_sim = df_sim[~filtro] # Eliminamos la fila vieja
                    df_sim.to_csv(SIMULACIONES_FILE, index=False)
                    # print(f"      ♻️  Regenerando predicción...")

            # 2. Entrenamos el Oráculo VIAJANDO AL PASADO (Sorteo Limite = Sorteo Actual)
            # Esto asegura que el modelo NO vea los resultados del sorteo actual, solo los anteriores.
            oraculo.entrenar(sorteo_limite=sorteo_actual)
            
            # 3. Predecimos "el futuro"
            # Usamos la fecha target REAL para que el modelo sepa qué día de la semana es el objetivo
            prediccion = oraculo.predecir(fecha_objetivo=fecha_target_dt) 
            
            if prediccion:
                print(f"      🔮 Oráculo dice: {prediccion}")
                
                timestamp_simulado = int(fecha_simulada.timestamp())
                import random
                id_ficticio = int(f"{timestamp_simulado}{random.randint(10,99)}")

                # 4. Guardamos la simulación "correcta"
                nueva_fila = {
                    'id': id_ficticio,
                    'fecha_generacion': fecha_sim_str,
                    'juego': juego,
                    'numeros': str(prediccion),
                    'sorteo_objetivo': sorteo_actual,
                    'estado': 'PENDIENTE', 
                    'aciertos': 0,
                    'score_afinidad': 0.0,
                    'hora_dia': fecha_simulada.hour, # <--- HORA SIMULADA
                    'algoritmo': 'oraculo_neural_v3'
                }
                
                # Re-cargamos por si hubo cambios concurrentes (paranoia de programador)
                if os.path.exists(SIMULACIONES_FILE):
                    df_final = pd.read_csv(SIMULACIONES_FILE)
                    df_final = pd.concat([df_final, pd.DataFrame([nueva_fila])], ignore_index=True)
                else:
                    df_final = pd.DataFrame([nueva_fila])
                    
                df_final.to_csv(SIMULACIONES_FILE, index=False)
            
            # Pausa técnica mínima
            time.sleep(0.1)
            
    print("\n✨ RECONSTRUCCIÓN FINALIZADA. Todos los modelos están sincronizados al último sorteo.")

if __name__ == "__main__":
    reconstruir_linea_tiempo()