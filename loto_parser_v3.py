import json
import os
import re
import unicodedata
from datetime import datetime

def normalize_name(name):
    if not name: return "UNKNOWN"
    nfkd_form = unicodedata.normalize('NFKD', name)
    name_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    clean_name = re.sub(r'[^a-zA-Z0-9]', '_', name_ascii).upper()
    return re.sub(r'_+', '_', clean_name).strip('_')

def parse_loto_flat(data_source):
    data = {}
    if isinstance(data_source, dict):
        data = data_source
    elif isinstance(data_source, str):
        if os.path.exists(data_source):
            with open(data_source, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else: return {}
    else: return {}

    row = {}

    # --- METADATA ---
    timestamp = data.get('drawDate')
    if timestamp:
        dt = datetime.fromtimestamp(timestamp / 1000)
        row['fecha'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        row['anio'] = dt.year
        row['mes'] = dt.month
        row['dia'] = dt.day
        row['dia_semana'] = dt.strftime('%A') # Puedes traducir esto si quieres

    row['sorteo'] = data.get('drawNumber')
    # precio_carton eliminado según tu solicitud

    # --- LOTO (Orden de Extracción) ---
    loto_raw = data.get('results', [])
    loto_pairs = []
    wild = None

    for item in loto_raw:
        order = item.get('order')
        number = item.get('number')
        if order is not None:
            if 0 <= order <= 5:
                # Guardamos la tupla (orden, numero)
                loto_pairs.append((order, int(number)))
            elif order == 6:
                wild = int(number)
    
    # Ordenamos por el índice de salida (0, 1, 2...), NO por valor
    loto_pairs.sort(key=lambda x: x[0])
    
    # Rellenamos n1..n6
    for i, pair in enumerate(loto_pairs):
        row[f'LOTO_n{i+1}'] = pair[1]
        
    row['LOTO_comodin'] = wild

    # --- SUB-JUEGOS ---
    additional = data.get('additionalGameResults', [])
    for game in additional:
        original_name = game.get('gameName', 'OTRO')
        col_name = normalize_name(original_name)
        areas = game.get('areas', [])
        
        if "MULTIPLICAR" in col_name:
            if areas and areas[0].get('winningNumbers'):
                n = [int(x['number']) for x in areas[0].get('winningNumbers', [])]
                if n: row['MULTIPLICAR_FACTOR'] = n[0]
            continue
            
        valid_sets = []
        for area in areas:
            raw_nums = area.get('winningNumbers', [])
            if raw_nums:
                # Aquí también ordenamos por 'order' para respetar la tómbola
                sorted_raw = sorted(raw_nums, key=lambda x: x.get('order', 0))
                n = [int(x['number']) for x in sorted_raw]
                valid_sets.append(n)
        
        if not valid_sets: continue

        if len(valid_sets) == 1:
            for i, n in enumerate(valid_sets[0]):
                row[f'{col_name}_n{i+1}'] = n
        else:
            for idx, s in enumerate(valid_sets):
                prefix = f"{col_name}_{idx+1}"
                for i, n in enumerate(s):
                    row[f'{prefix}_n{i+1}'] = n

    # --- PREMIOS ---
    # IDs según tu JSON
    cat_map = {
        1: "LOTO", 2: "SUPER_QUINA_5_ACIERTOS_COMODIN", 3: "QUINA_5_ACIERTOS",
        4: "SUPER_CUATERNA_4_ACIERTOS_COMODIN", 5: "CUATERNA_4_ACIERTOS",
        6: "SUPER_TERNA_3_ACIERTOS_COMODIN", 7: "TERNA_3_ACIERTOS",
        8: "SUPER_DUPLA_2_ACIERTOS_COMODIN", 9: "RECARGADO_6_ACIERTOS",
        11: "REVANCHA", 12: "DESQUITE"
    }
    # Intentamos mapear "Ahora si que si" si aparece con ID nuevo
    # Por ahora usará el nombre genérico si no tiene ID conocido

    raw_prizes = data.get('prizes', [])
    for p in raw_prizes:
        cat_id = p.get('id', {}).get('categoryCd')
        
        # Lógica especial para AHORA SI QUE SI (suele usar IDs 15, 16, 17 en esa época, o similares)
        # Si no está en el mapa, lo intentamos inferir o lo dejamos pasar
        
        if cat_id in cat_map:
            col_prefix = cat_map[cat_id]
            row[f'{col_prefix}_GANADORES'] = p.get('winners', 0)
            row[f'{col_prefix}_MONTO'] = p.get('divident', 0)
            
            # Acumulados para los juegos principales
            if cat_id in [1, 9, 11, 12]:
                 name_pozo = col_prefix.split("_")[0] + "_POZO_ACUMULADO"
                 if "LOTO" in name_pozo: name_pozo = "LOTO_POZO_ACUMULADO"
                 row[name_pozo] = p.get('jackpot', 0)

    return row