import sys
import datetime
import json
import re
import time
import pandas as pd
from curl_cffi import requests as cureq
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN MAESTRA ---
CSV_FILE = 'LOTO_HISTORIAL_MAESTRO.csv'
STATUS_FILE = 'system_status.json'
DEBUG_HTML_FILE = 'debug_view.html'

# Semilla Histórica (3 Enero 2016 - Sorteo Estimado 3806)
# NOTA: Ajusta 'START_SORTEO' si conoces el número exacto de ese día.
# Si no, el script intentará sincronizarse.
HISTORY_START_DATE = datetime.datetime(2016, 1, 3) 
HISTORY_START_SORTEO = 3806 # Valor aproximado para 2016, el script se ajusta si falla

def log(msg, status="INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{status}] {msg}")

def save_status(status, message):
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"status": status, "message": message, "updated": str(datetime.datetime.now())}, f)

def generate_url(sorteo_num, date_obj):
    """Construye la URL con precisión quirúrgica"""
    # Formato: /2025/11/20/resultados-loto-sorteo-5350-fecha-20-11-2025/
    yyyy = date_obj.strftime("%Y")
    mm = date_obj.strftime("%m")
    dd = date_obj.strftime("%d")
    
    slug_date = f"{dd}-{mm}-{yyyy}"
    url = f"https://resultadoslotochile.com/{yyyy}/{mm}/{dd}/resultados-loto-sorteo-{sorteo_num}-fecha-{slug_date}/"
    return url

def get_html(url):
    try:
        response = cureq.get(url, impersonate="chrome110", timeout=15)
        if response.status_code == 200:
            return response.text
        return None
    except:
        return None

def parse_html(html, expected_sorteo):
    """Extrae los datos usando la estructura conocida"""
    soup = BeautifulSoup(html, 'lxml')
    data = {'sorteo': expected_sorteo}
    
    # Validar que sea el sorteo correcto
    h1 = soup.find('h1')
    if not h1 or str(expected_sorteo) not in h1.get_text():
        return None # Falsa alarma o página incorrecta

    # Extractor de Bolas Helper
    def get_nums(header_pattern):
        header = soup.find('h3', string=re.compile(header_pattern, re.IGNORECASE))
        if header:
            div = header.find_next('div', class_=re.compile(r'bolitas|comodin'))
            if div:
                return [int(p.text) for p in div.find_all('p', class_='resultados')]
        return []

    data['LOTO'] = get_nums('Loto')
    # Fallback Loto (si no tiene h3)
    if not data['LOTO']:
        first_div = soup.find('div', class_='bolitas')
        if first_div: data['LOTO'] = [int(p.text) for p in first_div.find_all('p')]

    # Comodin
    comodin_div = soup.find('div', class_='comodin')
    data['COMODIN'] = int(comodin_div.find('p').text) if comodin_div else 0

    data['RECARGADO'] = get_nums('Recargado')
    data['REVANCHA'] = get_nums('Revancha')
    data['DESQUITE'] = get_nums('Desquite')

    # Premios
    table = soup.find('table', class_='table-prizes')
    data['LOTO_GANADORES'] = 0
    data['LOTO_MONTO'] = 0
    if table:
        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) >= 3 and 'loto' in cols[0].text.lower() and '6 aciertos' in cols[0].text.lower():
                gans = re.sub(r'\D', '', cols[2].text)
                monto = re.sub(r'\D', '', cols[1].text)
                data['LOTO_GANADORES'] = int(gans) if gans else 0
                data['LOTO_MONTO'] = int(monto) if monto else 0
                break
    
    return data

