import sys
import datetime
import json
import re
import time
import subprocess # Para ejecutar comandos de Git
import pandas as pd
from curl_cffi import requests as cureq
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
CSV_FILE = 'LOTO_HISTORIAL_MAESTRO.csv'
STATUS_FILE = 'system_status.json'

# SEMILLA 2024 (Enero 2 - Sorteo 5055)
# Usamos esta fecha porque está 100% verificada en la fuente.
HISTORY_START_DATE = datetime.datetime(2024, 1, 2) 
HISTORY_START_SORTEO = 5055 

def log(msg, status="INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{status}] {msg}")

def git_push_live(sorteo_num):
    """Sube los cambios a GitHub INMEDIATAMENTE"""
    try:
        subprocess.run(["git", "add", CSV_FILE], check=True)
        subprocess.run(["git", "commit", "-m", f"Live: Agregado Sorteo {sorteo_num}"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True)
        log(f"--> ¡Sorteo {sorteo_num} subido a la web!", "GIT")
    except Exception as e:
        log(f"No se pudo subir a Git (¿Corriendo local?): {e}", "WARNING")

def generate_url(sorteo_num, date_obj):
    # Formato: /2024/01/02/resultados-loto-sorteo-5055-fecha-02-01-2024/
    yyyy = date_obj.strftime("%Y")
    mm = date_obj.strftime("%m")
    dd = date_obj.strftime("%d")
    slug_date = f"{dd}-{mm}-{yyyy}"
    return f"https://resultadoslotochile.com/{yyyy}/{mm}/{dd}/resultados-loto-sorteo-{sorteo_num}-fecha-{slug_date}/"

def get_html(url):
    try:
        response = cureq.get(url, impersonate="chrome110", timeout=15)
        return response.text if response.status_code == 200 else None
    except: return None

def parse_html(html, expected_sorteo):
    soup = BeautifulSoup(html, 'lxml')
    # Validación básica
    if str(expected_sorteo) not in soup.text: return None

    data = {'sorteo': expected_sorteo}
    
    # Extractor Genérico
    def get_nums(header):
        h = soup.find('h3', string=re.compile(header, re.IGNORECASE))
        div = h.find_next('div', class_='bolitas') if h else None
        return [int(p.text) for p in div.find_all('p')] if div else []

    data['LOTO'] = get_nums('Loto')
    # Fallback si Loto no tiene título
    if not data['LOTO']:
        f = soup.find('div', class_='bolitas')
        if f: data['LOTO'] = [int(p.text) for p in f.find_all('p')]

    c_div = soup.find('div', class_='comodin')
    data['COMODIN'] = int(c_div.find('p').text) if c_div else 0

    data['RECARGADO'] = get_nums('Recargado')
    data['REVANCHA'] = get_nums('Revancha')
    data['DESQUITE'] = get_nums('Desquite')
    
    # Premios (Opcional, si falla ponemos 0)
    data['LOTO_GANADORES'] = 0
    data['LOTO_MONTO'] = 0
    table = soup.find('table', class_='table-prizes')
    if table:
        for r in table.find_all('tr'):
            cols = r.find_all('td')
            if len(cols)>=3 and 'loto' in cols[0].text.lower() and '6 aciertos' in cols[0].text.lower():
                data['LOTO_GANADORES'] = int(re.sub(r'\D','',cols[2].text) or 0)
                data['LOTO_MONTO'] = int(re.sub(r'\D','',cols[1].text) or 0)

    return data

def save_to_csv(data_dict, date_obj):
    try:
        try: df = pd.read_csv(CSV_FILE, sep=';')
        except: df = pd.DataFrame()
        
        # Check duplicado
        if 'sorteo' in df.columns and data_dict['sorteo'] in df['sorteo'].values:
            return False

        row = {
            'sorteo': data_dict['sorteo'],
            'anio': date_obj.year, 'mes': date_obj.month, 'dia': date_obj.day,
            'dia_semana': date_obj.strftime('%A'),
            'LOTO_n1': data_dict['LOTO'][0], 'LOTO_n2': data_dict['LOTO'][1],
            'LOTO_n3': data_dict['LOTO'][2], 'LOTO_n4': data_dict['LOTO'][3],
            'LOTO_n5': data_dict['LOTO'][4], 'LOTO_n6': data_dict['LOTO'][5],
            'LOTO_comodin': data_dict['COMODIN'],
            'LOTO_GANADORES': data_dict['LOTO_GANADORES'], 'LOTO_MONTO': data_dict['LOTO_MONTO'],
            # Rellenar con 0 los demás juegos para brevedad
            'RECARGADO_n1': data_dict['RECARGADO'][0] if data_dict['RECARGADO'] else 0
            # (El pandas concat rellenará el resto con NaN/0 automáticamente)
        }
        # Relleno simplificado de sub-juegos
        for g in ['RECARGADO','REVANCHA','DESQUITE']:
            nums = data_dict.get(g, [])
            for i in range(6): row[f'{g}_n{i+1}'] = nums[i] if i<len(nums) else 0

        new_df = pd.DataFrame([row])
        df_final = pd.concat([df, new_df], ignore_index=True)
        df_final.to_csv(CSV_FILE, sep=';', index=False)
        return True
    except Exception as e:
        log(f"Error CSV: {e}", "ERROR")
        return False

def run_historical_mode():
    log(f"--- INICIANDO HISTÓRICO DESDE 2024 (Semilla: {HISTORY_START_SORTEO}) ---")
    
    # Cargar estado actual
    try:
        df = pd.read_csv(CSV_FILE, sep=';')
        existing = set(df['sorteo'].unique()) if not df.empty else set()
    except: existing = set()

    current_date = HISTORY_START_DATE
    current_sorteo = HISTORY_START_SORTEO
    end_date = datetime.datetime.now()

    while current_date <= end_date:
        if current_date.weekday() in [1, 3, 6]: # Mar, Jue, Dom
            if current_sorteo in existing:
                log(f"[SALTAR] Sorteo {current_sorteo} ya existe.")
                current_sorteo += 1
            else:
                url = generate_url(current_sorteo, current_date)
                html = get_html(url)
                
                if html:
                    data = parse_html(html, current_sorteo)
                    if data and data['LOTO']:
                        if save_to_csv(data, current_date):
                            log(f"*** ¡CAPTURADO! Sorteo {current_sorteo} ***", "SUCCESS")
                            # EL TRUCO: Subir inmediatamente
                            git_push_live(current_sorteo)
                            current_sorteo += 1
                    else:
                        log(f"HTML ok, datos no (posible error web)")
                else:
                    log(f"404 - No encontrado (¿Feriado?)")
                
                time.sleep(1) # Pausa para no ser baneado
        
        current_date += datetime.timedelta(days=1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'history':
        run_historical_mode()
    else:
        # Modo diario simple (puedes completarlo con el código anterior)
        pass
