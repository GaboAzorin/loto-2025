import re
import datetime
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
INPUT_FILE = "pegue_html_aqui.txt"

def parse_financial_data(soup, data_dict):
    """Lógica de extracción financiera idéntica al scraper principal"""
    financial_targets = {
        'LOTO': ['loto 6 aciertos'],
        'SUPER_QUINA_5_ACIERTOS_COMODIN': ['súper quina', 'super quina'],
        'QUINA_5_ACIERTOS': ['quina 5 aciertos'],
        'SUPER_CUATERNA_4_ACIERTOS_COMODIN': ['súper cuaterna', 'super cuaterna'],
        'CUATERNA_4_ACIERTOS': ['cuaterna 4 aciertos'],
        'SUPER_TERNA_3_ACIERTOS_COMODIN': ['súper terna', 'super terna'],
        'TERNA_3_ACIERTOS': ['terna 3 aciertos'],
        'SUPER_DUPLA_2_ACIERTOS_COMODIN': ['súper dupla', 'super dupla'],
        'RECARGADO_6_ACIERTOS': ['recargado 6 aciertos'],
        'REVANCHA': ['revancha'],
        'DESQUITE': ['desquite']
    }

    # Inicializar en 0
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
            # Limpieza agresiva de caracteres no numéricos
            monto = int(re.sub(r'\D', '', cols[1].get_text(strip=True)) or 0)
            ganadores = int(re.sub(r'\D', '', cols[2].get_text(strip=True)) or 0)

            for db_key, search_terms in financial_targets.items():
                if any(term in cat_text for term in search_terms):
                    # Filtros anti-colisión (Crucial)
                    if db_key == 'QUINA_5_ACIERTOS' and 'súper' in cat_text: continue
                    if db_key == 'CUATERNA_4_ACIERTOS' and 'súper' in cat_text: continue
                    if db_key == 'TERNA_3_ACIERTOS' and 'súper' in cat_text: continue
                    
                    data_dict[f'{db_key}_GANADORES'] = ganadores
                    data_dict[f'{db_key}_MONTO'] = monto
                    break
    return data_dict

