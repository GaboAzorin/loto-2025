import pandas as pd
import os
import time
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
        
        # Ordenar por sorteo (antiguo a nuevo)
        df_real = df_real.sort_values('sorteo', ascending=True)
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
            print(f"   >>> Procesando Sorteo #{sorteo_actual}...")
            
            # A. FASE JUEZ (Actualiza estados de apuestas pasadas)
            juez_implacable.juzgar() 
            
            # B. FASE ENTRENADOR (Actualiza heurísticos, pares, sumas)
            entrenador_cognitivo.analizar_adn_ganador(juego_filtro=juego, sorteo_limite=sorteo_actual)
            
            # C. FASE ORÁCULO NEURAL (LA LÓGICA QUE PIDES)
    
            # 1. Verificamos si ya existe una predicción del Oráculo para este sorteo
            df_sim = pd.read_csv(SIMULACIONES_FILE) if os.path.exists(SIMULACIONES_FILE) else pd.DataFrame()
            
            existe_prediccion = False
            if not df_sim.empty and 'sorteo_objetivo' in df_sim.columns:
                # Buscamos si el oráculo ya opinó sobre este sorteo
                filtro = (df_sim['juego'] == juego) & \
                        (df_sim['sorteo_objetivo'] == sorteo_actual) & \
                        (df_sim['algoritmo'] == 'oraculo_neural_v3')
                
                if not df_sim[filtro].empty:
                    existe_prediccion = True
                    print(f"      ✅ Ya existe predicción del Oráculo para el sorteo {sorteo_actual}.")
                    # AQUÍ TU DECISIÓN:
                    # Si confías en que la predicción existente se hizo con los datos correctos, 'continue'.
                    # Si crees que se hizo 'tarde' o mal, la borramos y regeneramos.
                    # Según tu pedido: "reemplazar las simulaciones que se pasaron".
                    
                    # Borramos la anterior para garantizar que sea la "pura" generada con Time Travel
                    df_sim = df_sim[~filtro] # Eliminamos la fila vieja
                    df_sim.to_csv(SIMULACIONES_FILE, index=False)
                    print(f"      ♻️  Regenerando predicción pura (Time Travel) para asegurar consistencia...")

            # 2. Entrenamos el Oráculo VIAJANDO AL PASADO (Sorteo Limite = Sorteo Actual)
            # Esto asegura que el modelo NO vea los resultados del sorteo actual, solo los anteriores.
            oraculo.entrenar(sorteo_limite=sorteo_actual)
            
            # 3. Predecimos "el futuro" (que es el presente para nosotros, pero futuro para el modelo)
            # Nota: Usamos una fecha dummy o la fecha real del sorteo si la tienes, 
            # pero lo importante es que el modelo está cortado en el tiempo.
            prediccion = oraculo.predecir(fecha_objetivo=datetime.now()) 
            
            if prediccion:
                print(f"      🔮 Oráculo dice (Reconstrucción): {prediccion}")
                
                # 4. Guardamos la simulación "correcta"
                nueva_fila = {
                    'id': int(time.time()),
                    'fecha_generacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'juego': juego,
                    'numeros': str(prediccion),
                    'sorteo_objetivo': sorteo_actual,
                    'estado': 'PENDIENTE', # Se auditará en la siguiente vuelta del Juez
                    'aciertos': 0,
                    'score_afinidad': 0.0,
                    'hora_dia': 12, # Hora estándar simulada
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