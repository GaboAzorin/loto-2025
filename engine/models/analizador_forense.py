import pandas as pd
import numpy as np
import json
import re
import os
import random
from datetime import datetime

class LotoForense:
    def __init__(self, csv_path=None):
        # --- CONFIGURACIÓN DE RUTAS ROBUSTA ---
        # 1. Detectamos dónde está ESTE archivo (analizador_forense.py)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # 2. Asumimos que la carpeta 'data' está un nivel arriba, hermana de 'engine'
        self.data_dir = os.path.join(base_dir, '..', 'data')
        
        # 3. Definimos rutas absolutas
        if csv_path is None:
            self.csv_path = os.path.join(self.data_dir, "LOTO_HISTORIAL_MAESTRO.csv")
        else:
            self.csv_path = csv_path

        # El JSON de caché también va a la carpeta data para mantener orden
        self.biometrics_file = os.path.join(self.data_dir, "loto_biometrics.json")

        self.df = None
        self.structure = {} 
        self.stats_matrix = {}
        self.past_combinations = set() # Memoria de jugadas pasadas para el Gaussiano
        
        # Cache para modelos avanzados
        self.markov_matrix = {} 
        self.delta_distribution = {}
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 Inicializando LotoForense...")
        print(f"   📂 Ruta CSV: {self.csv_path}")
        
        # 1. Intentar cargar biometría existente para ahorrar tiempo de cómputo
        if os.path.exists(self.biometrics_file):
            try:
                with open(self.biometrics_file, "r", encoding='utf-8') as f:
                    self.stats_matrix = json.load(f)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧠 Biometría cargada desde JSON (Caché).")
            except:
                print("⚠️ Error leyendo JSON, se recalculará desde cero.")
        
        # Siempre cargamos datos para tener el historial disponible
        self.load_data()
        
        # 2. Si no hay matriz en caché, calcular
        if not self.stats_matrix:
            self._detect_game_structure()
            self.generate_mechanical_matrix()

    def load_data(self):
        if not os.path.exists(self.csv_path):
            print(f"⚠️ Advertencia CRÍTICA: No se encontró {self.csv_path}.")
            print(f"   Asegúrate de que el archivo esté en la carpeta 'data/'.")
            return

        self.df = pd.read_csv(self.csv_path)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📂 Datos cargados: {len(self.df)} sorteos históricos.")
        
        # Cargar historial de combinaciones para evitar repetirlas (Lógica Gaussiana)
        try:
            cols = [f'LOTO_n{i}' for i in range(1, 7)]
            if all(c in self.df.columns for c in cols):
                valid_df = self.df.dropna(subset=cols)
                for _, row in valid_df.iterrows():
                    try:
                        nums = sorted([int(row[c]) for c in cols])
                        self.past_combinations.add(tuple(nums))
                    except:
                        continue
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📚 Historial Gaussiano: {len(self.past_combinations)} jugadas pasadas memorizadas.")
        except Exception as e:
            print(f"⚠️ Alerta menor: No se pudo cargar historial de combinaciones ({e})")
        
        # Entrenar modelos avanzados (Delta y Markov) si hay datos
        self._train_advanced_models()

        # Ejecutar detección de estructura si no se ha hecho
        if not self.structure:
            self._detect_game_structure()

    def _detect_game_structure(self):
        """Escanea dinámicamente todas las columnas para identificar modalidades de juego."""
        if self.df is None: return

        columns = self.df.columns.tolist()
        game_map = {}
        pattern = re.compile(r'^(.*)_(n|pos)(\d+)$')

        for col in columns:
            match = pattern.match(col)
            if match:
                prefix = match.group(1) 
                type_ = match.group(2)  
                idx = int(match.group(3)) 

                if prefix not in game_map:
                    game_map[prefix] = {'n': {}, 'pos': {}, 'comodin': None}
                
                game_map[prefix][type_][idx] = col
                continue

            if col.endswith('_comodin'):
                prefix = col.replace('_comodin', '')
                if prefix not in game_map:
                    game_map[prefix] = {'n': {}, 'pos': {}, 'comodin': None}
                game_map[prefix]['comodin'] = col

        self.structure = game_map

    def _train_advanced_models(self):
        """Entrena las matrices para Delta y Markov en memoria"""
        if self.df is None or self.df.empty: return
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧠 Entrenando modelos avanzados (Delta & Markov)...")
        cols = [f'LOTO_n{i}' for i in range(1, 7)]
        
        # --- 1. ENTRENAMIENTO DELTA ---
        # Calculamos la diferencia entre la bola N y la bola N-1
        self.delta_distribution = {i: [] for i in range(6)} # 0: n1-0, 1: n2-n1, etc.
        
        valid_rows = self.df.dropna(subset=cols)
        for _, row in valid_rows.iterrows():
            try:
                nums = sorted([int(row[c]) for c in cols])
                prev = 0
                for i, n in enumerate(nums):
                    delta = n - prev
                    if delta > 0: self.delta_distribution[i].append(delta)
                    prev = n
            except: continue

        # --- 2. ENTRENAMIENTO MARKOV ---
        # Mapeamos: Números sorteo T -> Números sorteo T+1
        self.markov_matrix = {n: [] for n in range(1, 42)}
        
        # Convertir a lista de listas para iterar rápido
        history_lists = valid_rows[cols].values.tolist()
        
        for i in range(len(history_lists) - 1):
            current_draw = history_lists[i]
            next_draw = history_lists[i+1]
            
            # Para cada número del sorteo actual, registramos TODOS los números del siguiente
            for num_in_current in current_draw:
                try:
                    n_curr = int(num_in_current)
                    if 1 <= n_curr <= 41:
                        self.markov_matrix[n_curr].extend([int(x) for x in next_draw])
                except: continue

    def generate_mechanical_matrix(self):
        """Genera una matriz de probabilidades basada en la física de la extracción."""
        if self.df is None:
            self.load_data()
            if self.df is None: return {} 

        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚙️  Calculando Matriz de Peso Mecánico...")
        
        report = {
            "metadata": {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_sorteos_analizados": len(self.df)
            },
            "games": {}
        }

        for mode, cols in self.structure.items():
            use_pos = len(cols['pos']) > 0
            source_type = 'pos' if use_pos else 'n'
            target_cols = cols[source_type]

            if not target_cols:
                continue

            mode_data = {
                "source_type": "MECHANICAL" if use_pos else "SORTED",
                "positions": {},
                "global_heat": {}
            }

            global_counts = pd.Series(dtype=int)

            for pos_idx in sorted(target_cols.keys()):
                col_name = target_cols[pos_idx]
                vc = self.df[col_name].value_counts()
                global_counts = global_counts.add(vc, fill_value=0)
                freq_dict = {int(k): int(v) for k, v in vc.items()}
                
                total_valid_draws = self.df[col_name].count()
                prob_dict = {str(k): round(v / total_valid_draws, 5) for k, v in freq_dict.items()}

                mode_data["positions"][str(pos_idx)] = {
                    "col_name": col_name,
                    "counts": freq_dict,
                    "weights": prob_dict, 
                    "most_frequent": int(vc.idxmax()) if not vc.empty else None
                }

            if cols['comodin']:
                c_col = cols['comodin']
                vc_c = self.df[c_col].value_counts()
                mode_data["comodin"] = {
                    "col_name": c_col,
                    "counts": {int(k): int(v) for k, v in vc_c.items()}
                }

            global_counts = global_counts.sort_values(ascending=False)
            mode_data["global_heat"] = {str(k): int(v) for k, v in global_counts.items()}
            report["games"][mode] = mode_data

        self.stats_matrix = report
        self.save_intelligence()
        return report

    def save_intelligence(self, filename=None):
        # Usamos la ruta calculada si no se pasa nombre
        target_file = filename if filename else self.biometrics_file
        
        if not self.stats_matrix:
            return
        
        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats_matrix, f, indent=2)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Inteligencia guardada en '{target_file}'")
        except Exception as e:
            print(f"❌ Error guardando JSON: {e}")

    def get_quick_stats(self, game_mode, number):
        """Consulta rápida para verificar datos desde Python"""
        game_data = self.stats_matrix.get("games", {}).get(game_mode)
        if not game_data:
            return f"No hay datos para {game_mode}"
        total_hits = game_data.get("global_heat", {}).get(str(number), 0)
        return f"El número {number} ha salido {total_hits} veces en {game_mode}."

    # ==============================================================================
    # 🔮 1. MOTOR DE PREDICCIÓN BIOMÉTRICA (FÍSICA)
    # ==============================================================================
    def predict_numbers(self, game_mode="LOTO", n=6):
        """Genera predicción basada en pesos históricos por posición (Monte Carlo)."""
        if not self.stats_matrix:
            print("⚠️ Matriz vacía. Intentando generar...")
            self.generate_mechanical_matrix()

        game_data = self.stats_matrix.get("games", {}).get(game_mode)
        if not game_data:
            return sorted(random.sample(range(1, 42), n))

        prediction = []
        full_pool = set(range(1, 42)) 
        
        for i in range(1, n + 1):
            pos_key = str(i)
            pos_data = game_data['positions'].get(pos_key, {})
            weights_map = pos_data.get('weights', {})
            
            candidates = []
            probs = []
            available_numbers = full_pool - set(prediction)
            
            for num in available_numbers:
                num_str = str(num)
                weight = weights_map.get(num_str, 0.00001)
                candidates.append(num)
                probs.append(weight)
            
            total_prob = sum(probs)
            if total_prob <= 0:
                normalized_probs = [1.0/len(candidates)] * len(candidates)
            else:
                normalized_probs = [p / total_prob for p in probs]
            
            picked_number = np.random.choice(candidates, p=normalized_probs)
            prediction.append(int(picked_number))

        return sorted(prediction)

    # ==============================================================================
    # 📐 2. MOTOR DE PREDICCIÓN GAUSSIANA (ESTADÍSTICA)
    # ==============================================================================
    def predict_gaussian(self, n=6):
        """Genera predicción basada en filtros estadísticos estrictos."""
        attempts = 0
        max_attempts = 5000
        
        while attempts < max_attempts:
            attempts += 1
            nums = sorted(random.sample(range(1, 42), n))
            
            suma = sum(nums)
            if suma < 100 or suma > 150: continue
            
            evens = len([x for x in nums if x % 2 == 0])
            if evens < 2 or evens > 4: continue
            
            if tuple(nums) in self.past_combinations: continue
            
            consecutivos = 0
            max_consecutivos = 0
            for i in range(len(nums)-1):
                if nums[i+1] == nums[i] + 1: consecutivos += 1
                else: consecutivos = 0
                if consecutivos > max_consecutivos: max_consecutivos = consecutivos
            
            if max_consecutivos >= 2: continue
                
            return nums
            
        print("⚠️ Advertencia: No se encontró combinación gaussiana perfecta. Devolviendo aleatorio.")
        return sorted(random.sample(range(1, 42), n))

    # ==============================================================================
    # 📈 3. MOTOR DELTA TÁCTICO (DIFERENCIAL)
    # ==============================================================================
    def predict_delta(self, n=6):
        """
        Predice basado en la distancia promedio entre números consecutivos.
        Reconstruye la jugada sumando 'deltas' probables.
        """
        if not self.delta_distribution: self._train_advanced_models()
        
        for _ in range(100): # Intentos para encontrar secuencia válida
            prediction = []
            current_val = 0
            
            # Generar 6 deltas secuenciales basados en la historia de cada posición
            for i in range(6):
                # Obtener lista histórica de deltas para esta posición (i)
                deltas = self.delta_distribution.get(i, [5]) # Default 5 si no hay data
                if not deltas: deltas = [5]
                
                # Elegir un delta al azar de la historia real
                chosen_delta = random.choice(deltas)
                
                next_val = current_val + chosen_delta
                prediction.append(next_val)
                current_val = next_val
            
            # Validaciones Delta
            # 1. Rango válido (1-41)
            if any(x > 41 for x in prediction) or any(x < 1 for x in prediction): continue
            # 2. Sin repetidos (Delta lo garantiza si delta > 0, pero por seguridad)
            if len(set(prediction)) != n: continue
            
            return sorted(prediction)
        
        # Fallback al Gaussiano si no encuentra delta válido
        return self.predict_gaussian(n)

    # ==============================================================================
    # 🔗 4. MOTOR CADENAS DE MARKOV (TRANSICIONAL)
    # ==============================================================================
    def predict_markov(self, n=6):
        """
        Predice basado en la probabilidad de transición del ÚLTIMO sorteo conocido.
        """
        if not self.markov_matrix: self._train_advanced_models()
        
        # 1. Obtener el último sorteo real conocido para usar como "semilla"
        try:
            cols = [f'LOTO_n{i}' for i in range(1, 7)]
            valid_df = self.df.dropna(subset=cols)
            if valid_df.empty: return self.predict_gaussian(n)
            
            last_draw = valid_df.iloc[-1][cols].astype(int).tolist()
        except:
            return self.predict_gaussian(n)

        # 2. Construir bolsa de probabilidades
        # "Dado que salieron estos números, ¿qué suele salir después?"
        pool_weights = {}
        for num in last_draw:
            next_candidates = self.markov_matrix.get(num, [])
            for candidate in next_candidates:
                pool_weights[candidate] = pool_weights.get(candidate, 0) + 1
        
        # Si no hay historia suficiente para estos números
        if not pool_weights: return self.predict_gaussian(n)

        # 3. Selección ponderada
        candidates = list(pool_weights.keys())
        weights = list(pool_weights.values())
        
        # Normalizar pesos
        total_w = sum(weights)
        norm_w = [w/total_w for w in weights]
        
        # Elegir N números sin reposición
        # Si no hay suficientes candidatos (raro), rellenamos con aleatorios
        if len(candidates) < n:
            needed = n - len(candidates)
            others = [x for x in range(1,42) if x not in candidates]
            candidates.extend(random.sample(others, needed))
            norm_w.extend([0] * needed) # Peso 0 para los rellenados
            # Re-normalizar
            total_w = sum(weights) # Recalcular base
            if total_w > 0: norm_w = [w/total_w if i < len(weights) else 0 for i, w in enumerate(weights)] + [0]*needed
            else: norm_w = [1/len(candidates)] * len(candidates)

        # Selección final con numpy
        try:
            # Normalizar de nuevo por si acaso errores de flotante
            norm_w = np.array(norm_w)
            norm_w /= norm_w.sum()
            
            chosen = np.random.choice(candidates, size=n, replace=False, p=norm_w)
            return sorted(chosen.tolist())
        except:
             return sorted(random.sample(range(1, 42), n))

if __name__ == "__main__":
    # Test rápido
    forense = LotoForense()
    print("\n--- TEST DE PREDICCIÓN MULTI-MODELO ---")
    print(f"🔮 Biométrico: {forense.predict_numbers('LOTO')}")
    print(f"📐 Gaussiano:  {forense.predict_gaussian()}")
    print(f"📈 Delta:      {forense.predict_delta()}")
    print(f"🔗 Markov:     {forense.predict_markov()}")