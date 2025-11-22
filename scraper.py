import sys
import datetime
import json
import re
import time
import subprocess
import pandas as pd
from curl_cffi import requests as cureq
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
CSV_FILE = 'LOTO_HISTORIAL_MAESTRO.csv'
STATUS_FILE = 'system_status.json'

# SEMILLA 2024 (29 Dic - Sorteo 5210)
HISTORY_START_DATE = datetime.datetime(2024, 12, 29)
HISTORY_START_SORTEO = 5210

def log(msg, status="INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{status}] {msg}")

def git_push_live(sorteo_num):
    try:
        subprocess.run(["git", "add", CSV_FILE], check=True)
        subprocess.run(["git", "commit", "-m", f"Live: Agregado Sorteo {sorteo_num}"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True)
        log(f"--> Sorteo {sorteo_num} subido a GitHub.", "GIT")
    except Exception as e:
        log(f"Git push error: {e}", "WARN")

def generate_url(sorteo_num, date_obj):
    # Formato estricto: /2024/12/29/resultados-loto-sorteo-5210-fecha-29-12-2024/
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
    
    # Validación: Si el HTML cargó, asumimos que es el correcto 
    # (aunque la URL tenga typos, si carga, sirve)
    data = {'sorteo': expected_sorteo}
    
    def get_nums(header):
        h = soup.find('h3', string=re.compile(header, re.IGNORECASE))
        div = h.find_next('div', class_='bolitas') if h else None
        return [int(p.text) for p in div.find_all('p')] if div else []

    data['LOTO'] = get_nums('Loto')
    if not data['LOTO']: 
        f = soup.find('div', class_='bolitas')
        if f: data['LOTO'] = [int(p.text) for p in f.find_all('p')]

    # Si no hay bolas, es un falso positivo
    if not data['LOTO']: return None 

    c_div = soup.find('div', class_='comodin')
    data['COMODIN'] = int(c_div.find('p').text) if c_div else 0

    data['RECARGADO'] = get_nums('Recargado')
    data['REVANCHA'] = get_nums('Revancha')
    data['DESQUITE'] = get_nums('Desquite')
    
    # Premios
    data['LOTO_GANADORES'] = 0
    data['LOTO_MONTO'] = 0

    table = soup.find('table', class_='table-prizes')
    if table:
        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) >= 3:
                cat = cols[0].get_text(" ", strip=True).lower()
                monto = int(re.sub(r'\D', '', cols[1].text) or 0)
                ganadores = int(re.sub(r'\D', '', cols[2].text) or 0)

                if 'loto 6 aciertos' in cat:
                    data['LOTO_GANADORES'] = ganadores
                    data['LOTO_MONTO'] = monto

    return data

def save_to_csv(data_dict, date_obj):
    try:
        try: df = pd.read_csv(CSV_FILE, sep=';')
        except: df = pd.DataFrame()
        
        if 'sorteo' in df.columns and data_dict['sorteo'] in df['sorteo'].values:
            return False

        row = {
            'sorteo': data_dict['sorteo'],
            'anio': date_obj.year, 'mes': date_obj.month, 'dia': date_obj.day,
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
        
        for g in ['RECARGADO','REVANCHA','DESQUITE']:
            nums = data_dict.get(g, [])
            for i in range(6): row[f'{g}_n{i+1}'] = nums[i] if i<len(nums) else 0

        new_df = pd.DataFrame([row])
        df_final = pd.concat([df, new_df], ignore_index=True)
        
        # ORDEN ASCENDENTE (1, 2, 3...) como pediste
        df_final['sorteo'] = df_final['sorteo'].astype(int)
        df_final.sort_values(by='sorteo', ascending=True, inplace=True)
        
        df_final.to_csv(CSV_FILE, sep=';', index=False)
        return True
    except Exception as e:
        log(f"Error CSV: {e}", "ERROR")
        return False

def run_historical_mode():
    log(f"--- MODO FRANCOTIRADOR (V12) ---")
    log(f"Objetivo: Sorteo {HISTORY_START_SORTEO} en {HISTORY_START_DATE.date()}")
    
    existing = set()
    try:
        df = pd.read_csv(CSV_FILE, sep=';')
        if not df.empty: existing = set(df['sorteo'].unique())
    except: pass

    current_date = HISTORY_START_DATE
    current_sorteo = HISTORY_START_SORTEO
    end_date = datetime.datetime.now()

    while current_date <= end_date:
        # Solo Martes (1), Jueves (3), Domingo (6)
        if current_date.weekday() in [1, 3, 6]: 
            
            if current_sorteo in existing:
                log(f"[YA EXISTE] Sorteo {current_sorteo} ({current_date.date()})")
                # Avanzamos sorteo porque ya lo tenemos
                current_sorteo += 1
            else:
                url = generate_url(current_sorteo, current_date)
                html = get_html(url)
                
                if html:
                    data = parse_html(html, current_sorteo)
                    if data and data['LOTO']:
                        if save_to_csv(data, current_date):
                            log(f"*** [EXITO] Sorteo {current_sorteo} recuperado ***", "SUCCESS")
                            git_push_live(current_sorteo)
                            # Éxito: Pasamos al siguiente sorteo
                            current_sorteo += 1
                    else:
                        log(f"[ERROR CONTENIDO] URL cargó pero sin datos válidos.")
                        # PLAN B: SALTARSE AL SIGUIENTE
                        log(f"--> Saltando Sorteo {current_sorteo}...")
                        current_sorteo += 1
                else:
                    log(f"[404] URL No encontrada para {current_sorteo}")
                    # PLAN B: SALTARSE AL SIGUIENTE
                    # Si la URL está rota (caso 5210), asumimos perdido y avanzamos
                    # para no perder la sincronía del calendario con el 5211.
                    log(f"--> Saltando Sorteo {current_sorteo}...")
                    current_sorteo += 1
                
                time.sleep(0.5)
        
        # Avanzar calendario
        current_date += datetime.timedelta(days=1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'history':
        run_historical_mode()
    else:
        run_historical_mode()
