import json
import os
import re
import unicodedata
from datetime import datetime

def normalize_name(name):
    if not name: return "UNKNOWN"
    nfkd_form = unicodedata.normalize('NFKD', str(name))
    name_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    clean_name = re.sub(r'[^a-zA-Z0-9]', '_', name_ascii).upper()
    return re.sub(r'_+', '_', clean_name).strip('_')

def parse_loto_rich(data_source):
    data = {}
    if isinstance(data_source, dict):
        data = data_source
    elif isinstance(data_source, str) and os.path.exists(data_source):
        with open(data_source, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        return {}

    row = {}
    game = data.get('game', {})
    
    # --- 1. METADATA (COMPATIBLE CON HTMLs) ---
    row['sorteo'] = game.get('drawNumber') or data.get('drawNumber')
    
    ts = data.get('drawDate')
    if ts:
        dt = datetime.fromtimestamp(ts / 1000)
        row['fecha'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        row['anio'] = dt.year
        row['mes'] = dt.month
        row['dia'] = dt.day
        row['dia_semana'] = dt.strftime('%A')

    # --- 2. DATOS ECONÓMICOS (NUEVO) ---
    ventas = data.get('sales') or game.get('sales') or 0
    precio = game.get('columnPrice') or 1000
    row['ventas_totales'] = ventas
    row['boletos_estimados'] = int(ventas / precio) if precio and ventas else 0

    # --- 3. EXTRACCIÓN DE NÚMEROS Y ORDEN ---
    # Combinamos 'results' y 'additionalGameResults' porque a veces Polla los separa
    results_main = data.get('results', [])
    results_add = data.get('additionalGameResults', [])
    all_results = results_main + results_add

    # Mapeo de nombres de JUEGO (Prefijos de columnas de números)
    # Lógica: Buscar palabras clave en el nombre del juego
    keywords = {
        'RECARGADO': 'RECARGADO', # Prioridad alta
        'LOTO': 'LOTO',
        'REVANCHA': 'REVANCHA',
        'DESQUITE': 'DESQUITE',
        'AHORA': 'AHORA_SI_QUE_SI',
        'JUBILAZO': 'JUBILAZO',
        'MULTIPLICAR': 'MULTIPLICAR'
    }
    
    jubilazo_counter = 1

    for area in all_results:
        raw_name = area.get('gameName', 'UNKNOWN').upper()
        
        prefix = "OTRO"
        found_key = False
        for key, val in keywords.items():
            if key in raw_name:
                prefix = val
                found_key = True
                break
        
        # Manejo de múltiples Jubilazos para no sobrescribir
        if prefix == 'JUBILAZO':
            prefix = f'JUBILAZO_{jubilazo_counter}'
            jubilazo_counter += 1

        winning_nums = area.get('winningNumbers', [])
        if not winning_nums: continue

        # --- A) ORDEN FÍSICO (Para IA) ---
        # Ordenamos por 'order' si existe, sino confiamos en el orden de la lista
        ordenados_por_salida = sorted(winning_nums, key=lambda x: x.get('order', 999))
        valores_salida = [int(n.get('number')) for n in ordenados_por_salida]

        for i, val in enumerate(valores_salida):
            row[f'{prefix}_pos{i+1}'] = val

        # --- B) ORDEN NUMÉRICO (Para index.html) ---
        valores_numericos = sorted(valores_salida)
        for i, val in enumerate(valores_numericos):
            row[f'{prefix}_n{i+1}'] = val
            
        # Comodín
        supp = area.get('supplementaryNumbers')
        if supp:
            row[f'{prefix}_comodin'] = supp[0].get('number')

    # --- 4. PREMIOS (Mapeo por ID Estricto) ---
    # Mapa basado en tu parser_v3 y en la estructura histórica de Polla
    # ID -> Nombre de columna Legacy (v3)
    CAT_ID_MAP = {
        1: "LOTO",
        2: "SUPER_QUINA_5_ACIERTOS_COMODIN",
        3: "QUINA_5_ACIERTOS",
        4: "SUPER_CUATERNA_4_ACIERTOS_COMODIN",
        5: "CUATERNA_4_ACIERTOS",
        6: "SUPER_TERNA_3_ACIERTOS_COMODIN",
        7: "TERNA_3_ACIERTOS",
        8: "SUPER_DUPLA_2_ACIERTOS_COMODIN",
        9: "RECARGADO_6_ACIERTOS", # Nombre exacto de v3
        11: "REVANCHA",
        12: "DESQUITE"
        # IDs 13+ suelen ser Jubilazos o variantes, los ignoramos en el CSV maestro ancho
        # para no generar cientos de columnas, a menos que tu html los pida.
    }

    prizes = data.get('prizes', [])
    
    for p in prizes:
        # Obtenemos ID de categoría de forma segura
        cat_id = p.get('id', {}).get('categoryCd')
        
        col_prefix = CAT_ID_MAP.get(cat_id)

        # Fallback: Si no está en el mapa de IDs, intentamos normalizar el nombre (si existe)
        if not col_prefix:
            cat_name = p.get('name') or p.get('categoryName')
            if cat_name:
                norm = normalize_name(cat_name)
                # Intento de matchear nombres si el ID cambió (ej: Ahora Si Que Si antiguos)
                if 'AHORA' in norm: col_prefix = 'AHORA_SI_QUE_SI'
                elif 'JUBILAZO' in norm: continue # Saltamos premios detallados de jubilazo por limpieza

        if col_prefix:
            row[f'{col_prefix}_GANADORES'] = p.get('winners', 0)
            row[f'{col_prefix}_MONTO'] = p.get('prizePerWinner', 0) or p.get('winningAmount', 0)

    # Pozo acumulado
    row['LOTO_POZO_ACUMULADO'] = data.get('poolAccumulated', 0) or data.get('jackpotAmount', 0)

    return row