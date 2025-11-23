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

# Configuración para modo Histórico (Solo si se pide manualmente)
HISTORY_START_DATE = datetime.datetime(2024, 12, 29)
HISTORY_START_SORTEO = 5210

def log(msg, status="INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{status}] {msg}")

def git_push_live(sorteo_num, mode="Auto"):
    try:
        subprocess.run(["git", "add", CSV_FILE], check=True)
        subprocess.run(["git", "commit", "-m", f"{mode}: Sorteo {sorteo_num} agregado"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True)
        log(f"--> Sorteo {sorteo_num} subido a GitHub.", "GIT")
    except Exception as e:
        log(f"Git push omitido: {e}", "WARN")

def get_html(url):
    try:
        response = cureq.get(url, impersonate="chrome110", timeout=20)
        return response.text if response.status_code == 200 else None
    except: return None

# --- ESTRATEGIA 1: URL DIRECTA (FRANCOTIRADOR) ---
def generate_url(sorteo_num, date_obj):
    yyyy = date_obj.strftime("%Y")
    mm = date_obj.strftime("%m")
    dd = date_obj.strftime("%d")
    slug_date = f"{dd}-{mm}-{yyyy}"
    return f"https://resultadoslotochile.com/{yyyy}/{mm}/{dd}/resultados-loto-sorteo-{sorteo_num}-fecha-{slug_date}/"

# --- ESTRATEGIA 2: BÚSQUEDA (SABUESO) ---
# Vital para el domingo si la URL viene con errores de tipeo
def find_link_by_search(sorteo_num):
    search_url = f"https://resultadoslotochile.com/?s={sorteo_num}"
    log(f"Plan A falló. Buscando en el sitio: {search_url}", "SEARCH")
    
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
        if str(sorteo_num) in text and "resultados" in text:
            log(f"¡Enlace encontrado!: {a['href']}", "FOUND")
            return a['href']
    return None

def parse_html(html, expected_sorteo):
    soup = BeautifulSoup(html, 'lxml')
    
    # Validación suave: confiamos en la búsqueda, pero chequeamos si el texto está
    data = {'sorteo': expected_sorteo}
    
    # Intentar sacar fecha real del meta
    meta_date = soup.find('meta', property='article:published_time')
    if meta_date:
        try:
            dt = datetime.datetime.fromisoformat(meta_date['content'])
            data.update({'anio': dt.year, 'mes': dt.month, 'dia': dt.day, 'dia_semana': dt.strftime('%A')})
        except: pass

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
        
        if 'sorteo' in df.columns:
            df = df[df['sorteo'] != data_dict['sorteo']]

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
        df_final['sorteo'] = df_final['sorteo'].astype(int)
        df_final.sort_values(by='sorteo', ascending=True, inplace=True)
        
        df_final.to_csv(CSV_FILE, sep=';', index=False)
        return True
    except Exception as e:
        log(f"Error CSV: {e}", "ERROR")
        return False

# --- MODOS DE EJECUCIÓN ---

def run_daily_check():
    log("--- INICIANDO CHEQUEO DIARIO (V18) ---")
    
    # 1. Leer último sorteo
    try:
        df = pd.read_csv(CSV_FILE, sep=';')
        last_sorteo = int(df['sorteo'].max())
        target_sorteo = last_sorteo + 1
    except:
        log("No hay base de datos. Ejecuta modo histórico primero.", "ERROR")
        return

    log(f"Último registrado: {last_sorteo}. Buscando objetivo: {target_sorteo}")

    # 2. Intentar URL Directa (Para hoy)
    # Asumimos que si el cron corre hoy, la fecha es hoy
    today = datetime.datetime.now()
    direct_url = generate_url(target_sorteo, today)
    
    html = get_html(direct_url)
    
    # 3. Si falla, usar Búsqueda (Plan B)
    if not html:
        search_link = find_link_by_search(target_sorteo)
        if search_link:
            html = get_html(search_link)
    
    # 4. Procesar
    if html:
        data = parse_html(html, target_sorteo)
        if data and data['LOTO']:
            if save_to_csv(data):
                log(f"*** ¡EXITO! Sorteo {target_sorteo} capturado ***", "SUCCESS")
                git_push_live(target_sorteo, "Daily")
            else:
                log("Error al guardar datos.")
        else:
            log("HTML descargado pero sin datos legibles (¿Estructura cambió?)")
    else:
        log(f"El sorteo {target_sorteo} aún no está disponible o falló la conexión.")

def run_historical_mode():
    log("--- MODO HISTÓRICO / REPARACIÓN ---")
    
    existing = set()
    try:
        df = pd.read_csv(CSV_FILE, sep=';')
        existing = set(df['sorteo'].unique())
    except: pass

    current_date = HISTORY_START_DATE
    current_sorteo = HISTORY_START_SORTEO
    end_date = datetime.datetime.now()

    while current_date <= end_date:
        if current_date.weekday() in [1, 3, 6]: 
            if current_sorteo in existing:
                log(f"[SALTAR] {current_sorteo}")
                current_sorteo += 1
            else:
                # Intento Híbrido
                url = generate_url(current_sorteo, current_date)
                html = get_html(url)
                
                if not html:
                    s_link = find_link_by_search(current_sorteo)
                    if s_link: html = get_html(s_link)
                
                if html:
                    data = parse_html(html, current_sorteo)
                    if data and data['LOTO']:
                        save_to_csv(data)
                        log(f"[RECUPERADO] Sorteo {current_sorteo}", "SUCCESS")
                        git_push_live(current_sorteo, "Repair")
                        current_sorteo += 1
                
                time.sleep(1)
        
        current_date += datetime.timedelta(days=1)

if __name__ == "__main__":
    # LÓGICA DEL CEREBRO
    # Si le pasas "history", hace el barrido.
    # Si NO le pasas nada (lo que hace GitHub automáticamente), hace el "Daily Check".
    if len(sys.argv) > 1 and sys.argv[1] == 'history':
        run_historical_mode()
    else:
        run_daily_check()
