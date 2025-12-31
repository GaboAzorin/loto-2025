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
                        sorteo_id = str(int(float(row['sorteo'])))
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
    
    # --- REGLAS RACHA (Curva de Aprendizaje en V) ---
    if juego == "RACHA":
        # Usamos sets porque en Racha no importa el orden, solo estar dentro o fuera
        aciertos = len(set(prediccion) & set(realidad))
        
        # Premios Reales (Estado final)
        if aciertos >= 10 or aciertos <= 0: return 100.0
        if aciertos == 9 or aciertos == 1: return 85.0
        if aciertos == 8 or aciertos == 2: return 60.0
        if aciertos == 7 or aciertos == 3: return 40.0
        
        # --- CORRECCIÓN CRÍTICA PARA LA IA ---
        # Si tengo 4, 5 o 6 aciertos, NO debo devolver 0 absoluto.
        # Debo devolver un puntaje bajo pero que indique dirección.
        # 5 es el peor estado (máxima entropía/azar). 4 y 6 son un poco mejores.
        if aciertos == 4 or aciertos == 6: return 15.0 # Casi ganas algo
        if aciertos == 5: return 5.0 # El peor resultado posible (ni cerca de 0 ni de 10)
        
        return 0.0 

    # --- REGLAS LOTO 3 (Precisión Posicional Estricta) ---
    elif juego == "LOTO3":
        # Asumimos que Loto 3 requiere ORDEN EXACTO (Posición 1, 2 y 3)
        # Si predigo [1, 2, 3] y sale [1, 2, 3] -> 3 ptos
        # Si predigo [3, 2, 1] y sale [1, 2, 3] -> 1 pto (solo el 2 coincide en posición)
        
        match_posicional = 0
        match_numerico = 0 # Para consuelo si acertó el número pero no la posición
        
        # Copia para no destruir la lista original al contar numéricos
        real_temp = list(realidad)
        
        # 1. Análisis Posicional (Lo que más vale)
        for i in range(min(len(prediccion), len(realidad))):
            if prediccion[i] == realidad[i]:
                match_posicional += 1
        
        # 2. Análisis Numérico (Premio de consuelo)
        # Esto ayuda a la IA a saber que "tenía los números correctos" aunque desordenados
        for n in prediccion:
            if n in real_temp:
                match_numerico += 1
                real_temp.remove(n)
        
        # CÁLCULO DE SCORE
        if match_posicional == 3: return 100.0 # ¡Exacta!
        
        # Ponderamos: 70% Posición, 30% Tenencia
        score_pos = (match_posicional / 3) * 70
        score_num = (match_numerico / 3) * 30
        
        return score_pos + score_num

# --- REGLAS LOTO / LOTO 4 (Escala Logarítmica de Premio) ---
    else: 
        aciertos = len(set(prediccion) & set(realidad))
        
        # CASO ESPECIAL LOTO 4 (El Jackpot es 4, no 6)
        if juego == "LOTO4" and aciertos == 4:
             return 1000.0 # ¡JACKPOT LOTO 4!

        # ESCALA GENERAL
        if aciertos == 6: return 1000.0 # JACKPOT LOTO
        if aciertos == 5: return 300.0  # Quina / Super Cuaterna
        if aciertos == 4: return 100.0  # Cuaterna
        if aciertos == 3: return 10.0   # Terna (Umbral mínimo de supervivencia)
        
        # Todo lo demás es fracaso.
        # Sin piedad. Sin puntos por "casi".
        return 0.0

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
        target_id = str(int(float(row['sorteo_objetivo'])))
        
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