def save_to_csv(data_dict, date_obj):
    try:
        try:
            df = pd.read_csv(CSV_FILE, sep=';')
        except FileNotFoundError:
            df = pd.DataFrame()

        # Evitar duplicados
        if 'sorteo' in df.columns and data_dict['sorteo'] in df['sorteo'].values:
            return False

        row = {
            'sorteo': data_dict['sorteo'],
            'anio': date_obj.year,
            'mes': date_obj.month,
            'dia': date_obj.day,
            'dia_semana': date_obj.strftime('%A'),
            'LOTO_n1': data_dict['LOTO'][0] if len(data_dict['LOTO'])>0 else 0,
            'LOTO_n2': data_dict['LOTO'][1] if len(data_dict['LOTO'])>1 else 0,
            'LOTO_n3': data_dict['LOTO'][2] if len(data_dict['LOTO'])>2 else 0,
            'LOTO_n4': data_dict['LOTO'][3] if len(data_dict['LOTO'])>3 else 0,
            'LOTO_n5': data_dict['LOTO'][4] if len(data_dict['LOTO'])>4 else 0,
            'LOTO_n6': data_dict['LOTO'][5] if len(data_dict['LOTO'])>5 else 0,
            'LOTO_comodin': data_dict['COMODIN'],
            'LOTO_GANADORES': data_dict['LOTO_GANADORES'],
            'LOTO_MONTO': data_dict['LOTO_MONTO']
        }
        
        # Rellenar otros juegos
        for g in ['RECARGADO', 'REVANCHA', 'DESQUITE']:
            nums = data_dict.get(g, [])
            for i in range(6):
                row[f'{g}_n{i+1}'] = nums[i] if i < len(nums) else 0

        new_df = pd.DataFrame([row])
        df_final = pd.concat([df, new_df], ignore_index=True)
        df_final.to_csv(CSV_FILE, sep=';', index=False)
        return True
    except Exception as e:
        log(f"Error CSV: {e}", "ERROR")
        return False

# --- MOTORES DE TIEMPO ---

def run_daily_mode():
    log("--- MODO DIARIO (FRANCOTIRADOR) ---")
    try:
        df = pd.read_csv(CSV_FILE, sep=';')
        last_sorteo = int(df['sorteo'].max())
        # Buscamos el SIGUIENTE
        target_sorteo = last_sorteo + 1
    except:
        log("No hay CSV, imposible predecir siguiente sorteo.", "ERROR")
        return

    # Asumimos que HOY es el día del sorteo (ejecución 23:00)
    today = datetime.datetime.now()
    url = generate_url(target_sorteo, today)
    
    log(f"Apuntando a: {url}")
    html = get_html(url)
    
    if html:
        data = parse_html(html, target_sorteo)
        if data:
            if save_to_csv(data, today):
                log(f"¡DIANA! Sorteo {target_sorteo} capturado.", "SUCCESS")
                save_status("OK", f"Sorteo {target_sorteo} actualizado")
            else:
                log("Datos capturados pero ya existían en BD.")
        else:
            log("La URL cargó pero no se pudieron leer los datos (¿Estructura cambió?)", "WARNING")
            save_status("ERROR", "HTML leído sin datos")
    else:
        log("Tiro fallido (404). ¿Quizás no hubo sorteo hoy o cambió la URL?", "WARNING")
        save_status("WARNING", "404 - URL no encontrada hoy")

def run_historical_mode():
    log("--- MODO HISTÓRICO (RECONSTRUCCIÓN) ---")
    
    # Punteros iniciales
    current_date = HISTORY_START_DATE
    current_sorteo = HISTORY_START_SORTEO
    end_date = datetime.datetime.now()

    consecutive_fails = 0

    while current_date <= end_date:
        # Solo procesar Martes (1), Jueves (3), Domingo (6)
        wd = current_date.weekday()
        if wd in [1, 3, 6]:
            url = generate_url(current_sorteo, current_date)
            # log(f"Probando: {current_date.date()} - Sorteo {current_sorteo}")
            
            html = get_html(url)
            if html:
                data = parse_html(html, current_sorteo)
                if data:
                    save_to_csv(data, current_date)
                    log(f"[OK] {current_date.date()} | Sorteo {current_sorteo}")
                    consecutive_fails = 0
                    # Solo si tuvimos éxito incrementamos el sorteo esperado
                    current_sorteo += 1 
                else:
                     # HTML existe pero no es sorteo válido
                     log(f"[SKIP] HTML inválido {current_date.date()}")
            else:
                # 404 - Probablemente feriado o error de cálculo
                # No incrementamos sorteo, solo fecha
                consecutive_fails += 1
                # log(f"[404] No encontrado {current_date.date()}")

        # Avanzar al siguiente día
        current_date += datetime.timedelta(days=1)
        
        # Pausa de cortesía para no bloquear
        time.sleep(0.1)

if __name__ == "__main__":
    # Detección de argumentos para GitHub Actions
    if len(sys.argv) > 1 and sys.argv[1] == 'history':
        run_historical_mode()
    else:
        run_daily_mode()
