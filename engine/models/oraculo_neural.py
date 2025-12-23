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
# TYPE: 'SET' (Orden de salida no importa para ganar) vs 'POSITIONAL' (Orden exacto importa)
# INPUT_COLS: Las columnas que explican la FÍSICA (Orden de extracción)
# TARGET_COLS: Las columnas que explican el REGLAMENTO (Números ganadores)

GAME_CONFIG = {
    "LOTO": {
        "type": "SET",
        "max": 41, "min_val": 1,
        "n_balls": 6,
        # Aprendemos del CAOS (pos) -> Predecimos el ORDEN (n)
        "input_prefix": "LOTO_pos", 
        "target_prefix": "LOTO_n"
    },
    "LOTO4": {
        "type": "SET",
        "max": 25, "min_val": 1, 
        "n_balls": 4,
        "input_prefix": "pos",
        "target_prefix": "n"
    },
    "RACHA": {
        "type": "SET",
        "max": 20, "min_val": 1,
        "n_balls": 10,
        "input_prefix": "pos",
        "target_prefix": "n"
    },
    "LOTO3": {
        "type": "POSITIONAL",
        "max": 9, "min_val": 0,
        "n_balls": 3,
        "input_prefix": "n", 
        "target_prefix": "n"
    }
}

class OraculoNeural:
    def __init__(self, game_id="LOTO"):
        self.game_id = game_id
        self.config = GAME_CONFIG.get(game_id, GAME_CONFIG["LOTO"])
        
        # Rutas de Archivos
        self.model_file = os.path.join(DATA_DIR, f'{game_id.lower()}_rf_model.pkl')
        self._set_maestro_path()

        self.window_size = 3 # Memoria de corto plazo (últimos 3 sorteos)
        self.model = None
        
        # Carga segura del modelo
        if os.path.exists(self.model_file):
            try:
                self.model = joblib.load(self.model_file)
            except Exception:
                self.model = None # Si falla (versión distinta), se re-entrena

    def _set_maestro_path(self):
        """Resuelve la inconsistencia de nombres de archivos"""
        if self.game_id == "LOTO": fname = 'LOTO_HISTORIAL_MAESTRO.csv'
        elif self.game_id == "LOTO3": fname = 'LOTO3_MAESTRO.csv'
        elif self.game_id == "LOTO4": fname = 'LOTO4_MAESTRO.csv'
        elif self.game_id == "RACHA": fname = 'RACHA_MAESTRO.csv'
        else: fname = f'{self.game_id}_MAESTRO.csv'
        self.maestro_file = os.path.join(DATA_DIR, fname)

    # --- UTILITARIOS MATEMÁTICOS ---
    def _get_one_hot(self, numbers):
        """Convierte [1, 2] -> [0, 1, 1, 0...] (Para juegos tipo SET)"""
        size = self.config['max'] + 1
        vec = np.zeros(size, dtype=np.int8)
        for n in numbers:
            try:
                val = int(float(n)) # float por si viene como 1.0
                if 0 <= val < size: vec[val] = 1
            except: pass
        return vec

    def _decode_one_hot_probs(self, probs_list, top_n):
        """Decodifica las probabilidades del Random Forest a números"""
        candidates = []
        # probs_list es una lista de arrays [prob_no, prob_si] por cada número posible
        for num_val, prob_arr in enumerate(probs_list):
            # Obtener probabilidad de la clase positiva (1)
            if len(prob_arr) > 0 and prob_arr[0].shape[0] > 1:
                prob_success = prob_arr[0][1] 
            else:
                prob_success = 0
            
            # Filtros de rango
            if num_val < self.config['min_val']: continue
            if num_val > self.config['max']: continue
            
            candidates.append((num_val, prob_success))
            
        # Ordenar por probabilidad descendente
        candidates.sort(key=lambda x: x[1], reverse=True)
        return sorted([x[0] for x in candidates[:top_n]])

    def _get_dynamic_cols(self, df, prefix, count):
        """Busca columnas dinámicamente (ej. pos1 o LOTO_pos1)"""
        cols = []
        # Estrategia 1: Nombre exacto generado
        candidates = [f"{prefix}{i}" for i in range(1, count + 1)]
        
        # Estrategia 2: Búsqueda flexible si no coinciden exacto
        available_cols = df.columns.tolist()
        final_cols = []
        
        for c in candidates:
            if c in available_cols:
                final_cols.append(c)
            else:
                # Fallback: intentar sin prefijo si el prefijo es complejo
                simple_c = c.split('_')[-1] # LOTO_pos1 -> pos1
                if simple_c in available_cols:
                    final_cols.append(simple_c)
                    
        return final_cols

    # --- NÚCLEO: PREPARACIÓN DE DATOS ---
    def _preparar_dataset(self, df):
        # 1. Definir columnas Input (Física) y Target (Reglamento)
        n_balls = self.config['n_balls']
        
        input_cols = self._get_dynamic_cols(df, self.config['input_prefix'], n_balls)
        target_cols = self._get_dynamic_cols(df, self.config['target_prefix'], n_balls)
        
        # 2. Validación de Integridad
        # Si faltan datos de input (ej. scraper viejo sin pos), usamos target como fallback
        if len(input_cols) < n_balls:
            input_cols = target_cols 
            
        if len(target_cols) < n_balls:
            return None, None # Data corrupta, abortar
            
        # 3. Limpieza Temporal
        if 'sorteo' in df.columns:
            df = df.sort_values('sorteo', ascending=True).reset_index(drop=True)
            
        # Eliminar filas con nulos en las columnas clave
        df = df.dropna(subset=input_cols + target_cols)
        
        # 4. Feature Engineering
        X_raw = df[input_cols].values # Matriz de números físicos
        y_raw = df[target_cols].values # Matriz de números resultado
        
        # Día de la semana (Feature Contextual)
        if 'fecha' in df.columns:
            dias = pd.to_datetime(df['fecha'], errors='coerce').dt.dayofweek.fillna(0).astype(int).values
        else:
            dias = np.zeros(len(df), dtype=int)

        X, y = [], []
        
        # 5. Construcción de Ventanas Deslizantes
        for i in range(self.window_size, len(df)):
            # --- INPUT: Historia Posicional ---
            # Aplanamos los últimos N sorteos (Física pura)
            # Ej: [PosSorteo-3, PosSorteo-2, PosSorteo-1, DiaObjetivo]
            features = []
            for w in range(1, self.window_size + 1):
                features.extend(X_raw[i-w])
            
            features.append(dias[i]) # Contexto temporal
            X.append(features)
            
            # --- TARGET: Resultado Esperado ---
            if self.config['type'] == 'SET':
                # Multilabel One-Hot (No importa el orden para ganar)
                y.append(self._get_one_hot(y_raw[i]))
            else:
                # Multiclass Directo (Importa el orden exacto, ej. Loto3)
                y.append([int(float(v)) for v in y_raw[i]])
                
        return np.array(X), np.array(y), input_cols, target_cols

    # === CAMBIO ÚNICO: SOPORTE PARA SORTEO LÍMITE ===
    def entrenar(self, sorteo_limite=None):
        msg_extra = f" (Hasta sorteo #{sorteo_limite})" if sorteo_limite else ""
        print(f"🧠 ORÁCULO ({self.game_id}): Iniciando entrenamiento físico...{msg_extra}")
        
        if not os.path.exists(self.maestro_file):
            print(f"❌ Archivo no encontrado: {self.maestro_file}")
            return

        df = pd.read_csv(self.maestro_file)
        
        # --- FILTRO DE TIEMPO (CRUCIAL PARA TU REQUERIMIENTO) ---
        if sorteo_limite is not None and 'sorteo' in df.columns:
            # Simulamos que los datos futuros NO existen aún
            df = df[df['sorteo'] <= int(sorteo_limite)]
        # --------------------------------------------------------

        if len(df) < 50: return

        X, y, _, _ = self._preparar_dataset(df)
        if X is None: 
            print("⚠️ Estructura de columnas irreconocible.")
            return

        samples = len(X)
        
        # --- HIPERPARÁMETROS ADAPTATIVOS ---
        if samples < 2000: 
            # Modo Loto (Pocos datos)
            depth, est = 6, 100
            print(f"   🛡️ Modo Táctico ({samples} muestras)")
        elif samples < 8000:
            # Modo Loto4 (Datos medios)
            depth, est = 10, 150
            print(f"   ⚖️ Modo Estratégico ({samples} muestras)")
        else: 
            # Modo Racha/Loto3 (Big Data)
            depth, est = 14, 150 
            print(f"   🚀 Modo Profundo Optimizado ({samples} muestras)")

        rf = RandomForestClassifier(
            n_estimators=est,
            max_depth=depth,
            class_weight='balanced' if self.config['type'] == 'SET' else None,
            n_jobs=-1,
            random_state=42
        )
        
        self.model = MultiOutputClassifier(rf)
        self.model.fit(X, y)
        
        # Guardar (Esto sobrescribe el pkl en cada iteración, logrando el efecto deseado)
        joblib.dump(self.model, self.model_file, compress=9)
        print("✅ Modelo entrenado, comprimido y guardado.")

    def predecir(self, fecha_objetivo=None, _intento_recuperacion=False):
        """
        Genera predicción. 
        fecha_objetivo: datetime object o string YYYY-MM-DD
        """
        # 1. Si no hay modelo en memoria, intentar cargar o entrenar
        if self.model is None: 
            self.entrenar()
        
        if self.model is None: return []

        # 2. Cargar datos para el input
        df = pd.read_csv(self.maestro_file)
        df = df.sort_values('sorteo', ascending=True)
        
        # Recuperar columnas usadas (reutilizando lógica de training)
        n_balls = self.config['n_balls']
        input_cols = self._get_dynamic_cols(df, self.config['input_prefix'], n_balls)
        target_cols = self._get_dynamic_cols(df, self.config['target_prefix'], n_balls)
        
        # Fallback de input
        if len(input_cols) < n_balls: input_cols = target_cols
        
        # Obtener datos recientes válidos
        df_valid = df.dropna(subset=input_cols)
        X_raw = df_valid[input_cols].values
        
        if len(X_raw) < self.window_size: return []

        # Construir Vector Input (Pasado)
        input_features = []
        last_idx = len(X_raw)
        for w in range(self.window_size):
            # Tomamos secuencia correcta: -3, -2, -1
            draw = X_raw[last_idx - self.window_size + w]
            input_features.extend(draw)
            
        # Determinar Día Objetivo (Futuro)
        target_dow = 0
        if fecha_objetivo:
            if isinstance(fecha_objetivo, str):
                try: target_dow = pd.to_datetime(fecha_objetivo).dayofweek
                except: target_dow = datetime.now().weekday()
            elif hasattr(fecha_objetivo, 'weekday'):
                target_dow = fecha_objetivo.weekday()
        else:
            # Default: Hoy
            target_dow = datetime.now().weekday()

        input_features.append(target_dow)
        X_pred = np.array([input_features])
        
        # Ejecutar Predicción (CON CAPTURA DE ERROR DE VERSIÓN)
        try:
            if self.config['type'] == 'SET':
                probs = self.model.predict_proba(X_pred)
                return self._decode_one_hot_probs(probs, n_balls)
            else:
                # Loto 3
                prediction = self.model.predict(X_pred)
                return [int(x) for x in prediction[0]]
                
        except Exception as e:
            # --- ZONA DE AUTO-CURACIÓN ---
            err_msg = str(e).lower()
            # Detectar error de compatibilidad scikit-learn (monotonic_cst)
            if not _intento_recuperacion and ("monotonic" in err_msg or "attribute" in err_msg or "version" in err_msg):
                print(f"♻️ INCOMPATIBILIDAD DETECTADA ({e}). Re-entrenando modelo en el entorno actual...")
                self.model = None # Forzar limpieza
                self.entrenar()   # Re-entrenar con la librería local
                # Intentar de nuevo (solo una vez para evitar bucles infinitos)
                return self.predecir(fecha_objetivo, _intento_recuperacion=True)
            else:
                print(f"❌ Error irrecuperable en predicción {self.game_id}: {e}")
                return []

if __name__ == "__main__":
    # Test Unitario
    for g in ["LOTO", "LOTO3", "RACHA", "LOTO4"]:
        print(f"\n--- {g} ---")
        ai = OraculoNeural(g)
        # ai.entrenar() # Descomentar si se quiere forzar entrenamiento
        print(f"🔮 Predicción: {ai.predecir()}")