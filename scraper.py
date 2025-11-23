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

# SEMILLA: 29 Diciembre 2024 - Sorteo 5210
HISTORY_START_DATE = datetime.datetime(2024, 12, 29)
HISTORY_START_SORTEO = 5210

def log(msg, status="INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{status}] {msg}")

def git_push_live(sorteo_num, mode="Auto"):
    try:
        subprocess.run(["git", "add", CSV_FILE], check=True)
        subprocess.run(["git", "commit", "-m", f"{mode}: Sorteo {sorteo_num} actualizado"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True)
        log(f"--> Sorteo {sorteo_num} subido.", "GIT")
    except Exception as e:
        log(f"Git push omitido: {e}", "WARN")

def get_html(url):
    try:
        response = cureq.get(url, impersonate="chrome110", timeout=20)
        return response.text if response.status_code == 200 else None
    except: return None

def generate_url(sorteo_num, date_obj):
    yyyy = date_obj.strftime("%Y")
    mm = date_obj.strftime("%m")
    dd = date_obj.strftime("%d")
    slug_date = f"{dd}-{mm}-{yyyy}"
    return f"https://resultadoslotochile.com/{yyyy}/{mm}/{dd}/resultados-loto-sorteo-{sorteo_num}-fecha-{slug_date}/"

def find_link_by_search(sorteo_num):
    search_url = f"https://resultadoslotochile.com/?s={sorteo_num}"
    html = get_html(search_url)
    if not html: return None
    soup = BeautifulSoup(html, 'lxml')
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
            return a['href']
    return None

def parse_html(html, expected_sorteo):
    soup = BeautifulSoup(html, 'lxml')
    if str(expected_sorteo) not in soup.text: return None

    data = {'sorteo': expected_sorteo}
    
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
    
    # --- NUEVA LÓGICA DE EXTRACCIÓN FINANCIERA (TABLA) ---
    # Inicializamos TODAS las columnas financieras en 0
    financial_cols = [
        'LOTO', 'SUPER_QUINA_5_ACIERTOS_COMODIN', 'QUINA_5_ACIERTOS', 
        'SUPER_CUATERNA_4_ACIERTOS_COMODIN', 'CUATERNA_4_ACIERTOS', 
        'SUPER_TERNA_3_ACIERTOS_COMODIN', 'TERNA_3_ACIERTOS', 
        'SUPER_DUPLA_2_ACIERTOS_COMODIN', 'RECARGADO_6_ACIERTOS', 
        'REVANCHA', 'DESQUITE'
    ]
    for col in financial_cols:
        data[f'{col}_GANADORES'] = 0
        data[f'{col}_MONTO'] = 0

    table = soup.find('table', class_='table-prizes')
    if table:
        for row in table.find_all('tr'):
            cols = row.find_all('td')
            if len(cols) >= 3:
                # Normalizamos el texto de la categoría para comparar
                cat = cols[0].get_text(" ", strip=True).lower()
                
                # Extraemos números limpiando todo lo que no sea dígito
                monto_raw = cols[1].get_text(strip=True)
                gan_raw = cols[2].get_text(strip=True)
                
                monto = int(re.sub(r'\D', '', monto_raw) or 0)
                ganadores = int(re.sub(r'\D', '', gan_raw) or 0)

                # LOGICA DE MATCHING MÁS ROBUSTA
                target_col = None
                
                if 'loto' in cat and '6 aciertos' in cat: target_col = 'LOTO'
                elif 'súper quina' in cat or ('quina' in cat and 'comodín' in cat): target_col = 'SUPER_QUINA_5_ACIERTOS_COMODIN'
                elif 'quina' in cat: target_col = 'QUINA_5_ACIERTOS'
                elif 'súper cuaterna' in cat or ('cuaterna' in cat and 'comodín' in cat): target_col = 'SUPER_CUATERNA_4_ACIERTOS_COMODIN'
                elif 'cuaterna' in cat: target_col = 'CUATERNA_4_ACIERTOS'
                elif 'súper terna' in cat or ('terna' in cat and 'comodín' in cat): target_col = 'SUPER_TERNA_3_ACIERTOS_COMODIN'
                elif 'terna' in cat: target_col = 'TERNA_3_ACIERTOS'
                elif 'súper dupla' in cat: target_col = 'SUPER_DUPLA_2_ACIERTOS_COMODIN'
                elif 'recargado' in cat: target_col = 'RECARGADO_6_ACIERTOS'
                elif 'revancha' in cat: target_col = 'REVANCHA'
                elif 'desquite' in cat: target_col = 'DESQUITE'

                if target_col:
                    data[f'{target_col}_GANADORES'] = ganadores
                    data[f'{target_col}_MONTO'] = monto

    return data

def save_to_csv(data_dict):
    try:
        try: df = pd.read_csv(CSV_FILE, sep=';')
        except: df = pd.DataFrame()
        
        # Si el sorteo ya existe, lo REEMPLAZAMOS (para arreglar datos malos)
        if 'sorteo' in df.columns:
            df = df[df['sorteo'] != data_dict['sorteo']]

        # Fallback fecha
        if 'anio' not in data_dict:
            now = datetime.datetime.now()
            data_dict.update({'anio': now.year, 'mes': now.month, 'dia': now.day, 'dia_semana': now.strftime('%A')})

        # Construimos la fila con TODAS las columnas
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
        }
        
        # Agregamos dinámicamente todos los campos financieros que capturamos
        for k, v in data_dict.items():
            if k.endswith('_GANADORES') or k.endswith('_MONTO'):
                row[k] = v
        
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

