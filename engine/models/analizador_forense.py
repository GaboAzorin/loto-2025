import pandas as pd
import numpy as np
import json
import os
import random
from datetime import datetime

class LotoForense:
    def __init__(self, game_id="LOTO", target_csv=None, target_day=None, genoma=None):
        """
        game_id: "LOTO", "LOTO3", "LOTO4", "RACHA"
        target_day: 0=Lunes, 6=Domingo (Si es None, usa todo el historial)
        """
        # --- CONFIGURACIÓN DEL MULTIVERSO ---
        self.configs = {
            "LOTO":   {"n": 6,  "min": 1, "max": 41, "replace": False, "col_prefix": "LOTO_n"},
            "LOTO3":  {"n": 3,  "min": 0, "max": 9,  "replace": True,  "col_prefix": "n"},
            "LOTO4":  {"n": 4,  "min": 1, "max": 41, "replace": False, "col_prefix": "n"},
            "RACHA":  {"n": 10, "min": 1, "max": 20, "replace": False, "col_prefix": "n"}
        }
        
        self.genoma = genoma or {}
        self.morph = self.genoma.get('morphology', {}).get(game_id, {})
        self.game_id = game_id
        self.rules = self.configs.get(game_id, self.configs["LOTO"])
        self.target_day = target_day

        # --- RUTAS ---
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(base_dir, '..', '..', 'data')
        
        # Mapeo automático
        if not target_csv:
            file_map = {
                "LOTO": "LOTO_HISTORIAL_MAESTRO.csv",
                "LOTO3": "LOTO3_MAESTRO.csv",
                "LOTO4": "LOTO4_MAESTRO.csv",
                "RACHA": "RACHA_MAESTRO.csv"
            }
            target_csv = os.path.join(self.data_dir, file_map.get(game_id, "LOTO_HISTORIAL_MAESTRO.csv"))
            
        self.csv_path = target_csv
        self.biometrics_file = os.path.join(self.data_dir, f"{game_id.lower()}_biometrics.json")

        self.df = None
        self.stats_matrix = {}
        self.markov_matrix = {} 
        self.delta_distribution = {} # Recuperado
        self.past_combinations = set() # Recuperado
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 Forense iniciado: {game_id} | Filtro Día: {target_day if target_day is not None else 'TODOS'}")
        
        self.load_data()
        self.generate_mechanical_matrix()

    def load_data(self):
        if not os.path.exists(self.csv_path):
            print(f"⚠️ No se encontró {self.csv_path}")
            return

        self.df = pd.read_csv(self.csv_path)
        
        # Filtrado Temporal
        if self.target_day is not None:
            try:
                self.df['fecha_dt'] = pd.to_datetime(self.df['fecha'], errors='coerce', dayfirst=True)
                df_filtered = self.df[self.df['fecha_dt'].dt.dayofweek == self.target_day]
                
                if len(df_filtered) > 10:
                    print(f"   📅 Aplicando filtro temporal. Sorteos reducidos de {len(self.df)} a {len(df_filtered)}")
                    self.df = df_filtered
                else:
                    print("   ⚠️ Poca data para este día específico. Usando dataset global.")
            except Exception as e:
                print(f"   ⚠️ Error filtrando fechas: {e}")

        # Entrenar modelos avanzados y cargar historial
        self._train_advanced_models()
        self._load_past_combinations()

    def _train_advanced_models(self):
        if self.df is None or self.df.empty: return
        
        cols = [f"{self.rules['col_prefix']}{i}" for i in range(1, self.rules['n'] + 1)]
        if not all(c in self.df.columns for c in cols): return

        # 1. Markov & Delta
        self.markov_matrix = {}
        self.delta_distribution = {i: [] for i in range(self.rules['n'])}

        history_lists = self.df[cols].fillna(-1).astype(int).values.tolist()
        
        for i in range(len(history_lists)):
            current_draw = history_lists[i]
            
            # Entrenamiento Delta (Diferencia entre bolas)
            if self.game_id == "LOTO": # Delta tiene más sentido en Loto ordenado
                prev = 0
                for idx, n in enumerate(current_draw):
                    if n > 0:
                        delta = n - prev
                        if delta > 0: self.delta_distribution[idx].append(delta)
                        prev = n

            # Entrenamiento Markov
            if i < len(history_lists) - 1:
                next_draw = history_lists[i+1]
                for num in current_draw:
                    if num < 0: continue
                    if num not in self.markov_matrix: self.markov_matrix[num] = []
                    self.markov_matrix[num].extend([x for x in next_draw if x > 0])

    def _load_past_combinations(self):
        """Memoriza combinaciones pasadas para evitar repetirlas (Solo Loto)"""
        if self.game_id != "LOTO": return
        cols = [f"{self.rules['col_prefix']}{i}" for i in range(1, self.rules['n'] + 1)]
        if all(c in self.df.columns for c in cols):
             for _, row in self.df[cols].dropna().iterrows():
                 try:
                     nums = tuple(sorted([int(x) for x in row]))
                     self.past_combinations.add(nums)
                 except: pass

    def generate_mechanical_matrix(self):
        if self.df is None or self.df.empty: return
        cols = [f"{self.rules['col_prefix']}{i}" for i in range(1, self.rules['n'] + 1)]
        
        matrix = {}
        for col in cols:
            if col in self.df.columns:
                counts = self.df[col].value_counts(normalize=True).to_dict()
                matrix[col] = counts
        self.stats_matrix = matrix

    # ================= MOTORES DE PREDICCIÓN =================

    def predict_weighted(self): # Antes llamado forense_biometrico
        """Predicción basada en pesos posicionales"""
        prediction = []
        possible_numbers = list(range(self.rules['min'], self.rules['max'] + 1))
        cols = [f"{self.rules['col_prefix']}{i}" for i in range(1, self.rules['n'] + 1)]

        for col in cols:
            weights_map = self.stats_matrix.get(col, {})
            weights = []
            for num in possible_numbers:
                weights.append(weights_map.get(num, 0.001))
            
            total = sum(weights)
            probs = [w/total for w in weights]
            
            chosen = np.random.choice(possible_numbers, p=probs)
            
            if not self.rules['replace']:
                # Intento simple de evitar colisiones
                attempts = 0
                while chosen in prediction and attempts < 50:
                    chosen = np.random.choice(possible_numbers, p=probs)
                    attempts += 1
            
            prediction.append(int(chosen))
        
        return sorted(prediction)

    def predict_smart_gaussian(self):
        """Predicción estadística que respeta el ADN del genoma"""
        if not self.morph: return self.predict_weighted()

        # Extraemos métricas del ADN ganador
        rango_suma = self.morph.get('ideal_sum_range', [100, 150])
        ideal_pares = self.morph.get('ideal_even_count', 3)
        
        attempts = 0
        while attempts < 5000:
            attempts += 1
            # Generar candidato respetando los límites físicos del juego
            nums = sorted(random.sample(range(self.rules['min'], self.rules['max'] + 1), self.rules['n']))
            
            # FILTRO 1: Suma Dinámica
            suma = sum(nums)
            if suma < rango_suma[0] or suma > rango_suma[1]: continue
            
            # FILTRO 2: Paridad Dinámica (Tolerancia de +/- 1)
            evens = len([x for x in nums if x % 2 == 0])
            if abs(evens - ideal_pares) > 1.5: continue
            
            # FILTRO 3: Historia (Solo Loto)
            if self.game_id == "LOTO" and tuple(nums) in self.past_combinations: continue
                
            return nums
        return self.predict_weighted()

    def predict_dna_delta(self):
        """Generación basada en la 'velocidad' (distancia) ideal entre números"""
        avg_delta_target = self.morph.get('ideal_avg_delta', 6.0)
        
        for _ in range(200):
            prediction = []
            current_val = self.rules['min']
            
            for i in range(self.rules['n']):
                # Obtenemos deltas reales observados para esta posición
                deltas_reales = self.delta_distribution.get(i, [int(avg_delta_target)])
                # Sesgamos la elección hacia el delta ideal del genoma
                chosen_delta = random.choice(deltas_reales)
                
                # Ajuste fino: si nos alejamos mucho del promedio ideal, compensamos
                if i > 0:
                    current_avg = (sum(np.diff(prediction)) + chosen_delta) / len(prediction)
                    if current_avg > avg_delta_target: chosen_delta = max(1, chosen_delta - 1)
                
                next_val = current_val + chosen_delta
                prediction.append(next_val)
                current_val = next_val
            
            # Validación de salida
            if any(x > self.rules['max'] for x in prediction): continue
            if len(set(prediction)) != self.rules['n']: continue
            
            return sorted(prediction)
        return self.predict_weighted()

    def predict_markov(self):
        """Predicción basada en transiciones"""
        if self.df is None or self.df.empty: return self.predict_weighted()
        
        cols = [f"{self.rules['col_prefix']}{i}" for i in range(1, self.rules['n'] + 1)]
        last_draw = self.df.iloc[-1][cols].fillna(-1).astype(int).tolist()
        
        pool = []
        for num in last_draw:
            if num in self.markov_matrix:
                pool.extend(self.markov_matrix[num])
        
        if not pool: return self.predict_weighted()
        
        from collections import Counter
        counts = Counter(pool)
        common = counts.most_common(self.rules['n'] + 10)
        candidates = [num for num, count in common]
        
        prediction = []
        for num in candidates:
            if len(prediction) >= self.rules['n']: break
            if self.rules['replace'] or num not in prediction:
                prediction.append(num)
                
        while len(prediction) < self.rules['n']:
            r = random.randint(self.rules['min'], self.rules['max'])
            if self.rules['replace'] or r not in prediction:
                prediction.append(r)
                
        return sorted(prediction)