import pandas as pd
import os
import time
from datetime import datetime, timedelta
import json
import sys
import csv

# --- GESTIÓN DE RUTAS ROBUSTA ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Importamos sin miedo (Manejo de errores explícito)
try:
    import juez_implacable
    import entrenador_cognitivo
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
        try:
            df_real = pd.read_csv(path)
        except: continue

        if 'sorteo' not in df_real.columns: continue
        
        # Ordenar cronológicamente
        df_real = df_real.sort_values('sorteo', ascending=True).reset_index(drop=True)
        todos_sorteos = df_real['sorteo'].unique()
        
        # 2. Determinar punto de partida
        ultimo_procesado = obtener_ultimo_procesado(juego)
        nuevos = [s for s in todos_sorteos if s > ultimo_procesado]
        
        if not nuevos:
            # print(f"✅ {juego}: Al día.")
            continue
            
        print(f"\n🚀 {juego}: Detectados {len(nuevos)} sorteos nuevos para reconstruir.")
        print(f"   📅 Sincronizando desde sorteo #{min(nuevos)}...")
        
        # Instanciamos una sola vez el oráculo para ahorrar memoria
        oraculo = OraculoNeural(juego) if OraculoNeural else None

        # 3. BUCLE DE VIAJE EN EL TIEMPO
        for sorteo_actual in nuevos:
            print(f"   >>> Procesando Sorteo #{sorteo_actual}...", end=" ")

            # --- A. CÁLCULO DE FECHA SIMULADA ---
            try:
                fila_actual = df_real[df_real['sorteo'] == sorteo_actual].iloc[0]
                fecha_target_str = str(fila_actual['fecha'])
                
                # Manejo robusto de fechas
                if 'T' in fecha_target_str:
                    fecha_target_dt = datetime.strptime(fecha_target_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                else:
                    fecha_target_dt = datetime.strptime(fecha_target_str, '%Y-%m-%d %H:%M:%S')
                
                # Viajamos 1 hora antes del sorteo real
                fecha_simulada = fecha_target_dt - timedelta(hours=1)
            except: 
                # Fallback de seguridad
                fecha_target_dt = datetime.now()
                fecha_simulada = datetime.now()
            
            # --- B. FASE JUEZ (Evalúa predicciones pendientes de la vuelta anterior) ---
            # El Juez es autónomo: va al CSV, busca PENDIENTES y los cruza con MAESTROS.
            juez_implacable.juzgar() 
            
            # --- C. FASE ENTRENADOR (Aprende de lo que el Juez acaba de calificar) ---
            # El Entrenador es autónomo: va al CSV, busca AUDITADOS nuevos y ajusta el JSON.
            entrenador_cognitivo.analizar_adn_ganador()
            
            # --- D. FASE ORÁCULO NEURAL (Predice el "Futuro Inmediato") ---
            if oraculo:
                # 1. Limpieza preventiva en CSV (Evita duplicados)
                # (Solo leemos si el archivo existe para borrar la fila vieja si hubiese)
                if os.path.exists(SIMULACIONES_FILE):
                    try:
                        # Leemos solo columnas clave para velocidad
                        df_sim = pd.read_csv(SIMULACIONES_FILE, usecols=['juego', 'sorteo_objetivo', 'algoritmo'])
                        hay_duplicado = ((df_sim['juego'] == juego) & 
                                         (df_sim['sorteo_objetivo'] == sorteo_actual) & 
                                         (df_sim['algoritmo'] == 'oraculo_neural_v3')).any()
                        
                        if hay_duplicado:
                            # Si hay duplicado, aquí sí hacemos la operación lenta de limpieza completa
                            df_full = pd.read_csv(SIMULACIONES_FILE)
                            mask = (df_full['juego'] == juego) & \
                                   (df_full['sorteo_objetivo'] == sorteo_actual) & \
                                   (df_full['algoritmo'] == 'oraculo_neural_v3')
                            df_full = df_full[~mask]
                            df_full.to_csv(SIMULACIONES_FILE, index=False)
                    except: pass

                # 2. ENTRENAMIENTO Y PREDICCIÓN
                try:
                    # Time Travel: Entrenar solo hasta ayer
                    oraculo.entrenar(sorteo_limite=sorteo_actual)
                    
                    prediccion = oraculo.predecir(fecha_objetivo=fecha_target_dt)
                    
                    if prediccion:
                        print(f"🔮 Oráculo: {prediccion}", end=" ")
                        
                        # 3. CONSTRUCCIÓN DE LA JUGADA SINTÉTICA
                        timestamp_simulado = int(time.time())
                        import random
                        id_ficticio = int(f"{timestamp_simulado}{random.randint(10,99)}")

                        # Variable corregida: nueva_fila (antes fallaba aquí)
                        nueva_fila = {
                            'id': id_ficticio,
                            'fecha_generacion': fecha_simulada.strftime('%Y-%m-%d %H:%M:%S'),
                            'juego': juego,
                            'numeros': str(sorted(prediccion)),
                            'sorteo_objetivo': sorteo_actual,
                            'estado': 'PENDIENTE', 
                            'aciertos': 0,
                            'score_afinidad': 0.0,
                            'hora_dia': fecha_simulada.hour,
                            'algoritmo': 'oraculo_neural_v3'
                        }
                        
                        # 4. GUARDADO ATÓMICO (OPTIMIZADO)
                        # Usamos append 'a' en lugar de reescribir todo el CSV
                        file_exists = os.path.exists(SIMULACIONES_FILE)
                        mode = 'a' if file_exists else 'w'
                        
                        keys = ['id', 'fecha_generacion', 'juego', 'numeros', 'sorteo_objetivo', 
                                'estado', 'aciertos', 'score_afinidad', 'hora_dia', 'algoritmo']
                        
                        with open(SIMULACIONES_FILE, mode, newline='', encoding='utf-8') as f:
                            w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
                            if not file_exists: w.writeheader()
                            w.writerow(nueva_fila) # ✅ Variable correcta

                except Exception as e:
                    print(f"⚠️ Fallo Oráculo: {e}", end=" ")
            
            # --- E. MARCAR HITO ---
            actualizar_ultimo_procesado(juego, sorteo_actual)
            print("✅")

    print("\n✨ RECONSTRUCCIÓN FINALIZADA.")

if __name__ == "__main__":
    reconstruir_linea_tiempo()