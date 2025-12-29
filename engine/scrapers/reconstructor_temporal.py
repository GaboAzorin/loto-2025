import pandas as pd
import os
import time
from datetime import datetime, timedelta
import json
import sys

# --- GESTIÓN DE RUTAS ROBUSTA ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Importamos sin miedo
try:
    import juez_implacable
    import entrenador_cognitivo
    # OJO: OraculoNeural es opcional, si no está, el script no muere, pero avisa.
    try:
        from oraculo_neural import OraculoNeural
    except ImportError:
        OraculoNeural = None
        print("⚠️ Advertencia: OraculoNeural no encontrado. El Time Travel será limitado.")

except ImportError as e:
    print(f"❌ ERROR CRÍTICO EN RECONSTRUCTOR: No puedo importar mis dependencias.")
    raise e 

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
GENOMA_FILE = os.path.join(DATA_DIR, "loto_genome.json")
SIMULACIONES_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")

# Mapeo de archivos maestros
JUEGOS = {
    "LOTO3": "LOTO3_MAESTRO.csv",
    "RACHA": "RACHA_MAESTRO.csv",
    "LOTO":  "LOTO_HISTORIAL_MAESTRO.csv",
    "LOTO4": "LOTO4_MAESTRO.csv"
}

def obtener_ultimo_procesado(juego):
    """Busca en el genoma hasta qué sorteo ya hemos 'viajado'."""
    if not os.path.exists(GENOMA_FILE): return 0
    try:
        with open(GENOMA_FILE, 'r') as f:
            data = json.load(f)
            # Usamos un campo específico para tracking de reconstrucción
            return data.get("last_processed", {}).get(juego, 0)
    except: return 0

