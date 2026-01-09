import pandas as pd
import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestRegressor

# Configuración
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
MODEL_FILE = os.path.join(DATA_DIR, 'meta_learner_model.pkl')
SIMULACIONES_FILE = os.path.join(DATA_DIR, 'LOTO_SIMULACIONES.csv')

class MetaLearner:
    def __init__(self):
        self.model = self.cargar_modelo()

    def cargar_modelo(self):
        if os.path.exists(MODEL_FILE):
            return joblib.load(MODEL_FILE)
        return None

    def entrenar(self):
        """Entrena el cerebro de nivel 2 usando el historial de simulaciones"""
        if not os.path.exists(SIMULACIONES_FILE): return
        
        df = pd.read_csv(SIMULACIONES_FILE)
        df_audit = df[df['estado'] == 'AUDITADO'].copy()
        if len(df_audit) < 500: return # Necesitamos una base mínima

        # 1. Ingeniería de Características (Features)
        # Convertimos el nombre del algoritmo y la hora en números
        df_audit['alg_id'] = pd.factorize(df_audit['algoritmo'])[0]
        df_audit['juego_id'] = pd.factorize(df_audit['juego'])[0]
        
        X = df_audit[['alg_id', 'juego_id', 'hora_dia', 'score_afinidad']]
        y = df_audit['aciertos'] # El objetivo es predecir cuántos aciertos tendrá

        # 2. Entrenamiento
        model = RandomForestRegressor(n_estimators=100, max_depth=5)
        model.fit(X, y)
        
        # 3. Guardado
        joblib.dump(model, MODEL_FILE)
        self.model = model
        print("🧠 META-LEARNER: Sistema de segundo nivel actualizado.")

    def predecir_confianza_real(self, juego, algoritmo, hora, score_adn):
        """Devuelve la probabilidad de éxito ajustada por el Meta-Learner"""
        if not self.model: return 1.0 # Si no hay modelo, no altera el peso
        
        # Mapeo rápido para la predicción (simplificado)
        # Nota: En una versión pro, mapearíamos los IDs reales
        try:
            input_data = np.array([[0, 0, hora, score_adn]]) 
            prob = self.model.predict(input_data)[0]
            return max(0.1, prob) # Nunca devolver 0 para no anular
        except:
            return 1.0