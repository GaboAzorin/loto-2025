import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import json
import os
from datetime import datetime

# ==========================================
# 🧭 NAVEGACIÓN DE RUTAS ABSOLUTA
# ==========================================
# Obtenemos la ruta absoluta de ESTE archivo (engine/models/loto3_tricore.py)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Retrocedemos 2 niveles para llegar a la raíz del proyecto (engine -> models -> raiz)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))

# Definimos las rutas exactas usando la raíz calculada
RUTA_DATA = os.path.join(PROJECT_ROOT, "data", "LOTO3_MAESTRO.csv")
RUTA_DASHBOARD = os.path.join(PROJECT_ROOT, "dashboard_data.json")

# ==========================================
# LÓGICA TRI-CORE
# ==========================================
class CerebroPosicional:
    """Un mini-modelo dedicado exclusivamente a UNA posición vertical"""
    def __init__(self, posicion_id):
        self.pos_id = posicion_id
        self.model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
    
    def preparar_features(self, df):
        col_name = f'LOTO3_n{self.pos_id}'
        
        # Validar que la columna exista
        if col_name not in df.columns:
            raise ValueError(f"Columna {col_name} no encontrada en CSV.")

        df = df.copy()
        
        # 1. Lags (Memoria de corto plazo)
        for i in range(1, 6):
            df[f'lag_{i}'] = df[col_name].shift(i)
        
        # 2. Frecuencia reciente
        df['rolling_mean'] = df[col_name].rolling(window=10).mean()
        
        # 3. Fecha (Ciclos temporales)
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'])
            df['dia_semana'] = df['fecha'].dt.dayofweek
            df['dia_mes'] = df['fecha'].dt.day
        else:
            df['dia_semana'] = df.index % 7
            df['dia_mes'] = df.index % 30
            
        return df.dropna()

    def entrenar(self, df):
        df_proc = self.preparar_features(df)
        
        features = [c for c in df_proc.columns if 'lag_' in c or 'dia_' in c or 'rolling' in c]
        target = f'LOTO3_n{self.pos_id}'
        
        X = df_proc[features]
        y = df_proc[target].astype(int)
        
        self.model.fit(X, y)
        self.last_X = X.iloc[[-1]] 
        return self.model.score(X, y)

    def predecir(self):
        probs = self.model.predict_proba(self.last_X)[0]
        
        # ESTRATEGIA: Selección ponderada de los top 3 para mantener varianza
        top_indices = np.argsort(probs)[-3:] 
        top_probs = probs[top_indices]
        top_probs = top_probs / top_probs.sum()
        
        prediccion = np.random.choice(top_indices, p=top_probs)
        confianza = probs[prediccion]
        
        return int(prediccion), confianza

def ejecutar_sistema_tricore():
    print("🚀 Iniciando Protocolo Tri-Core para LOTO 3...")
    print(f"📂 Raíz del proyecto detectada: {PROJECT_ROOT}")
    
    # 1. Cargar Datos
    if not os.path.exists(RUTA_DATA):
        print(f"❌ Error Crítico: No se encuentra el archivo en {RUTA_DATA}")
        return

    try:
        df = pd.read_csv(RUTA_DATA)
        print(f"✅ Datos cargados: {len(df)} sorteos históricos.")
    except Exception as e:
        print(f"❌ Error cargando CSV: {e}")
        return

    prediccion_final = []
    confianza_total = 0
    
    # 2. Bucle de Entrenamiento
    for i in range(1, 4):
        print(f"  ⚙️ Entrenando Núcleo Posicional #{i}...")
        try:
            cerebro = CerebroPosicional(i)
            acc = cerebro.entrenar(df)
            num, conf = cerebro.predecir()
            prediccion_final.append(num)
            confianza_total += conf
            print(f"     ✅ Núcleo {i} predice: {num} (Confianza: {conf:.2f})")
        except Exception as e:
            print(f"     ❌ Fallo en Núcleo {i}: {e}")
            prediccion_final.append(0) # Fallback

    # 3. Consolidar Resultado
    score_final = int((confianza_total / 3) * 100)
    
    nueva_jugada = {
        "fecha_generacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_lanzamiento": "Próximo Sorteo",
        "sorteo_objetivo": int(df['sorteo'].iloc[-1]) + 1 if 'sorteo' in df.columns else 0,
        "juego": "LOTO3_TRICORE",
        "numeros": prediccion_final, 
        "algoritmo": "Tri-Core (RF Independiente)",
        "score_afinidad": min(score_final + 25, 99), 
        "nota_especial": "ESTRUCTURA_POSICIONAL"
    }
    
    # 4. Inyectar en Dashboard
    guardar_en_dashboard(nueva_jugada)

def guardar_en_dashboard(jugada):
    data = []
    if os.path.exists(RUTA_DASHBOARD):
        try:
            with open(RUTA_DASHBOARD, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            print("⚠️ Dashboard corrupto o vacío, creando uno nuevo.")
            data = []
    
    # Insertar al principio
    data.insert(0, jugada)
    data = data[:200] # Limpieza
    
    try:
        with open(RUTA_DASHBOARD, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"✨ Predicción Tri-Core {jugada['numeros']} inyectada exitosamente en {RUTA_DASHBOARD}")
    except Exception as e:
        print(f"❌ Error escribiendo JSON: {e}")

if __name__ == "__main__":
    ejecutar_sistema_tricore()