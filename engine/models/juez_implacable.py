import pandas as pd
import ast
import numpy as np
import os

# --- CONFIGURACIÓN DE RUTAS ROBÚSTA ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')

FILE_SIMULACIONES = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
FILE_MAESTRO = os.path.join(DATA_DIR, "LOTO_HISTORIAL_MAESTRO.csv")

def calcular_afinidad(prediccion, realidad):
    """
    Calcula un puntaje PONDERADO (Híbrido).
    Prioriza los ACIERTOS EXACTOS sobre la cercanía matemática.
    """
    pred_vec = np.array(sorted(prediccion))
    real_vec = np.array(sorted(realidad))
    
    # 1. ACIERTOS (14 pts c/u)
    aciertos = len(set(prediccion) & set(realidad))
    
    # 2. PROXIMIDAD (Bonus max 16 pts)
    diferencia_promedio = np.mean(np.abs(pred_vec - real_vec))
    score_distancia = max(0, 100 - (diferencia_promedio * 5))
    
    puntaje_base = aciertos * 14
    bonus_proximidad = score_distancia * 0.16 
    
    score_final = puntaje_base + bonus_proximidad
    
    if aciertos == 6: return 100.0
    return round(score_final, 2)

def juzgar():
    print("⚖️ La corte está en sesión (Modo: Integridad Total)...")
    
    if not os.path.exists(FILE_SIMULACIONES):
        print("No hay simulaciones para juzgar.")
        return

    df_sim = pd.read_csv(FILE_SIMULACIONES)
    df_maestro = pd.read_csv(FILE_MAESTRO)
    
    # --- OPTIMIZACIÓN: Crear Mapa de Resultados en Memoria ---
    # Convertimos el maestro a un Diccionario {sorteo: [n1, n2...]}
    # Esto evita leer el DataFrame miles de veces dentro del bucle.
    mapa_ganadores = {}
    cols_reales = ['LOTO_n1', 'LOTO_n2', 'LOTO_n3', 'LOTO_n4', 'LOTO_n5', 'LOTO_n6']
    
    for _, row in df_maestro.iterrows():
        try:
            nums = sorted([int(row[c]) for c in cols_reales])
            mapa_ganadores[int(row['sorteo'])] = nums
        except:
            continue
    # -------------------------------------------------------
    
    cambios = 0
    
    # Recorremos TODAS las simulaciones para asegurar integridad
    for index, row in df_sim.iterrows():
        objetivo = int(row['sorteo_objetivo'])
        
        # Verificamos instantáneamente si tenemos el resultado en memoria
        if objetivo in mapa_ganadores:
            nums_real = mapa_ganadores[objetivo]
            
            try:
                nums_pred = sorted(ast.literal_eval(row['numeros']))
            except:
                continue # Saltar errores de formato
            
            # Calcular métricas nuevas
            aciertos = len(set(nums_real) & set(nums_pred))
            afinidad = calcular_afinidad(nums_pred, nums_real)
            
            # DETECCIÓN DE CAMBIOS INTELIGENTE
            # Solo "tocamos" la fila si los valores son diferentes a los que ya tiene
            # Esto evita reescribir el archivo si no es necesario
            old_aciertos = int(row['aciertos']) if not pd.isna(row['aciertos']) else -1
            old_score = float(row['score_afinidad']) if not pd.isna(row['score_afinidad']) else -1.0
            old_estado = row['estado']

            if aciertos != old_aciertos or abs(afinidad - old_score) > 0.01 or old_estado != 'AUDITADO':
                df_sim.at[index, 'aciertos'] = aciertos
                df_sim.at[index, 'score_afinidad'] = afinidad
                df_sim.at[index, 'estado'] = 'AUDITADO'
                
                print(f"📝 Sorteo {objetivo} actualizado. Score: {old_score} -> {afinidad}")
                cambios += 1
            
    if cambios > 0:
        df_sim.to_csv(FILE_SIMULACIONES, index=False)
        print(f"✅ Se actualizaron {cambios} registros (Corrección/Auditoría).")
    else:
        print("💤 Todo sincronizado. No hubo cambios en los puntajes.")

if __name__ == "__main__":
    juzgar()