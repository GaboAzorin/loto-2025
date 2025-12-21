import pandas as pd
import numpy as np
import os
import joblib
import sys
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from datetime import datetime

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')

# --- CONFIGURACIÓN MAESTRA DEL MULTIVERSO ---
GAME_CONFIG = {
    "LOTO": {
        "type": "SET", "max": 41, "min_val": 1, "n_balls": 6,
        "input_prefix": "LOTO_pos", "target_prefix": "LOTO_n"
    },
    "LOTO4": {
        "type": "SET", "max": 25, "min_val": 1, "n_balls": 4,
        "input_prefix": "pos", "target_prefix": "n"
    },
    "RACHA": {
        "type": "SET", "max": 20, "min_val": 1, "n_balls": 10,
        "input_prefix": "pos", "target_prefix": "n"
    },
    "LOTO3": {
        "type": "POSITIONAL", "max": 9, "min_val": 0, "n_balls": 3,
        "input_prefix": "n", "target_prefix": "n"
    }
}

class OraculoNeural:
    def __init__(self, game_id="LOTO"):
        self.game_id = game_id
        self.config = GAME_CONFIG.get(game_id, GAME_CONFIG["LOTO"])
        self.model_file = os.path.join(DATA_DIR, f'{game_id.lower()}_rf_model.pkl')
        self._set_maestro_path()
        self.window_size = 3 
        self.model = None
        
        if os.path.exists(self.model_file):
            try: self.model = joblib.load(self.model_file)
            except: self.model = None

    def _set_maestro_path(self):
        if self.game_id == "LOTO": fname = 'LOTO_HISTORIAL_MAESTRO.csv'
        elif self.game_id == "LOTO3": fname = 'LOTO3_MAESTRO.csv'
        elif self.game_id == "LOTO4": fname = 'LOTO4_MAESTRO.csv'
        elif self.game_id == "RACHA": fname = 'RACHA_MAESTRO.csv'
        else: fname = f'{self.game_id}_MAESTRO.csv'
        self.maestro_file = os.path.join(DATA_DIR, fname)

    def _get_one_hot(self, numbers):
        size = self.config['max'] + 1
        vec = np.zeros(size, dtype=np.int8)
        for n in numbers:
            try:
                val = int(float(n))
                if 0 <= val < size: vec[val] = 1
            except: pass
        return vec

    def _decode_one_hot_probs(self, probs_list, top_n):
        candidates = []
        for num_val, prob_arr in enumerate(probs_list):
            if len(prob_arr) > 0 and prob_arr[0].shape[0] > 1:
                prob_success = prob_arr[0][1] 
            else: prob_success = 0
            
            if num_val < self.config['min_val']: continue
            if num_val > self.config['max']: continue
            candidates.append((num_val, prob_success))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return sorted([x[0] for x in candidates[:top_n]])

    def _get_dynamic_cols(self, df, prefix, count):
        candidates = [f"{prefix}{i}" for i in range(1, count + 1)]
        available_cols = df.columns.tolist()
        final_cols = []
        for c in candidates:
            if c in available_cols: final_cols.append(c)
            else:
                simple_c = c.split('_')[-1]
                if simple_c in available_cols: final_cols.append(simple_c)
        return final_cols

    def _preparar_dataset(self, df):
        n_balls = self.config['n_balls']
        input_cols = self._get_dynamic_cols(df, self.config['input_prefix'], n_balls)
        target_cols = self._get_dynamic_cols(df, self.config['target_prefix'], n_balls)
        
        if len(input_cols) < n_balls: input_cols = target_cols 
        if len(target_cols) < n_balls: return None, None
        
        if 'sorteo' in df.columns:
            df = df.sort_values('sorteo', ascending=True).reset_index(drop=True)
            
        df = df.dropna(subset=input_cols + target_cols)
        X_raw = df[input_cols].values
        y_raw = df[target_cols].values
        
        if 'fecha' in df.columns:
            dias = pd.to_datetime(df['fecha'], errors='coerce').dt.dayofweek.fillna(0).astype(int).values
        else: dias = np.zeros(len(df), dtype=int)

        X, y = [], []
        for i in range(self.window_size, len(df)):
            features = []
            for w in range(1, self.window_size + 1):
                features.extend(X_raw[i-w])
            features.append(dias[i]) 
            X.append(features)
            
            if self.config['type'] == 'SET':
                y.append(self._get_one_hot(y_raw[i]))
            else:
                y.append([int(float(v)) for v in y_raw[i]])
        return np.array(X), np.array(y), input_cols, target_cols

    def entrenar(self, sorteo_limite=None):
        """
        Entrena el modelo.
        sorteo_limite (int, opcional): Si se entrega, el modelo SOLO entrena 
        con datos hasta ese sorteo (inclusive).
        """
        msg_extra = f" [LIMITE: #{sorteo_limite}]" if sorteo_limite else ""
        print(f"🧠 ORÁCULO ({self.game_id}): Iniciando entrenamiento físico...{msg_extra}")
        
        if not os.path.exists(self.maestro_file): return

        df = pd.read_csv(self.maestro_file)
        
        if sorteo_limite and 'sorteo' in df.columns:
            df = df[df['sorteo'] <= int(sorteo_limite)]

        if len(df) < 50: return

        X, y, _, _ = self._preparar_dataset(df)
        if X is None: return

        samples = len(X)
        if samples < 2000: depth, est = 6, 100
        elif samples < 8000: depth, est = 10, 150
        else: depth, est = 14, 150 

        rf = RandomForestClassifier(
            n_estimators=est, max_depth=depth,
            class_weight='balanced' if self.config['type'] == 'SET' else None,
            n_jobs=-1, random_state=42
        )
        
        self.model = MultiOutputClassifier(rf)
        self.model.fit(X, y)
        
        joblib.dump(self.model, self.model_file, compress=9)
        print("   ✅ Modelo calibrado y guardado.")

    def predecir(self, fecha_objetivo=None):
        if self.model is None: self.entrenar()
        if self.model is None: return []

        df = pd.read_csv(self.maestro_file)
        df = df.sort_values('sorteo', ascending=True)
        
        n_balls = self.config['n_balls']
        input_cols = self._get_dynamic_cols(df, self.config['input_prefix'], n_balls)
        target_cols = self._get_dynamic_cols(df, self.config['target_prefix'], n_balls)
        if len(input_cols) < n_balls: input_cols = target_cols
        
        df_valid = df.dropna(subset=input_cols)
        X_raw = df_valid[input_cols].values
        
        if len(X_raw) < self.window_size: return []

        input_features = []
        last_idx = len(X_raw)
        for w in range(self.window_size):
            draw = X_raw[last_idx - self.window_size + w]
            input_features.extend(draw)
            
        target_dow = 0
        if fecha_objetivo:
            if isinstance(fecha_objetivo, str):
                try: target_dow = pd.to_datetime(fecha_objetivo).dayofweek
                except: target_dow = datetime.now().weekday()
            elif hasattr(fecha_objetivo, 'weekday'): target_dow = fecha_objetivo.weekday()
        else: target_dow = datetime.now().weekday()

        input_features.append(target_dow)
        X_pred = np.array([input_features])
        
        try:
            if self.config['type'] == 'SET':
                probs = self.model.predict_proba(X_pred)
                return self._decode_one_hot_probs(probs, n_balls)
            else:
                prediction = self.model.predict(X_pred)
                return [int(x) for x in prediction[0]]
        except Exception: return []

if __name__ == "__main__":
    for g in ["LOTO", "LOTO3", "RACHA", "LOTO4"]:
        ai = OraculoNeural(g)
        ai.entrenar()