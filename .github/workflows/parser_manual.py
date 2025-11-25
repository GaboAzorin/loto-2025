import re
import datetime
import subprocess
import platform
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
INPUT_FILE = "pegue_html_aqui.txt"

# --- SEMILLA DE TIEMPO (Sorteo Conocido) ---
SEED_SORTEO = 5210
SEED_DATE = datetime.datetime(2024, 12, 29) # Año, Mes, Día

def copy_to_clipboard(text):
    """
    Copia texto al portapapeles usando comandos nativos del sistema.
    Funciona en Windows, Mac y Linux (con xclip).
    """
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run("clip", input=text.strip().encode('utf-16'), check=True)
            print(">> [CLIPBOARD] ¡Línea copiada exitosamente al portapapeles!")
        elif system == "Darwin": # Mac
            subprocess.run("pbcopy", input=text.strip().encode('utf-8'), check=True)
            print(">> [CLIPBOARD] ¡Línea copiada exitosamente al portapapeles!")
        else: # Linux
            try:
                subprocess.run(["xclip", "-selection", "clipboard"], input=text.strip().encode('utf-8'), check=True)
                print(">> [CLIPBOARD] ¡Línea copiada exitosamente al portapapeles!")
            except FileNotFoundError:
                print(">> [AVISO] No se encontró 'xclip'. Instálalo para usar el portapapeles automático, o copia manualmente.")
    except Exception as e:
        print(f">> [ERROR] No se pudo copiar al portapapeles: {e}")

def calculate_date(target_sorteo):
    delta = target_sorteo - SEED_SORTEO
    weeks = delta // 3
    remainder = delta % 3
    days_to_add = weeks * 7
    if remainder == 1: days_to_add += 2
    elif remainder == 2: days_to_add += 4
    return SEED_DATE + datetime.timedelta(days=days_to_add)

def parse_financial_data(soup, data_dict):
    financial_targets = {
        'LOTO': ['loto'], 
        'SUPER_QUINA_5_ACIERTOS_COMODIN': ['súper quina', 'super quina'],
        'QUINA_5_ACIERTOS': ['quina'], 
        'SUPER_CUATERNA_4_ACIERTOS_COMODIN': ['súper cuaterna', 'super cuaterna'],
        'CUATERNA_4_ACIERTOS': ['cuaterna'],
        'SUPER_TERNA_3_ACIERTOS_COMODIN': ['súper terna', 'super terna'],
        'TERNA_3_ACIERTOS': ['terna'], 
        'SUPER_DUPLA_2_ACIERTOS_COMODIN': ['súper dupla', 'super dupla', 'dupla'],
        'RECARGADO_6_ACIERTOS': ['recargado'],
        'REVANCHA': ['revancha'],
        'DESQUITE': ['desquite']
    }

    for key in financial_targets:
        data_dict[f'{key}_GANADORES'] = 0
        data_dict[f'{key}_MONTO'] = 0

    table = soup.find('table', class_='table-prizes')
    if not table:
        print("ADVERTENCIA: No se encontró la tabla de premios.")
        return data_dict

    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) >= 3:
            cat_text = cols[0].get_text(" ", strip=True).lower()
            monto = int(re.sub(r'\D', '', cols[1].get_text(strip=True)) or 0)
            ganadores = int(re.sub(r'\D', '', cols[2].get_text(strip=True)) or 0)

            for db_key, search_terms in financial_targets.items():
                if any(term in cat_text for term in search_terms):
                    if db_key == 'LOTO':
                        if 'recargado' in cat_text or 'revancha' in cat_text or 'desquite' in cat_text: continue
                    if db_key == 'QUINA_5_ACIERTOS' and 'súper' in cat_text: continue
                    if db_key == 'CUATERNA_4_ACIERTOS' and 'súper' in cat_text: continue
                    if db_key == 'TERNA_3_ACIERTOS' and 'súper' in cat_text: continue
                    
                    data_dict[f'{db_key}_GANADORES'] = ganadores
                    data_dict[f'{db_key}_MONTO'] = monto
                    break
    return data_dict

