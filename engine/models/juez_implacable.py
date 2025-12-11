import pandas as pd
import ast
import numpy as np
import os
import json

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')

FILE_SIMULACIONES = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")

# Mapeo de archivos maestros
MAESTROS_CONFIG = {
    "LOTO":   {"file": "LOTO_HISTORIAL_MAESTRO.csv", "cols": ["LOTO_n1","LOTO_n2","LOTO_n3","LOTO_n4","LOTO_n5","LOTO_n6"]},
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
            # Crear mapa: { '1234': [1, 2, 3...] } (Sorteo -> Números)
            mapa_sorteos = {}
            for _, row in df.iterrows():
                try:
                    # Extraer números ganadores
                    numeros = []
                    for col in config['cols']:
                        if col in row and not pd.isna(row[col]):
                            numeros.append(int(row[col]))
                    
                    if numeros:
                        sorteo_id = str(row['sorteo']) # Usar string para evitar problemas de tipos
                        mapa_sorteos[sorteo_id] = sorted(numeros)
                except: continue
            
            memoria[juego] = mapa_sorteos
            print(f"📚 {juego}: {len(mapa_sorteos)} sorteos cargados en memoria.")
            
        except Exception as e:
            print(f"❌ Error cargando {juego}: {e}")
            
    return memoria

def calcular_afinidad(prediccion, realidad, juego):
    """Calcula score 0-100 dependiendo de las reglas del juego."""
    if not prediccion or not realidad: return 0.0
    
    # --- REGLAS RACHA (Efecto Espejo) ---
    if juego == "RACHA":
        aciertos = len(set(prediccion) & set(realidad))
        # En Racha ganas con 10 aciertos O con 0 aciertos (y escalas intermedias)
        # Convertimos esto a una escala de "interés" para el bot
        if aciertos >= 10 or aciertos <= 0: return 100.0
        if aciertos >= 9 or aciertos <= 1: return 85.0
        if aciertos >= 8 or aciertos <= 2: return 60.0
        if aciertos >= 7 or aciertos <= 3: return 40.0
        return 0.0 # 4, 5, 6 aciertos no valen nada en Racha
        
    # --- REGLAS LOTO 3 (Exactitud con repetición) ---
    elif juego == "LOTO3":
        # Loto 3 importa el orden a veces, pero aquí mediremos coincidencia numérica simple
        # Si predigo [1, 1, 2] y sale [1, 2, 3], tengo 2 aciertos numéricos
        # Implementación simple: intersección
        # Nota: Para ser exactos en Loto3 habría que comparar conteos, pero set() simplifica
        aciertos = 0
        real_copy = list(realidad)
        for num in prediccion:
            if num in real_copy:
                aciertos += 1
                real_copy.remove(num)
        
        if aciertos == 3: return 100.0
        if aciertos == 2: return 50.0
        if aciertos == 1: return 10.0
        return 0.0

    # --- REGLAS LOTO / LOTO 4 (Clásico) ---
    else: 
        aciertos = len(set(prediccion) & set(realidad))
        total_bolas = len(realidad)
        
        # Puntuación exponencial
        ratio = aciertos / total_bolas
        if ratio == 1.0: return 100.0
        
        # Bonus por proximidad (solo si no ganamos)
        try:
            # Calcular cuán lejos estuvimos matemáticamente
            pred_vec = np.array(sorted(prediccion)[:total_bolas]) # Asegurar longitud
            real_vec = np.array(sorted(realidad)[:total_bolas])
            
            # Si las longitudes difieren (error de dato), saltar proximidad
            if len(pred_vec) == len(real_vec):
                diff = np.mean(np.abs(pred_vec - real_vec))
                # Un diff de 0 es 100 pts, un diff de 20 es 0 pts
                proximity_score = max(0, 100 - (diff * 5))
            else:
                proximity_score = 0
        except:
            proximity_score = 0
            
        # El score final es mayormente aciertos, con un toque de proximidad
        base_score = (aciertos / total_bolas) * 100
        return (base_score * 0.8) + (proximity_score * 0.2)

def juzgar():
    print("⚖️ JUEZ MULTIVERSO EN SESIÓN...")
    
    if not os.path.exists(FILE_SIMULACIONES):
        print("No hay simulaciones para juzgar.")
        return

    # 1. Cargar Memoria
    maestros = cargar_maestros()
    
    # 2. Leer Jugadas
    df_sim = pd.read_csv(FILE_SIMULACIONES)
    
    # Migración: Si no existe columna juego, asumir LOTO
    if 'juego' not in df_sim.columns:
        df_sim['juego'] = 'LOTO'
    
    cambios = 0
    
    # 3. Iterar y Juzgar
    for index, row in df_sim.iterrows():
        # Solo juzgar si está pendiente o si queremos re-auditar todo (opcional)
        # Para eficiencia, juzgamos todo lo que no tenga score perfecto o esté pendiente
        
        juego = row['juego']
        target_id = str(row['sorteo_objetivo'])
        
        # Verificar si tenemos los resultados oficiales para ese juego y sorteo
        if juego in maestros and target_id in maestros[juego]:
            nums_real = maestros[juego][target_id]
            
            try:
                # Parsear predicción que viene como string "[1, 2, 3]"
                # Manejo robusto por si viene sucio
                raw_nums = row['numeros']
                if isinstance(raw_nums, str):
                    nums_pred = ast.literal_eval(raw_nums)
                else:
                    nums_pred = raw_nums # Ya era lista
                
                if not isinstance(nums_pred, list): continue

            except Exception as e:
                # print(f"Error parseando fila {index}: {e}")
                continue
            
            # Calcular Métricas
            # Aciertos simples para mostrar al usuario
            if juego == "LOTO3":
                 # Logica especial para contar aciertos con repetidos
                 aciertos_display = 0
                 r_cp = list(nums_real)
                 for n in nums_pred:
                     if n in r_cp: 
                         aciertos_display +=1
                         r_cp.remove(n)
            else:
                aciertos_display = len(set(nums_pred) & set(nums_real))

            # Score interno para el algoritmo
            score_final = calcular_afinidad(nums_pred, nums_real, juego)
            
            # 4. Actualizar si hubo cambios
            # (Actualizamos si estaba PENDIENTE o si el score cambió por ajuste de fórmula)
            old_score = float(row['score_afinidad']) if not pd.isna(row['score_afinidad']) else -1.0
            
            if row['estado'] != 'AUDITADO' or abs(score_final - old_score) > 0.01:
                df_sim.at[index, 'aciertos'] = aciertos_display
                df_sim.at[index, 'score_afinidad'] = round(score_final, 2)
                df_sim.at[index, 'estado'] = 'AUDITADO'
                cambios += 1
                
                # Feedback visual
                if cambios % 10 == 0:
                    print(f"   🔨 Sentencia dictada para {juego} #{target_id}. Score: {score_final:.1f}")

    # 5. Guardar
    if cambios > 0:
        df_sim.to_csv(FILE_SIMULACIONES, index=False)
        print(f"✅ {cambios} veredictos actualizados en el archivo de simulaciones.")
    else:
        print("💤 La corte no encontró casos nuevos para juzgar.")

if __name__ == "__main__":
    juzgar()