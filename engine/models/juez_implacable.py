import pandas as pd
import ast
import numpy as np
import os
import json

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')

FILE_SIMULACIONES = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")

# Mapeo de archivos maestros (Añadimos referencia al Comodín para LOTO)
MAESTROS_CONFIG = {
    "LOTO":   {"file": "LOTO_HISTORIAL_MAESTRO.csv", "cols": ["LOTO_n1","LOTO_n2","LOTO_n3","LOTO_n4","LOTO_n5","LOTO_n6"], "comodin": "LOTO_comodin"},
    "LOTO3":  {"file": "LOTO3_MAESTRO.csv",          "cols": ["n1","n2","n3"]},
    "LOTO4":  {"file": "LOTO4_MAESTRO.csv",          "cols": ["n1","n2","n3","n4"]},
    "RACHA":  {"file": "RACHA_MAESTRO.csv",          "cols": ["n1","n2","n3","n4","n5","n6","n7","n8","n9","n10"]}
}

def cargar_maestros():
    """Carga todos los resultados históricos en un diccionario gigante en memoria."""
    memoria = {}
    
    for juego, config in MAESTROS_CONFIG.items():
        path = os.path.join(DATA_DIR, config['file'])
        if not os.path.exists(path):
            print(f"⚠️ No se encontró maestro para {juego}")
            continue
            
        try:
            df = pd.read_csv(path)
            mapa_sorteos = {}
            for _, row in df.iterrows():
                try:
                    # Extraer números ganadores
                    numeros = []
                    for col in config['cols']:
                        if col in row and not pd.isna(row[col]):
                            numeros.append(int(row[col]))
                    
                    # --- NUEVO: Extraer Comodín si existe ---
                    comodin = None
                    if "comodin" in config and config["comodin"] in row:
                        val = row[config["comodin"]]
                        comodin = int(val) if not pd.isna(val) else None

                    if numeros:
                        sorteo_id = str(int(float(row['sorteo'])))
                        # Ahora guardamos un diccionario con números y comodín
                        mapa_sorteos[sorteo_id] = {
                            "numeros": sorted(numeros),
                            "comodin": comodin
                        }
                except: continue
            
            memoria[juego] = mapa_sorteos
            print(f"📚 {juego}: {len(mapa_sorteos)} sorteos cargados en memoria.")
            
        except Exception as e:
            print(f"❌ Error cargando {juego}: {e}")
            
    return memoria

def calcular_afinidad(prediccion, realidad_obj, juego):
    """Calcula score 0-100 dependiendo de las reglas del juego."""
    if not prediccion or not realidad_obj: return 0.0
    
    # Extraemos los datos del objeto realidad
    realidad = realidad_obj["numeros"]
    comodin_real = realidad_obj.get("comodin")
    
    # --- REGLAS RACHA (Curva de Aprendizaje en V) ---
    if juego == "RACHA":
        aciertos = len(set(prediccion) & set(realidad))
        if aciertos >= 10 or aciertos <= 0: return 100.0
        if aciertos == 9 or aciertos == 1: return 85.0
        if aciertos == 8 or aciertos == 2: return 60.0
        if aciertos == 7 or aciertos == 3: return 40.0
        if aciertos == 4 or aciertos == 6: return 15.0 
        if aciertos == 5: return 5.0 
        return 0.0 

    # --- REGLAS LOTO 3 (Precisión Posicional Estricta) ---
    elif juego == "LOTO3":
        match_posicional = 0
        match_numerico = 0 
        real_temp = list(realidad)
        for i in range(min(len(prediccion), len(realidad))):
            if prediccion[i] == realidad[i]:
                match_posicional += 1
        for n in prediccion:
            if n in real_temp:
                match_numerico += 1
                real_temp.remove(n)
        if match_posicional == 3: return 100.0
        score_pos = (match_posicional / 3) * 70
        score_num = (match_numerico / 3) * 30
        return score_pos + score_num

    # --- REGLAS LOTO / LOTO 4 (Escala de Mérito Normalizada) ---
    else: 
        aciertos = len(set(prediccion) & set(realidad))
        
        # CASO ESPECIAL LOTO 4 (Normalizado a 100)
        if juego == "LOTO4":
            if aciertos == 4: return 100.0
            if aciertos == 3: return 50.0
            if aciertos == 2: return 20.0
            return 0.0

        # --- NUEVA ESCALA LOTO 41 (Basada en Categorías Reales) ---
        tiene_comodin = (comodin_real is not None) and (comodin_real in prediccion)
        
        if aciertos == 6: return 100.0                    # Loto (Jackpot)
        if aciertos == 5 and tiene_comodin: return 85.0     # Súper Quina
        if aciertos == 5: return 70.0                    # Quina
        if aciertos == 4 and tiene_comodin: return 55.0     # Súper Cuaterna
        if aciertos == 4: return 40.0                    # Cuaterna
        if aciertos == 3 and tiene_comodin: return 25.0     # Súper Terna
        if aciertos == 3: return 15.0                    # Terna
        if aciertos == 2 and tiene_comodin: return 10.0     # Súper Dupla
        
        # Pequeño mérito basal para orientar a la IA (máx 5%)
        return (aciertos / 6) * 5

