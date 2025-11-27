import json
import os
import re
import unicodedata
from datetime import datetime

def normalize_name(name):
    """
    Convierte 'AHORA SÍ QUE SÍ' -> 'AHORA_SI_QUE_SI'
    Quita acentos, espacios y caracteres raros para usarlos como columnas de BD.
    """
    if not name: return "UNKNOWN"
    # Normalizar unicode (quitar tildes)
    nfkd_form = unicodedata.normalize('NFKD', name)
    name_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Reemplazar espacios y guiones por _
    clean_name = re.sub(r'[^a-zA-Z0-9]', '_', name_ascii).upper()
    # Eliminar guiones bajos repetidos
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    return clean_name

def parse_loto_flat(data_source):
    """
    Parsea los datos del Loto y devuelve un diccionario PLANO.
    
    Args:
        data_source: Puede ser una ruta de archivo (str) O un diccionario ya cargado (dict).
                     ¡Esto evita tener que guardar archivos temporales!
    """
    data = {}
    
    # LÓGICA HÍBRIDA: Detectar si es Archivo o Memoria
    if isinstance(data_source, dict):
        data = data_source
    elif isinstance(data_source, str):
        if os.path.exists(data_source):
            with open(data_source, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            return {}
    else:
        return {}

    row = {}

    # --- 1. METADATA ---
    timestamp = data.get('drawDate')
    if timestamp:
        dt = datetime.fromtimestamp(timestamp / 1000)
        row['fecha'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        row['anio'] = dt.year
        row['mes'] = dt.month
        row['dia'] = dt.day
        row['dia_semana'] = dt.strftime('%A')

    row['sorteo'] = data.get('drawNumber')
    row['precio_carton'] = data.get('columnPrice')

    # --- 2. LOTO PRINCIPAL ---
    loto_raw = data.get('results', [])
    numeros_loto = []
    comodin = None

    for item in loto_raw:
        order = item.get('order')
        number = item.get('number')
        if order is not None:
            if 0 <= order <= 5:
                numeros_loto.append(int(number))
            elif order == 6:
                comodin = int(number)
    
    numeros_loto.sort()
    for i, num in enumerate(numeros_loto):
        row[f'LOTO_n{i+1}'] = num
    row['LOTO_comodin'] = comodin

    # --- 3. SUB-JUEGOS DINÁMICOS (La Magia) ---
    additional = data.get('additionalGameResults', [])
    
    for game in additional:
        original_name = game.get('gameName', 'OTRO')
        col_name = normalize_name(original_name)
        areas = game.get('areas', [])
        
        # Caso especial MULTIPLICAR
        if "MULTIPLICAR" in col_name:
            if areas and areas[0].get('winningNumbers'):
                nums = [int(n['number']) for n in areas[0].get('winningNumbers', [])]
                if nums:
                    row['MULTIPLICAR_FACTOR'] = nums[0]
            continue # Siguiente juego
            
        # Recolectar todos los sorteos válidos dentro de este juego
        sorteos_validos = []
        for area in areas:
            raw_nums = area.get('winningNumbers', [])
            if raw_nums: # Si tiene números
                nums = [int(n['number']) for n in raw_nums]
                nums.sort()
                sorteos_validos.append(nums)
        
        if not sorteos_validos:
            continue

        # Generar columnas dinámicamente
        if len(sorteos_validos) == 1:
            # Caso simple (Revancha, Desquite, Ahora Si Que Si) -> NOMBRE_n1...
            nums = sorteos_validos[0]
            for i, n in enumerate(nums):
                row[f'{col_name}_n{i+1}'] = n
        else:
            # Caso múltiple (Jubilazos) -> NOMBRE_1_n1, NOMBRE_2_n1...
            for idx, nums in enumerate(sorteos_validos):
                # idx + 1 para que sea JUBILAZO_1, JUBILAZO_2...
                prefix = f"{col_name}_{idx+1}"
                for i, n in enumerate(nums):
                    row[f'{prefix}_n{i+1}'] = n

    # --- 4. PREMIOS (Mapeo por IDs conocidos) ---
    # Nota: Los juegos viejos pueden no coincidir con estos IDs, 
    # pero los montos se mapean si el ID existe.
    cat_map = {
        1: "LOTO",
        2: "SUPER_QUINA_5_ACIERTOS_COMODIN",
        3: "QUINA_5_ACIERTOS",
        4: "SUPER_CUATERNA_4_ACIERTOS_COMODIN",
        5: "CUATERNA_4_ACIERTOS",
        6: "SUPER_TERNA_3_ACIERTOS_COMODIN",
        7: "TERNA_3_ACIERTOS",
        8: "SUPER_DUPLA_2_ACIERTOS_COMODIN",
        9: "RECARGADO_6_ACIERTOS",
        11: "REVANCHA",
        12: "DESQUITE"
    }

    raw_prizes = data.get('prizes', [])
    for p in raw_prizes:
        cat_id = p.get('id', {}).get('categoryCd')
        if cat_id in cat_map:
            col_prefix = cat_map[cat_id]
            row[f'{col_prefix}_GANADORES'] = p.get('winners', 0)
            row[f'{col_prefix}_MONTO'] = p.get('divident', 0)
            
            if cat_id in [1, 9, 11, 12]:
                 name_pozo = col_prefix.split("_")[0] + "_POZO_ACUMULADO"
                 if "LOTO" in name_pozo: name_pozo = "LOTO_POZO_ACUMULADO"
                 row[name_pozo] = p.get('jackpot', 0)

    return row

if __name__ == "__main__":
    # Bloque de prueba
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print("El parser está listo para ser importado por el scraper.")