def generate_line():
    print(f"--- LECTOR MANUAL DE HTML ---")
    print(f"Leyendo archivo: {INPUT_FILE}...")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"ERROR: No existe el archivo '{INPUT_FILE}'. Créalo y pega el HTML dentro.")
        return

    # 1. Pedir ID manual para evitar errores
    try:
        sorteo_input = input(">> Ingrese el NÚMERO DE SORTEO de este HTML: ")
        sorteo_num = int(sorteo_input)
    except ValueError:
        print("Error: Debes ingresar un número entero.")
        return

    soup = BeautifulSoup(html_content, 'lxml')
    data = {'sorteo': sorteo_num}

    # 2. Fecha
    meta_date = soup.find('meta', property='article:published_time')
    if meta_date:
        try:
            dt = datetime.datetime.fromisoformat(meta_date['content'])
            data.update({'anio': dt.year, 'mes': dt.month, 'dia': dt.day, 'dia_semana': dt.strftime('%A')})
        except: pass
    
    if 'anio' not in data:
        print("ADVERTENCIA: No se encontró fecha en meta tags. Usando fecha de hoy.")
        now = datetime.datetime.now()
        data.update({'anio': now.year, 'mes': now.month, 'dia': now.day, 'dia_semana': now.strftime('%A')})

    # 3. Bolitas
    def get_nums(header_regex):
        h = soup.find(['h3', 'h2'], string=re.compile(header_regex, re.IGNORECASE))
        if not h: return []
        div = h.find_next('div', class_='bolitas')
        return [int(p.text) for p in div.find_all('p') if p.text.strip().isdigit()] if div else []

    data['LOTO'] = get_nums('Loto')
    # Fallback
    if not data['LOTO']:
        div = soup.find('div', class_='bolitas')
        if div: data['LOTO'] = [int(p.text) for p in div.find_all('p')]

    if not data['LOTO']:
        print("ERROR FATAL: No se pudieron leer las bolitas del LOTO. Revisa el HTML.")
        return

    c_div = soup.find('div', class_='comodin')
    data['COMODIN'] = int(c_div.find('p').text) if c_div and c_div.find('p') else 0

    data['RECARGADO'] = get_nums('Recargado')
    data['REVANCHA'] = get_nums('Revancha')
    data['DESQUITE'] = get_nums('Desquite')
    
    # 4. Financiero
    data = parse_financial_data(soup, data)

    # 5. CONSTRUCCIÓN DE LA LÍNEA CSV (Orden Estricto)
    # Definimos el orden de columnas exacto de tu archivo maestro
    csv_order = [
        data['sorteo'],
        data['anio'], data['mes'], data['dia'], data['dia_semana'],
        # Loto nums
        data['LOTO'][0] if len(data['LOTO'])>0 else 0,
        data['LOTO'][1] if len(data['LOTO'])>1 else 0,
        data['LOTO'][2] if len(data['LOTO'])>2 else 0,
        data['LOTO'][3] if len(data['LOTO'])>3 else 0,
        data['LOTO'][4] if len(data['LOTO'])>4 else 0,
        data['LOTO'][5] if len(data['LOTO'])>5 else 0,
        data['COMODIN'],
        
        # Loto Money
        data['LOTO_GANADORES'], data['LOTO_MONTO'],
        
        # Quinas y Cuaternas
        data['SUPER_QUINA_5_ACIERTOS_COMODIN_GANADORES'], data['SUPER_QUINA_5_ACIERTOS_COMODIN_MONTO'],
        data['QUINA_5_ACIERTOS_GANADORES'], data['QUINA_5_ACIERTOS_MONTO'],
        data['SUPER_CUATERNA_4_ACIERTOS_COMODIN_GANADORES'], data['SUPER_CUATERNA_4_ACIERTOS_COMODIN_MONTO'],
        data['CUATERNA_4_ACIERTOS_GANADORES'], data['CUATERNA_4_ACIERTOS_MONTO'],
        data['SUPER_TERNA_3_ACIERTOS_COMODIN_GANADORES'], data['SUPER_TERNA_3_ACIERTOS_COMODIN_MONTO'],
        data['TERNA_3_ACIERTOS_GANADORES'], data['TERNA_3_ACIERTOS_MONTO'],
        data['SUPER_DUPLA_2_ACIERTOS_COMODIN_GANADORES'], data['SUPER_DUPLA_2_ACIERTOS_COMODIN_MONTO'],

        # Recargado Nums
        data['RECARGADO'][0] if len(data['RECARGADO'])>0 else 0,
        data['RECARGADO'][1] if len(data['RECARGADO'])>1 else 0,
        data['RECARGADO'][2] if len(data['RECARGADO'])>2 else 0,
        data['RECARGADO'][3] if len(data['RECARGADO'])>3 else 0,
        data['RECARGADO'][4] if len(data['RECARGADO'])>4 else 0,
        data['RECARGADO'][5] if len(data['RECARGADO'])>5 else 0,
        
        # Recargado Money
        data['RECARGADO_6_ACIERTOS_GANADORES'], data['RECARGADO_6_ACIERTOS_MONTO'],

        # Revancha Nums
        data['REVANCHA'][0] if len(data['REVANCHA'])>0 else 0,
        data['REVANCHA'][1] if len(data['REVANCHA'])>1 else 0,
        data['REVANCHA'][2] if len(data['REVANCHA'])>2 else 0,
        data['REVANCHA'][3] if len(data['REVANCHA'])>3 else 0,
        data['REVANCHA'][4] if len(data['REVANCHA'])>4 else 0,
        data['REVANCHA'][5] if len(data['REVANCHA'])>5 else 0,
        
        # Revancha Money
        data['REVANCHA_GANADORES'], data['REVANCHA_MONTO'],

        # Desquite Nums
        data['DESQUITE'][0] if len(data['DESQUITE'])>0 else 0,
        data['DESQUITE'][1] if len(data['DESQUITE'])>1 else 0,
        data['DESQUITE'][2] if len(data['DESQUITE'])>2 else 0,
        data['DESQUITE'][3] if len(data['DESQUITE'])>3 else 0,
        data['DESQUITE'][4] if len(data['DESQUITE'])>4 else 0,
        data['DESQUITE'][5] if len(data['DESQUITE'])>5 else 0,

        # Desquite Money
        data['DESQUITE_GANADORES'], data['DESQUITE_MONTO']
    ]

    # Convertir todo a string y unir con ;
    csv_line = ";".join(str(x) for x in csv_order)
    
    print("\n" + "="*50)
    print("COPIA LA SIGUIENTE LÍNEA EN TU CSV:")
    print("="*50)
    print(csv_line)
    print("="*50 + "\n")

if __name__ == "__main__":
    generate_line()