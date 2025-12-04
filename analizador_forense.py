import pandas as pd
import numpy as np
import json
import re
import os
import random
from datetime import datetime

class LotoForense:
    def __init__(self, csv_path="LOTO_HISTORIAL_MAESTRO.csv"):
        self.csv_path = csv_path
        self.df = None
        self.structure = {} 
        self.stats_matrix = {}
        self.past_combinations = set() # NUEVO: Memoria de jugadas pasadas para el Gaussiano
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 Inicializando LotoForense...")
        
        # 1. Intentar cargar biometría existente para ahorrar tiempo de cómputo
        # Esto es útil si el script corre cada 30 min
        if os.path.exists("loto_biometrics.json"):
            try:
                with open("loto_biometrics.json", "r", encoding='utf-8') as f:
                    self.stats_matrix = json.load(f)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧠 Biometría cargada desde JSON (Caché).")
            except:
                print("⚠️ Error leyendo JSON, se recalculará desde cero.")
        
        # Siempre cargamos datos para tener el historial disponible para el filtro Gaussiano
        self.load_data()
        
        # 2. Si no hay matriz en caché, calcular
        if not self.stats_matrix:
            self._detect_game_structure() # Asegurar que tenemos la estructura antes de calcular
            self.generate_mechanical_matrix()

    def load_data(self):
        if not os.path.exists(self.csv_path):
            # Si no existe el CSV, intentamos continuar sin datos (para modo predicción solo con JSON)
            print(f"⚠️ Advertencia: No se encontró {self.csv_path}. Se dependerá del JSON biométrico.")
            return

        self.df = pd.read_csv(self.csv_path)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📂 Datos cargados: {len(self.df)} sorteos históricos.")
        
        # --- NUEVO BLOQUE: Cargar historial de combinaciones para evitar repetirlas (Lógica Gaussiana) ---
        try:
            # Asumimos columnas LOTO_n1 a LOTO_n6 para verificar duplicados
            cols = [f'LOTO_n{i}' for i in range(1, 7)]
            # Filtrar filas válidas donde existan estos datos
            if all(c in self.df.columns for c in cols):
                valid_df = self.df.dropna(subset=cols)
                for _, row in valid_df.iterrows():
                    try:
                        # Creamos una tupla ordenada de los números ganadores pasados
                        nums = sorted([int(row[c]) for c in cols])
                        self.past_combinations.add(tuple(nums))
                    except:
                        continue
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📚 Historial Gaussiano: {len(self.past_combinations)} jugadas pasadas memorizadas.")
        except Exception as e:
            print(f"⚠️ Alerta menor: No se pudo cargar historial de combinaciones ({e})")
        # ------------------------------------------------------------------------------------------------

        # Ejecutar detección de estructura si no se ha hecho
        if not self.structure:
            self._detect_game_structure()

    def _detect_game_structure(self):
        """
        Escanea dinámicamente todas las columnas para identificar modalidades de juego.
        """
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

    def generate_mechanical_matrix(self):
        """
        Genera una matriz de probabilidades basada en la física de la extracción.
        """
        if self.df is None:
            self.load_data()
            if self.df is None: return {} # No se puede generar sin datos

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
                    "weights": prob_dict, # Usado para la predicción
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
        # Guardamos automáticamente al generar
        self.save_intelligence()
        return report

    def save_intelligence(self, filename="loto_biometrics.json"):
        if not self.stats_matrix:
            return
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.stats_matrix, f, indent=2)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Inteligencia guardada en '{filename}'")

    def get_quick_stats(self, game_mode, number):
        """Consulta rápida para verificar datos desde Python"""
        game_data = self.stats_matrix.get("games", {}).get(game_mode)
        if not game_data:
            return f"No hay datos para {game_mode}"
        total_hits = game_data.get("global_heat", {}).get(str(number), 0)
        return f"El número {number} ha salido {total_hits} veces en {game_mode}."

    # ==============================================================================
    # 🔮 MOTOR DE PREDICCIÓN BIOMÉTRICA (FÍSICA)
    # ==============================================================================
    def predict_numbers(self, game_mode="LOTO", n=6):
        """
        Genera una predicción utilizando Simulación Monte Carlo basada en pesos históricos.
        Respeta la exclusión física: una vez que sale una bola, no puede volver a salir en la misma jugada.
        """
        # Asegurar datos
        if not self.stats_matrix:
            print("⚠️ Matriz vacía. Intentando generar...")
            self.generate_mechanical_matrix()

        game_data = self.stats_matrix.get("games", {}).get(game_mode)
        
        # Fallback de seguridad si el modo de juego no existe
        if not game_data:
            print(f"⚠️ MODO '{game_mode}' NO ENCONTRADO. Usando aleatorio puro.")
            return sorted(random.sample(range(1, 42), n))

        prediction = []
        # Pool de números disponibles (1 al 41 para Loto Chile)
        full_pool = set(range(1, 42)) 
        
        # Simular extracción bolilla a bolilla (Posición 1 a n)
        for i in range(1, n + 1):
            pos_key = str(i)
            
            # Obtener los pesos específicos de ESTA posición física
            # (Ej: Qué suele salir en la primera bolilla)
            pos_data = game_data['positions'].get(pos_key, {})
            weights_map = pos_data.get('weights', {})
            
            # Preparar candidatos
            candidates = []
            probs = []
            
            # Números que NO han salido todavía en esta simulación
            available_numbers = full_pool - set(prediction)
            
            for num in available_numbers:
                num_str = str(num)
                # Peso histórico (si nunca salió, le damos un peso ínfimo épsilon para que sea posible pero improbable)
                weight = weights_map.get(num_str, 0.00001)
                
                candidates.append(num)
                probs.append(weight)
            
            # Re-normalizar probabilidades (Deben sumar 1.0)
            total_prob = sum(probs)
            if total_prob <= 0:
                normalized_probs = [1.0/len(candidates)] * len(candidates) # Uniforme si falla
            else:
                normalized_probs = [p / total_prob for p in probs]
            
            # Selección aleatoria ponderada (Weighted Random Choice)
            picked_number = np.random.choice(candidates, p=normalized_probs)
            prediction.append(int(picked_number))

        # El resultado final siempre se ordena ascendente para el usuario
        return sorted(prediction)

    # ==============================================================================
    # 📐 NUEVO: MOTOR DE PREDICCIÓN GAUSSIANA (ESTADÍSTICA / 'BOTÓN AMARILLO')
    # ==============================================================================
    def predict_gaussian(self, n=6):
        """
        Replica la lógica del 'Generador Cuántico' (Botón Amarillo):
        - Suma: 100-150
        - Pares: 2-4
        - No repetida en historia
        - Consecutivos: Max 2 seguidos (ej: 1,2 OK; 1,2,3 NO)
        """
        attempts = 0
        max_attempts = 5000
        
        while attempts < max_attempts:
            attempts += 1
            
            # 1. Generar aleatorio base (sin reposición)
            nums = sorted(random.sample(range(1, 42), n))
            
            # 2. Filtro de Suma (100 - 150)
            suma = sum(nums)
            if suma < 100 or suma > 150:
                continue
            
            # 3. Filtro de Paridad (2 a 4 pares)
            evens = len([x for x in nums if x % 2 == 0])
            if evens < 2 or evens > 4:
                continue
            
            # 4. Filtro Histórico (Inédita)
            # Verifica si la tupla de números ya existe en el historial cargado
            if tuple(nums) in self.past_combinations:
                continue
            
            # 5. Filtro Consecutivos (Max 1 pareja consecutiva)
            # Ej: 1,2,3 -> Rechazado (2 saltos seguidos). 1,2,5,6 -> Aceptado.
            consecutivos = 0
            max_consecutivos = 0
            for i in range(len(nums)-1):
                if nums[i+1] == nums[i] + 1:
                    consecutivos += 1
                else:
                    consecutivos = 0
                
                if consecutivos > max_consecutivos:
                    max_consecutivos = consecutivos
            
            if max_consecutivos >= 2: # Si hay 3 números seguidos (2 enlaces) o más
                continue
                
            # Si pasa todos los filtros, es una jugada válida
            return nums
            
        # Si falla demasiadas veces, devolvemos uno aleatorio para no romper el flujo
        print("⚠️ Advertencia: No se encontró combinación gaussiana perfecta. Devolviendo aleatorio.")
        return sorted(random.sample(range(1, 42), n))

if __name__ == "__main__":
    # Test rápido
    forense = LotoForense()
    print("\n--- TEST DE PREDICCIÓN ---")
    print(f"🔮 Biométrico: {forense.predict_numbers('LOTO')}")
    print(f"📐 Gaussiano:  {forense.predict_gaussian()}")