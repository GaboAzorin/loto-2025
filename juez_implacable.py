import pandas as pd
import ast
import numpy as np
import os

FILE_SIMULACIONES = "LOTO_SIMULACIONES.csv"
FILE_MAESTRO = "LOTO_HISTORIAL_MAESTRO.csv"

def calcular_afinidad(prediccion, realidad):
    """
    Calcula un puntaje de 0 a 100 basado en qué tan cerca estuvieron los números.
    Menor distancia vectorial = Mayor puntaje.
    """
    pred = np.array(prediccion)
    real = np.array(realidad)
    # Diferencia absoluta promedio por posición
    diferencia = np.mean(np.abs(pred - real))
    # Convertimos a score (Si diferencia es 0, score 100. Si es muy alta, baja)
    # Una diferencia promedio de 15 números da score 0.
    score = max(0, 100 - (diferencia * 6.6)) 
    return round(score, 2)

def juzgar():
    print("⚖️ La corte está en sesión...")
    
    if not os.path.exists(FILE_SIMULACIONES):
        print("No hay simulaciones para juzgar.")
        return

    df_sim = pd.read_csv(FILE_SIMULACIONES)
    df_maestro = pd.read_csv(FILE_MAESTRO)
    
    # Filtramos solo las pendientes
    pendientes = df_sim[df_sim['estado'] == 'PENDIENTE']
    
    cambios = 0
    for index, row in pendientes.iterrows():
        objetivo = row['sorteo_objetivo']
        
        # Buscamos si ese sorteo YA OCURRIÓ en el maestro
        resultado_real = df_maestro[df_maestro['sorteo'] == objetivo]
        
        if not resultado_real.empty:
            # Extraer números reales
            cols_reales = ['LOTO_n1', 'LOTO_n2', 'LOTO_n3', 'LOTO_n4', 'LOTO_n5', 'LOTO_n6']
            nums_real = sorted(resultado_real.iloc[0][cols_reales].values.tolist())
            nums_pred = sorted(ast.literal_eval(row['numeros']))
            
            # 1. Calcular Aciertos (Clásico)
            aciertos = len(set(nums_real) & set(nums_pred))
            
            # 2. Calcular Afinidad (Avanzado)
            afinidad = calcular_afinidad(nums_pred, nums_real)
            
            # Actualizar DataFrame
            df_sim.at[index, 'aciertos'] = aciertos
            df_sim.at[index, 'score_afinidad'] = afinidad
            df_sim.at[index, 'estado'] = 'AUDITADO'
            
            print(f"📝 Sorteo {objetivo} auditado. Aciertos: {aciertos} | Afinidad: {afinidad}%")
            cambios += 1
            
    if cambios > 0:
        df_sim.to_csv(FILE_SIMULACIONES, index=False)
        print(f"✅ Se actualizaron {cambios} predicciones.")
    else:
        print("💤 No se encontraron predicciones pendientes para sorteos finalizados.")

if __name__ == "__main__":
    juzgar()