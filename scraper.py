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

def log(msg, status="INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{status}] {msg}")

def git_push_live(sorteo_num):
    """Sube cambios a GitHub inmediatamente"""
    try:
        subprocess.run(["git", "add", CSV_FILE], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto: Sorteo {sorteo_num} capturado"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True)
        log(f"--> Sorteo {sorteo_num} subido a la nube.", "GIT")
    except Exception as e:
        log(f"Git push omitido (Local o Error): {e}", "WARN")

def get_html(url):
    try:
        response = cureq.get(url, impersonate="chrome110", timeout=20)
        return response.text if response.status_code == 200 else None
    except: return None

# --- ESTRATEGIA 1: FRANCOTIRADOR (URL POR FECHA) ---
def generate_url(sorteo_num, date_obj):
    yyyy = date_obj.strftime("%Y")
    mm = date_obj.strftime("%m")
    dd = date_obj.strftime("%d")
    slug_date = f"{dd}-{mm}-{yyyy}"
    return f"https://resultadoslotochile.com/{yyyy}/{mm}/{dd}/resultados-loto-sorteo-{sorteo_num}-fecha-{slug_date}/"

# --- ESTRATEGIA 2: SABUESO (BUSCADOR INTERNO) ---
def find_link_by_search(sorteo_num):
    search_url = f"https://resultadoslotochile.com/?s={sorteo_num}"
    log(f"Activando búsqueda de emergencia para {sorteo_num}...", "SEARCH")
    
    html = get_html(search_url)
    if not html: return None
    
    soup = BeautifulSoup(html, 'lxml')
    
    # Buscar en artículos o links generales
    candidates = soup.find_all('article')
    links = []
    if candidates:
        links = [art.find('a', href=True) for art in candidates if art.find('a', href=True)]
    else:
        links = soup.find_all('a', href=True)

    for a in links:
        if not a: continue
        text = a.get_text(" ", strip=True).lower()
        # Validación laxa para encontrar URLs mal escritas
        if str(sorteo_num) in text and "resultados" in text:
            return a['href']
    return None

def parse_html(html, expected_sorteo):
    soup = BeautifulSoup(html, 'lxml')
    
    # Validación: El HTML debe mencionar el sorteo en algún lado
    if str(expected_sorteo) not in soup.text: return None

    data = {'sorteo': expected_sorteo}
    
    # Intentar rescatar la fecha real del artículo
    meta_date = soup.find('meta', property='article:published_time')
    if meta_date:
        try:
            dt = datetime.datetime.fromisoformat(meta_date['content'])
            data['anio'] = dt.year; data['mes'] = dt.month; data['dia'] = dt.day; data['dia_semana'] = dt.strftime('%A')
        except: pass # Si falla, se usarán los datos de la llamada
        
    def get_nums(header):
        h = soup.find('h3', string=re.compile(header, re.IGNORECASE))
        div = h.find_next('div', class_='bolitas') if h else None
        return [int(p.text) for p in div.find_all('p')] if div else []

    data['LOTO'] = get_nums('Loto')
    if not data['LOTO']: 
        f = soup.find('div', class_='bolitas')
        if f: data['LOTO'] = [int(p.text) for p in f.find_all('p')]

    if not data['LOTO']: return None

    c_div = soup.find('div', class_='comodin')
    data['COMODIN'] = int(c_div.find('p').text) if c_div else 0

    data['RECARGADO'] = get_nums('Recargado')
    data['REVANCHA'] = get_nums('Revancha')
    data['DESQUITE'] = get_nums('Desquite')
    
    # Premios
    data['LOTO_GANADORES'] = 0; data['LOTO_MONTO'] = 0
    table = soup.find('table', class_='table-prizes')
    if table:
        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) >= 3:
                cat = cols[0].get_text(" ", strip=True).lower()
                if 'loto 6 aciertos' in cat:
                    data['LOTO_MONTO'] = int(re.sub(r'\D', '', cols[1].text) or 0)
                    data['LOTO_GANADORES'] = int(re.sub(r'\D', '', cols[2].text) or 0)
    return data

def save_to_csv(data_dict):
    try:
        try: df = pd.read_csv(CSV_FILE, sep=';')
        except: df = pd.DataFrame()
        
        # Limpieza anti-duplicados
        if 'sorteo' in df.columns:
            df = df[df['sorteo'] != data_dict['sorteo']]

        # Si no capturamos fecha del HTML, usamos hoy (fallback)
        if 'anio' not in data_dict:
            now = datetime.datetime.now()
            data_dict.update({'anio': now.year, 'mes': now.month, 'dia': now.day, 'dia_semana': now.strftime('%A')})

        row = {
            'sorteo': data_dict['sorteo'],
            'anio': data_dict['anio'], 'mes': data_dict['mes'], 'dia': data_dict['dia'],
            'dia_semana': data_dict['dia_semana'],
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
        
        # Ordenar Descendente (Lo más nuevo arriba) para la vista, o Ascendente si prefieres
        # Usaré Ascendente para mantener consistencia con tu petición anterior
        df_final['sorteo'] = df_final['sorteo'].astype(int)
        df_final.sort_values(by='sorteo', ascending=True, inplace=True)
        
        df_final.to_csv(CSV_FILE, sep=';', index=False)
        return True
    except Exception as e:
        log(f"Error CSV: {e}", "ERROR")
        return False

def run_daily_check():
    log("--- INICIANDO CHEQUEO DIARIO ---")
    
    # 1. Identificar cuál es el próximo sorteo necesario
    try:
        df = pd.read_csv(CSV_FILE, sep=';')
        last_sorteo = int(df['sorteo'].max())
        target_sorteo = last_sorteo + 1
    except:
        log("No hay BD. Por favor corre el modo histórico primero.")
        return

    log(f"El último sorteo fue {last_sorteo}. Buscando el {target_sorteo}...")

    # 2. Intentar Estrategia A: URL de Hoy
    today = datetime.datetime.now()
    url = generate_url(target_sorteo, today)
    
    log(f"Probando URL directa: {url}")
    html = get_html(url)
    
    success = False
    
    if html:
        data = parse_html(html, target_sorteo)
        if data and data['LOTO']:
            if save_to_csv(data):
                log(f"¡EXITO! Sorteo {target_sorteo} capturado vía Directa.", "SUCCESS")
                success = True
    
    # 3. Si falla A, intentar Estrategia B: Buscar en todo el sitio
    if not success:
        log("Fallo directo. Activando Sabueso...", "WARN")
        search_url = find_link_by_search(target_sorteo)
        
        if search_url:
            log(f"Link encontrado por búsqueda: {search_url}")
            html = get_html(search_url)
            if html:
                data = parse_html(html, target_sorteo)
                if data and data['LOTO']:
                    if save_to_csv(data):
                        log(f"¡EXITO! Sorteo {target_sorteo} capturado vía Búsqueda.", "SUCCESS")
                        success = True
    
    if success:
        git_push_live(target_sorteo)
    else:
        log(f"El sorteo {target_sorteo} aún no está disponible o falló la búsqueda.", "INFO")

if __name__ == "__main__":
    # Por defecto (cron job) corre el chequeo diario
    run_daily_check()
