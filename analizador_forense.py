import pandas as pd
import numpy as np
import json
import re
import os
from datetime import datetime

class LotoForense:
    def __init__(self, csv_path="LOTO_HISTORIAL_MAESTRO.csv"):
        self.csv_path = csv_path
        self.df = None
        self.structure = {} # Almacenará la estructura detectada de la base de datos
        self.stats_matrix = {} # Almacenará los pesos calculados
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 Inicializando LotoForense...")
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"❌ No se encontró el archivo maestro: {self.csv_path}")
        
        # Cargar CSV
        self.df = pd.read_csv(self.csv_path)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 📂 Datos cargados: {len(self.df)} sorteos históricos.")
        
        # Ejecutar detección de estructura
        self._detect_game_structure()

    def _detect_game_structure(self):
        """
        Escanea dinámicamente todas las columnas para identificar modalidades de juego.
        Busca patrones _n{d} y _pos{d} para agruparlos por prefijo (ej: JUBILAZO_1, DESQUITE).
        """
        columns = self.df.columns.tolist()
        game_map = {}

        # Expresión regular para capturar: NOMBRE_JUEGO + TIPO (n/pos) + INDICE (1-6)
        # Ejemplo: JUBILAZO_1_pos4 -> Grupo 1: JUBILAZO_1, Grupo 2: pos, Grupo 3: 4
        pattern = re.compile(r'^(.*)_(n|pos)(\d+)$')

        for col in columns:
            # 1. Chequeo de bolas normales y posiciones
            match = pattern.match(col)
            if match:
                prefix = match.group(1) # Ej: LOTO, RECARGADO, JUBILAZO_1
                type_ = match.group(2)  # 'n' o 'pos'
                idx = int(match.group(3)) # 1, 2, 3...

                if prefix not in game_map:
                    game_map[prefix] = {'n': {}, 'pos': {}, 'comodin': None}
                
                game_map[prefix][type_][idx] = col
                continue

            # 2. Chequeo de comodines
            if col.endswith('_comodin'):
                prefix = col.replace('_comodin', '')
                if prefix not in game_map:
                    game_map[prefix] = {'n': {}, 'pos': {}, 'comodin': None}
                game_map[prefix]['comodin'] = col

        self.structure = game_map
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 👁️  Estructura detectada ({len(game_map)} modalidades):")
        for mode in sorted(game_map.keys()):
            has_pos = len(game_map[mode]['pos']) > 0
            detail = "✅ Datos Físicos (POS)" if has_pos else "⚠️ Solo Ordenados (N)"
            print(f"   • {mode:<20} {detail}")

    def generate_mechanical_matrix(self):
        """
        Genera una matriz de probabilidades basada en la física de la extracción.
        Prioriza columnas '_pos' si existen.
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚙️  Calculando Matriz de Peso Mecánico...")
        
        report = {
            "metadata": {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_sorteos_analizados": len(self.df)
            },
            "games": {}
        }

        # Iterar sobre CADA modalidad descubierta (Loto, Desquite, Jubilazos...)
        for mode, cols in self.structure.items():
            
            # Determinar si usamos datos mecánicos (pos) o estadísticos (n)
            use_pos = len(cols['pos']) > 0
            source_type = 'pos' if use_pos else 'n'
            target_cols = cols[source_type] # Diccionario {1: 'col_name', 2: 'col_name'...}

            if not target_cols:
                continue

            mode_data = {
                "source_type": "MECHANICAL" if use_pos else "SORTED",
                "positions": {},
                "global_heat": {} # Frecuencia global del número en este juego sin importar posición
            }

            # Contadores globales para este juego
            global_counts = pd.Series(dtype=int)

            # Analizar cada posición (1 a 6 típicamente)
            for pos_idx in sorted(target_cols.keys()):
                col_name = target_cols[pos_idx]
                
                # Obtener frecuencia de valores (1-41)
                # value_counts() devuelve cuantos veces salió cada número
                vc = self.df[col_name].value_counts()
                
                # Sumar al global
                global_counts = global_counts.add(vc, fill_value=0)

                # Convertir a dict nativo (int: int)
                freq_dict = {int(k): int(v) for k, v in vc.items()}
                
                # Calcular "Frecuencia Relativa" (Probabilidad histórica)
                total_valid_draws = self.df[col_name].count()
                prob_dict = {k: round(v / total_valid_draws, 5) for k, v in freq_dict.items()}

                mode_data["positions"][pos_idx] = {
                    "col_name": col_name,
                    "counts": freq_dict,
                    "weights": prob_dict,
                    "most_frequent": int(vc.idxmax()) if not vc.empty else None
                }

            # Procesar Comodín si existe
            if cols['comodin']:
                c_col = cols['comodin']
                vc_c = self.df[c_col].value_counts()
                mode_data["comodin"] = {
                    "col_name": c_col,
                    "counts": {int(k): int(v) for k, v in vc_c.items()}
                }

            # Guardar mapa de calor global de este juego
            global_counts = global_counts.sort_values(ascending=False)
            mode_data["global_heat"] = {int(k): int(v) for k, v in global_counts.items()}

            report["games"][mode] = mode_data

        self.stats_matrix = report
        return report

    def save_intelligence(self, filename="loto_biometrics.json"):
        """Guarda el análisis completo en un JSON para ser consumido por el Dashboard/Frontend"""
        if not self.stats_matrix:
            self.generate_mechanical_matrix()
            
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.stats_matrix, f, indent=2)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Inteligencia guardada en '{filename}' ({os.path.getsize(filename)/1024:.1f} KB)")

    def get_quick_stats(self, game_mode, number):
        """Consulta rápida para verificar datos desde Python"""
        game_data = self.stats_matrix.get("games", {}).get(game_mode)
        if not game_data:
            return f"No hay datos para {game_mode}"
        
        total_hits = game_data.get("global_heat", {}).get(number, 0)
        return f"El número {number} ha salido {total_hits} veces en {game_mode}."

# ==========================================
# EJECUCIÓN DEL ANÁLISIS
# ==========================================
if __name__ == "__main__":
    # 1. Instanciar el forense
    forense = LotoForense()
    
    # 2. Generar la matriz
    matrix = forense.generate_mechanical_matrix()
    
    # 3. Guardar el archivo JSON para el dashboard
    forense.save_intelligence("loto_biometrics.json")
    
    # 4. (Opcional) Verificación rápida en consola
    print("\n--- Verificación Rápida ---")
    print(forense.get_quick_stats("LOTO", 33))
    print(forense.get_quick_stats("REVANCHA", 33))
    if "JUBILAZO_1" in matrix["games"]:
        print(forense.get_quick_stats("JUBILAZO_1", 33))