def juzgar():
    print("⚖️ JUEZ MULTIVERSO EN SESIÓN...")
    
    if not os.path.exists(FILE_SIMULACIONES):
        print("No hay simulaciones para juzgar.")
        return

    # 1. Cargar Memoria
    maestros = cargar_maestros()
    
    # 2. Leer Jugadas
    df_sim = pd.read_csv(FILE_SIMULACIONES)
    
    if 'juego' not in df_sim.columns:
        df_sim['juego'] = 'LOTO'
    
    cambios = 0
    
    # 3. Iterar y Juzgar
    for index, row in df_sim.iterrows():
        juego = row['juego']
        target_id = str(int(float(row['sorteo_objetivo'])))
        
        if juego in maestros and target_id in maestros[juego]:
            # Realidad ahora es un dict con {"numeros": [...], "comodin": X}
            realidad_obj = maestros[juego][target_id]
            nums_real = realidad_obj["numeros"]
            
            try:
                raw_nums = row['numeros']
                if isinstance(raw_nums, str):
                    nums_pred = ast.literal_eval(raw_nums)
                else:
                    nums_pred = raw_nums
                
                if not isinstance(nums_pred, list): continue
            except: continue
            
            # Calcular Aciertos para display (Lógica original)
            if juego == "LOTO3":
                 aciertos_display = 0
                 r_cp = list(nums_real)
                 for n in nums_pred:
                     if n in r_cp: 
                         aciertos_display +=1
                         r_cp.remove(n)
            else:
                aciertos_display = len(set(nums_pred) & set(nums_real))

            # Score interno (NUEVA ESCALA)
            score_final = calcular_afinidad(nums_pred, realidad_obj, juego)
            
            old_score = float(row['score_afinidad']) if not pd.isna(row['score_afinidad']) else -1.0
            
            # Actualizamos si cambió el score (importante para recalibrar el histórico)
            if row['estado'] != 'AUDITADO' or abs(score_final - old_score) > 0.01:
                df_sim.at[index, 'aciertos'] = aciertos_display
                df_sim.at[index, 'score_afinidad'] = round(score_final, 2)
                df_sim.at[index, 'estado'] = 'AUDITADO'
                cambios += 1
                
                if cambios % 10 == 0:
                    print(f"    🔨 Sentencia dictada para {juego} #{target_id}. Score: {score_final:.1f}%")

    # 5. Guardar
    if cambios > 0:
        df_sim.to_csv(FILE_SIMULACIONES, index=False)
        print(f"✅ {cambios} veredictos actualizados y normalizados.")
    else:
        print("💤 La corte no encontró casos nuevos para juzgar.")

if __name__ == "__main__":
    juzgar()