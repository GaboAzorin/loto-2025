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
HISTORY_START_DATE = datetime.datetime(2025, 1, 9)
HISTORY_START_SORTEO = 5215

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

def get_html(url):
    try:
        # Timeout generoso
        response = cureq.get(url, impersonate="chrome110", timeout=20)
        return response.text if response.status_code == 200 else None
    except: return None

# --- PLAN A: CONSTRUCCIÓN DIRECTA (FRANCOTIRADOR) ---
def generate_direct_url(sorteo_num, date_obj):
    # Estructura estándar: /AAAA/MM/DD/resultados-loto-sorteo-NNNN-fecha-DD-MM-AAAA/
    yyyy = date_obj.strftime("%Y")
    mm = date_obj.strftime("%m")
    dd = date_obj.strftime("%d")
    slug_date = f"{dd}-{mm}-{yyyy}"
    return f"https://resultadoslotochile.com/{yyyy}/{mm}/{dd}/resultados-loto-sorteo-{sorteo_num}-fecha-{slug_date}/"

# --- PLAN B: BUSCADOR INTERNO (RESPALDO) ---
def find_link_by_internal_search(sorteo_num):
    search_url = f"https://resultadoslotochile.com/?s={sorteo_num}"
    log(f"Plan A falló (404). Activando Plan B (Búsqueda): {search_url}", "SEARCH")
    
    html = get_html(search_url)
    if not html: return None
    
    soup = BeautifulSoup(html, 'lxml')
    
    # Buscar artículos
    articles = soup.find_all('article')
    if not articles:
        links = soup.find_all('a', href=True)
    else:
        links = [art.find('a', href=True) for art in articles if art.find('a', href=True)]

    for a in links:
        if not a: continue
        text = a.get_text(" ", strip=True).lower()
        href = a['href']
        
        # Verificamos que sea el sorteo correcto
        if str(sorteo_num) in text and "resultados loto" in text:
            log(f"¡Encontrado vía búsqueda! -> {href}", "SUCCESS")
            return href
            
    return None

def parse_html(html, expected_sorteo):
    soup = BeautifulSoup(html, 'lxml')
    
    data = {'sorteo': expected_sorteo}
    
    def get_nums(header):
        h = soup.find('h3', string=re.compile(header, re.IGNORECASE))
        div = h.find_next('div', class_='bolitas') if h else None
        return [int(p.text) for p in div.find_all('p')] if div else []

    data['LOTO'] = get_nums('Loto')
    # Fallback
    if not data['LOTO']: 
        f = soup.find('div', class_='bolitas')
        if f: data['LOTO'] = [int(p.text) for p in f.find_all('p')]

    if not data['LOTO']: return None # Abortar si no hay números

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
        
        # ORDEN ASCENDENTE (Antiguo -> Nuevo)
        df_final['sorteo'] = df_final['sorteo'].astype(int)
        df_final.sort_values(by='sorteo', ascending=True, inplace=True)
        
        df_final.to_csv(CSV_FILE, sep=';', index=False)
        return True
    except Exception as e:
        log(f"Error CSV: {e}", "ERROR")
        return False

def run_historical_mode():
    log(f"--- MODO HISTÓRICO V11 (DIRECTO + BÚSQUEDA) ---")
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
        if current_date.weekday() in [1, 3, 6]: # Mar, Jue, Dom
            
            if current_sorteo in existing:
                log(f"[SALTAR] {current_date.date()} (Ya existe)")
                current_sorteo += 1
            else:
                # ====================================================
                # ESTRATEGIA DOBLE
                # ====================================================
                
                target_url = None
                
                # 1. PLAN A: URL DIRECTA
                direct_url = generate_direct_url(current_sorteo, current_date)
                html = get_html(direct_url)
                
                if html:
                    # Validamos si la URL directa cargó el sorteo correcto
                    data = parse_html(html, current_sorteo)
                    if data:
                        # ¡Éxito a la primera!
                        log(f"Plan A Exitoso: {direct_url}")
                    else:
                        html = None # Invalido, forzar Plan B
                
                # 2. PLAN B: SI PLAN A FALLÓ, USAR BÚSQUEDA
                if not html:
                    search_link = find_link_by_internal_search(current_sorteo)
                    if search_link:
                        html = get_html(search_link)
                        if html:
                            data = parse_html(html, current_sorteo)
                        else:
                            data = None
                    else:
                        data = None

                # 3. PROCESAMIENTO FINAL
                if data:
                    if save_to_csv(data, current_date):
                        log(f"*** [CAPTURADO] Sorteo {current_sorteo} ***", "SUCCESS")
                        git_push_live(current_sorteo)
                        current_sorteo += 1
                    else:
                        log("Error guardando CSV")
                else:
                    log(f"[404 FINAL] No se encontró Sorteo {current_sorteo} hoy.")
                    # No avanzamos sorteo
                
                time.sleep(1) # Pausa
        
        current_date += datetime.timedelta(days=1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'history':
        run_historical_mode()
    else:
        run_historical_mode()