def generate_line():
    print(f"--- LECTOR MANUAL DE HTML (V4: AUTO-CLIPBOARD) ---")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"ERROR: No existe '{INPUT_FILE}'.")
        return

    try:
        sorteo_input = input(">> Ingrese el NÚMERO DE SORTEO: ")
        sorteo_num = int(sorteo_input)
    except ValueError:
        print("Error: Número inválido.")
        return

    soup = BeautifulSoup(html_content, 'lxml')
    data = {'sorteo': sorteo_num}

    calc_date = calculate_date(sorteo_num)
    data.update({
        'anio': calc_date.year, 'mes': calc_date.month, 'dia': calc_date.day,
        'dia_semana': calc_date.strftime('%A')
    })
    
    print(f"-> Fecha: {data['dia']}/{data['mes']}/{data['anio']} ({data['dia_semana']})")

    def get_nums(header_regex):
        h = soup.find(['h3', 'h2'], string=re.compile(header_regex, re.IGNORECASE))
        if not h: return []
        div = h.find_next('div', class_='bolitas')
        return [int(p.text) for p in div.find_all('p') if p.text.strip().isdigit()] if div else []

    data['LOTO'] = get_nums('Loto')
    if not data['LOTO']:
        div = soup.find('div', class_='bolitas')
        if div: data['LOTO'] = [int(p.text) for p in div.find_all('p')]

    if not data['LOTO']:
        print("ERROR FATAL: Sin bolitas LOTO.")
        return

    c_div = soup.find('div', class_='comodin')
    data['COMODIN'] = int(c_div.find('p').text) if c_div and c_div.find('p') else 0
    data['RECARGADO'] = get_nums('Recargado')
    data['REVANCHA'] = get_nums('Revancha')
    data['DESQUITE'] = get_nums('Desquite')
    data = parse_financial_data(soup, data)

    csv_order = [
        data['sorteo'], data['anio'], data['mes'], data['dia'], data['dia_semana'],
        data['LOTO'][0] if len(data['LOTO'])>0 else 0,
        data['LOTO'][1] if len(data['LOTO'])>1 else 0,
        data['LOTO'][2] if len(data['LOTO'])>2 else 0,
        data['LOTO'][3] if len(data['LOTO'])>3 else 0,
        data['LOTO'][4] if len(data['LOTO'])>4 else 0,
        data['LOTO'][5] if len(data['LOTO'])>5 else 0,
        data['COMODIN'],
        data['LOTO_GANADORES'], data['LOTO_MONTO'],
        data['SUPER_QUINA_5_ACIERTOS_COMODIN_GANADORES'], data['SUPER_QUINA_5_ACIERTOS_COMODIN_MONTO'],
        data['QUINA_5_ACIERTOS_GANADORES'], data['QUINA_5_ACIERTOS_MONTO'],
        data['SUPER_CUATERNA_4_ACIERTOS_COMODIN_GANADORES'], data['SUPER_CUATERNA_4_ACIERTOS_COMODIN_MONTO'],
        data['CUATERNA_4_ACIERTOS_GANADORES'], data['CUATERNA_4_ACIERTOS_MONTO'],
        data['SUPER_TERNA_3_ACIERTOS_COMODIN_GANADORES'], data['SUPER_TERNA_3_ACIERTOS_COMODIN_MONTO'],
        data['TERNA_3_ACIERTOS_GANADORES'], data['TERNA_3_ACIERTOS_MONTO'],
        data['SUPER_DUPLA_2_ACIERTOS_COMODIN_GANADORES'], data['SUPER_DUPLA_2_ACIERTOS_COMODIN_MONTO'],
        data['RECARGADO'][0] if len(data['RECARGADO'])>0 else 0,
        data['RECARGADO'][1] if len(data['RECARGADO'])>1 else 0,
        data['RECARGADO'][2] if len(data['RECARGADO'])>2 else 0,
        data['RECARGADO'][3] if len(data['RECARGADO'])>3 else 0,
        data['RECARGADO'][4] if len(data['RECARGADO'])>4 else 0,
        data['RECARGADO'][5] if len(data['RECARGADO'])>5 else 0,
        data['RECARGADO_6_ACIERTOS_GANADORES'], data['RECARGADO_6_ACIERTOS_MONTO'],
        data['REVANCHA'][0] if len(data['REVANCHA'])>0 else 0,
        data['REVANCHA'][1] if len(data['REVANCHA'])>1 else 0,
        data['REVANCHA'][2] if len(data['REVANCHA'])>2 else 0,
        data['REVANCHA'][3] if len(data['REVANCHA'])>3 else 0,
        data['REVANCHA'][4] if len(data['REVANCHA'])>4 else 0,
        data['REVANCHA'][5] if len(data['REVANCHA'])>5 else 0,
        data['REVANCHA_GANADORES'], data['REVANCHA_MONTO'],
        data['DESQUITE'][0] if len(data['DESQUITE'])>0 else 0,
        data['DESQUITE'][1] if len(data['DESQUITE'])>1 else 0,
        data['DESQUITE'][2] if len(data['DESQUITE'])>2 else 0,
        data['DESQUITE'][3] if len(data['DESQUITE'])>3 else 0,
        data['DESQUITE'][4] if len(data['DESQUITE'])>4 else 0,
        data['DESQUITE'][5] if len(data['DESQUITE'])>5 else 0,
        data['DESQUITE_GANADORES'], data['DESQUITE_MONTO']
    ]

    csv_line = ";".join(str(x) for x in csv_order)
    
    # --- COPIA AL PORTAPAPELES ---
    copy_to_clipboard(csv_line)
    
    print("\n" + "="*50)
    print("RESULTADO:")
    print("="*50)
    print(csv_line)
    print("="*50 + "\n")

if __name__ == "__main__":
    generate_line()