def actualizar_ultimo_procesado(juego, sorteo_id):
    """Guarda en el genoma que ya procesamos este hito temporal."""
    data = {}
    if os.path.exists(GENOMA_FILE):
        try:
            with open(GENOMA_FILE, 'r') as f: data = json.load(f)
        except: pass
    
    if "last_processed" not in data: data["last_processed"] = {}
    data["last_processed"][juego] = int(sorteo_id)
    
    with open(GENOMA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def reconstruir_linea_tiempo():
    print("⏳ INICIANDO RECONSTRUCCIÓN EXHAUSTIVA (MODO HOMOLOGACIÓN TOTAL)...")
    
    for juego, archivo in JUEGOS.items():
        path = os.path.join(DATA_DIR, archivo)
        if not os.path.exists(path): continue
        
        # 1. Leer historia real
        df_real = pd.read_csv(path)
        if 'sorteo' not in df_real.columns: continue
        
        # Ordenar cronológicamente
        df_real = df_real.sort_values('sorteo', ascending=True).reset_index(drop=True)
        todos_sorteos = df_real['sorteo'].unique()
        
        # 2. Determinar punto de partida
        ultimo_procesado = obtener_ultimo_procesado(juego)
        
        # Filtramos solo lo nuevo
        nuevos = [s for s in todos_sorteos if s > ultimo_procesado]
        
        if not nuevos:
            continue
            
        print(f"\n🚀 {juego}: Detectados {len(nuevos)} sorteos nuevos para reconstruir.")
        print(f"   📅 Sincronizando desde sorteo #{min(nuevos)}...")
        
        # Instanciamos el oráculo si existe
        oraculo = OraculoNeural(juego) if OraculoNeural else None

        # 3. BUCLE DE VIAJE EN EL TIEMPO
        for sorteo_actual in nuevos:
            print(f"   >>> Procesando Sorteo #{sorteo_actual}...", end=" ")

            # --- A. CÁLCULO DE FECHA SIMULADA ---
            fila_actual = df_real[df_real['sorteo'] == sorteo_actual].iloc[0]
            fecha_target_str = str(fila_actual['fecha'])
            
            # Intentamos parsear la fecha real
            fecha_target_dt = datetime.now()
            try:
                # Soporte para dos formatos comunes
                if 'T' in fecha_target_str:
                    fecha_target_dt = datetime.strptime(fecha_target_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                else:
                    fecha_target_dt = datetime.strptime(fecha_target_str, '%Y-%m-%d %H:%M:%S')
            except: pass
            
            # Simulamos que estamos 5 minutos después del sorteo ANTERIOR (si existe)
            # Esto es cosmético para la data, pero útil para análisis de horarios
            fecha_simulada = fecha_target_dt - timedelta(hours=1) # Por defecto 1 hora antes
            
            # --- B. FASE JUEZ (Sentencia sobre el pasado inmediato) ---
            # El Juez evalúa las predicciones que hicimos para sorteos ANTERIORES a este.
            # Al correr juzgar(), él mira todo lo pendiente en el CSV.
            juez_implacable.juzgar() 
            
            # --- C. FASE ENTRENADOR (Aprende de la sentencia) ---
            # IMPORTANTE: Llamada sin argumentos, el entrenador es autónomo.
            # Él buscará las filas recién auditadas por el Juez.
            entrenador_cognitivo.analizar_adn_ganador()
            
            # --- D. FASE ORÁCULO NEURAL (Predicción del "Futuro Inmediato") ---
            if oraculo:
                # 1. Borrar predicción vieja si existe (para evitar duplicados sucios)
                if os.path.exists(SIMULACIONES_FILE):
                    df_sim = pd.read_csv(SIMULACIONES_FILE)
                    mask = (df_sim['juego'] == juego) & \
                           (df_sim['sorteo_objetivo'] == sorteo_actual) & \
                           (df_sim['algoritmo'] == 'oraculo_neural_v3')
                    if mask.any():
                        df_sim = df_sim[~mask]
                        df_sim.to_csv(SIMULACIONES_FILE, index=False)

                # 2. ENTRENAMIENTO "TIME TRAVEL"
                # Le prohibimos al oráculo ver el futuro (sorteo_actual)
                # Solo puede aprender de la historia hasta (sorteo_actual - 1)
                try:
                    oraculo.entrenar(sorteo_limite=sorteo_actual) # Asume que tu clase soporta este param
                    
                    # 3. PREDICCIÓN
                    prediccion = oraculo.predecir(fecha_objetivo=fecha_target_dt)
                    
                    if prediccion:
                        print(f"🔮 Oráculo: {prediccion}", end=" ")
                        
                        # 4. GUARDAR APUESTA SINTÉTICA
                        timestamp_simulado = int(time.time())
                        import random
                        id_ficticio = int(f"{timestamp_simulado}{random.randint(10,99)}")

                        nueva_fila = {
                            'id': id_ficticio,
                            'fecha_generacion': fecha_simulada.strftime('%Y-%m-%d %H:%M:%S'),
                            'juego': juego,
                            'numeros': str(sorted(prediccion)),
                            'sorteo_objetivo': sorteo_actual,
                            'estado': 'PENDIENTE', # Nace pendiente, el Juez la evaluará en la PRÓXIMA vuelta del bucle
                            'aciertos': 0,
                            'score_afinidad': 0.0,
                            'hora_dia': fecha_simulada.hour,
                            'algoritmo': 'oraculo_neural_v3'
                        }
                        
                        # Append atómico (modo append 'a' es más seguro y rápido que leer/escribir todo)
                        file_exists = os.path.exists(SIMULACIONES_FILE)
                        mod = 'a' if file_exists else 'w'
                        header = not file_exists
                        
                        keys = ['id', 'fecha_generacion', 'juego', 'numeros', 'sorteo_objetivo', 
                                'estado', 'aciertos', 'score_afinidad', 'hora_dia', 'algoritmo']
                        
                        import csv
                        with open(SIMULACIONES_FILE, mod, newline='', encoding='utf-8') as f:
                            w = csv.DictWriter(f, fieldnames=keys)
                            if header: w.writeheader()
                            # Aseguramos que el dict tenga solo las llaves necesarias
                            row_clean = {k: new_fila.get(k, '') for k in keys} # Typo fix: nueva_fila
                            w.writerow({k: nueva_fila.get(k, '') for k in keys})

                except Exception as e:
                    print(f"⚠️ Fallo Oráculo: {e}", end=" ")
            
            # --- E. MARCAR HITO ---
            actualizar_ultimo_procesado(juego, sorteo_actual)
            print("✅")

    print("\n✨ RECONSTRUCCIÓN FINALIZADA.")

if __name__ == "__main__":
    reconstruir_linea_tiempo()