def run_repair_mode():
    log("--- MODO REPARACIÓN DE PREMIOS ---")
    
    # Identificar sorteos incompletos (aquellos con LOTO_MONTO NaN o 0, pero que sabemos que existen)
    # O simplemente iterar sobre los que me dijiste (5210... etc)
    # Para estar seguros, vamos a forzar la revisión de los sorteos problemáticos que detectaste
    
    targets = [5210, 5211, 5212, 5213, 5214, 5215, 5216, 5217, 5218, 5219, 5220, 5221, 5222, 5223, 5224] 
    # Agrega aquí más si quieres, o usa un rango
    
    # O MEJOR: Iterar desde el 5210 hasta el 5350 revisando uno por uno
    current = 5210
    end = 5350
    
    # Fecha inicial estimada para el 5210
    curr_date = datetime.datetime(2024, 12, 29) 

    while current <= end:
        log(f"Revisando Sorteo {current}...")
        
        # 1. Intentar URL directa
        url = generate_url(current, curr_date)
        html = get_html(url)
        
        # 2. Si falla, búsqueda
        if not html:
            s_link = find_link_by_search(current)
            if s_link: html = get_html(s_link)
        
        if html:
            data = parse_html(html, current)
            if data and data['LOTO']:
                # VERIFICACIÓN: ¿Tiene datos financieros?
                # Si LOTO_MONTO es 0 y LOTO_GANADORES es 0, podría ser vacante (correcto)
                # Pero chequeamos si capturó ALGO de la tabla (ej: Quina)
                has_money_data = any(data[k] > 0 for k in data if k.endswith('_MONTO'))
                
                if has_money_data:
                    if save_to_csv(data):
                        log(f"[CORREGIDO] Sorteo {current} con datos financieros.", "SUCCESS")
                        git_push_live(current, "Repair")
                else:
                    log(f"[WARNING] Sorteo {current} capturado pero tabla de premios vacía/incompleta.")
            else:
                log(f"[ERROR] HTML sin datos válidos para {current}")
        else:
            log(f"[MISSING] No se encontró URL para {current}")

        # Avanzar lógica de fecha (aprox) para la siguiente URL directa
        # No es crítico que sea exacta porque tenemos el fallback de búsqueda
        curr_date += datetime.timedelta(days=2) 
        current += 1
        time.sleep(1)

if __name__ == "__main__":
    # Ejecuta la reparación masiva una vez para arreglar tu CSV
    run_repair_mode()
    
    # Cuando termines de arreglar, cambia esta línea por:
    # run_daily_check()
