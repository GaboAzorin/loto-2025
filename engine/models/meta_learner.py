import pandas as pd
import numpy as np
import joblib
import os
import json
from sklearn.ensemble import RandomForestRegressor

# Configuración
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
MODEL_FILE = os.path.join(DATA_DIR, 'meta_learner_model.pkl')
MAPS_FILE = os.path.join(DATA_DIR, 'meta_learner_maps.json') # NUEVO: Para persistir IDs
SIMULACIONES_FILE = os.path.join(DATA_DIR, 'LOTO_SIMULACIONES.csv')

class MetaLearner:
    def __init__(self):
        self.model = self.cargar_modelo()
        self.maps = self.cargar_mapas()

    def cargar_modelo(self):
        if os.path.exists(MODEL_FILE):
            return joblib.load(MODEL_FILE)
        return None

    def cargar_mapas(self):
        if os.path.exists(MAPS_FILE):
            with open(MAPS_FILE, 'r') as f: return json.load(f)
        return {"algos": {}, "juegos": {}}

    def entrenar(self):
        if not os.path.exists(SIMULACIONES_FILE): return
        
        df = pd.read_csv(SIMULACIONES_FILE)
        df_audit = df[df['estado'] == 'AUDITADO'].copy()
        if len(df_audit) < 300: return 

        # 1. Ingeniería de Características Pro
        # Creamos mapeos reales y los persistimos
        df_audit['alg_id'], alg_map = pd.factorize(df_audit['algoritmo'])
        df_audit['juego_id'], juego_map = pd.factorize(df_audit['juego'])
        
        self.maps['algos'] = {name: i for i, name in enumerate(alg_map)}
        self.maps['juegos'] = {name: i for i, name in enumerate(juego_map)}
        
        # Guardamos los mapas para que la predicción use las mismas IDs
        with open(MAPS_FILE, 'w') as f: json.dump(self.maps, f)

        # X = [ID Juego, ID Algo, Hora, Score ADN]
        X = df_audit[['juego_id', 'alg_id', 'hora_dia', 'score_afinidad']]
        y = df_audit['aciertos'] 

        # 2. Entrenamiento con regularización (para no sobreajustar al azar)
        model = RandomForestRegressor(n_estimators=150, max_depth=7, random_state=42)
        model.fit(X, y)
        
        joblib.dump(model, MODEL_FILE)
        self.model = model
        print(f"🧠 META-LEARNER: Cerebro de nivel 2 actualizado con {len(df_audit)} experiencias.")

    def predecir_confianza_real(self, juego, algoritmo, hora, score_adn):
        """Devuelve el multiplicador de peso basado en la probabilidad de éxito real"""
        if not self.model or not self.maps['algos']: return 1.0 
        
        try:
            # Recuperamos las IDs correctas de los diccionarios
            j_id = self.maps['juegos'].get(juego, -1)
            a_id = self.maps['algos'].get(algoritmo, -1)
            
            if j_id == -1 or a_id == -1: return 1.0 # Si es nuevo, peso neutro

            input_data = np.array([[j_id, a_id, hora, score_adn]]) 
            # El modelo predice cuántos aciertos se esperan
            esperanza_aciertos = self.model.predict(input_data)[0]
            
            # Normalizamos el multiplicador (Si espera muchos aciertos, sube el peso)
            # Para LOTO3 (max 3), una esperanza de 1.0 es altísima.
            multiplicador = 1.0 + (esperanza_aciertos * 2.0) 
            
            return max(0.5, multiplicador) 
        except:
            return 1.0