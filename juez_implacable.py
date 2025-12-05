import pandas as pd
import ast
import numpy as np
import os

FILE_SIMULACIONES = "LOTO_SIMULACIONES.csv"
FILE_MAESTRO = "LOTO_HISTORIAL_MAESTRO.csv"

def calcular_afinidad(prediccion, realidad):
    """
    Calcula un puntaje PONDERADO (Híbrido).
    Prioriza los ACIERTOS EXACTOS sobre la cercanía matemática.
    """
    # Asegurar listas y orden para cálculo vectorial
    pred_vec = np.array(sorted(prediccion))
    real_vec = np.array(sorted(realidad))
    
    # 1. ACIERTOS (Lo más importante - Base sólida)
    # Usamos conjuntos para ver coincidencias exactas sin importar orden
    aciertos = len(set(prediccion) & set(realidad))
    
    # 2. PROXIMIDAD (Factor secundario - Desempate)
    # Diferencia absoluta promedio entre vectores ordenados
    diferencia_promedio = np.mean(np.abs(pred_vec - real_vec))
    
    # Score de distancia puro (0 a 100). 
    # Si la diferencia promedio es > 20 números, esto da 0.
    score_distancia = max(0, 100 - (diferencia_promedio * 5))
    
    # 3. FÓRMULA MAESTRA
    # - Cada acierto garantiza 14 puntos. (6 aciertos = 84 pts base)
    # - El 16% restante se llena con la calidad de la proximidad (bonus)
    # Lógica: 3 aciertos (42 pts) SIEMPRE ganarán a 0 aciertos muy cercanos (max 16 pts)
    
    puntaje_base = aciertos * 14
    bonus_proximidad = score_distancia * 0.16 
    
    score_final = puntaje_base + bonus_proximidad
    
    # Si tuvo 6 aciertos, es el Jackpot (100 cerrado)
    if aciertos == 6:
        return 100.0
        
    return round(score_final, 2)

def juzgar():
    print("⚖️ La corte está en sesión (Criterio Ponderado)...")
    
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
            
            try:
                # Convertir string de lista a lista real
                nums_pred = sorted(ast.literal_eval(row['numeros']))
            except:
                print(f"⚠️ Error de formato en fila {index}")
                continue
            
            # 1. Calcular Aciertos (Clásico)
            aciertos = len(set(nums_real) & set(nums_pred))
            
            # 2. Calcular Afinidad (Nueva fórmula ponderada)
            afinidad = calcular_afinidad(nums_pred, nums_real)
            
            # Actualizar DataFrame
            df_sim.at[index, 'aciertos'] = aciertos
            df_sim.at[index, 'score_afinidad'] = afinidad
            df_sim.at[index, 'estado'] = 'AUDITADO'
            
            print(f"📝 Sorteo {objetivo} auditado. Aciertos: {aciertos} | Score: {afinidad}")
            cambios += 1
            
    if cambios > 0:
        df_sim.to_csv(FILE_SIMULACIONES, index=False)
        print(f"✅ Se actualizaron {cambios} predicciones.")
    else:
        print("💤 No se encontraron predicciones pendientes para sorteos finalizados.")

if __name__ == "__main__":
    juzgar()