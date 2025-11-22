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

# SEMILLA: 29 Diciembre 2024 - Sorteo 5210 (El problemático)
HISTORY_START_DATE = datetime.datetime(2024, 12, 29)
HISTORY_START_SORTEO = 5210

def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def update_status_json(sorteo, fecha, estado, detalle):
    """Escribe el estado actual en el JSON"""
    data = {
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "current_target": {
            "sorteo": sorteo,
            "fecha": fecha.strftime("%d-%m-%Y")
        },
        "status": estado, # "BUSCANDO", "ENCONTRADO", "MISSING"
        "message": detalle
    }
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def git_push_changes(files_to_add, commit_msg):
    """Sube cambios específicos a GitHub"""
    try:
        for f in files_to_add:
            subprocess.run(["git", "add", f], check=False)
        
        subprocess.run(["git", "commit", "-m", commit_msg], check=False, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=False)
        log(f"--> Git Push: {commit_msg}")
    except Exception as e:
        log(f"Error Git: {e}")

def generate_url(sorteo_num, date_obj):
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
    if str(expected_sorteo) not in soup.text: return None

    data = {'sorteo': expected_sorteo}
    
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
        
        # ORDEN ASCENDENTE
        df_final['sorteo'] = df_final['sorteo'].astype(int)
        df_final.sort_values(by='sorteo', ascending=True, inplace=True)
        
        df_final.to_csv(CSV_FILE, sep=';', index=False)
        return True
    except Exception as e:
        log(f"Error CSV: {e}")
        return False

def run_historical_mode():
    log(f"--- INICIO MODO HISTÓRICO V13 (REPORTING) ---")
    
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
            
            # 1. REPORTE INICIAL: "Estoy buscando X"
            update_status_json(current_sorteo, current_date, "BUSCANDO", "Consultando URL...")
            # Solo pusheamos el JSON para avisar que estamos vivos (cada 3 intentos para no saturar, o siempre)
            # Aquí lo haremos siempre para que veas el avance
            git_push_changes([STATUS_FILE], f"Status: Buscando {current_sorteo}")

            if current_sorteo in existing:
                log(f"[YA EXISTE] Sorteo {current_sorteo}")
                update_status_json(current_sorteo, current_date, "OMITIDO", "Ya existe en BD")
                current_sorteo += 1
            else:
                url = generate_url(current_sorteo, current_date)
                html = get_html(url)
                
                if html:
                    data = parse_html(html, current_sorteo)
                    if data and data['LOTO']:
                        if save_to_csv(data, current_date):
                            msg = f"*** ¡EXITO! Sorteo {current_sorteo} Guardado ***"
                            log(msg)
                            update_status_json(current_sorteo, current_date, "ENCONTRADO", "Datos guardados correctamente")
                            # SUBIDA CRÍTICA: CSV Y JSON
                            git_push_changes([CSV_FILE, STATUS_FILE], f"DB: Sorteo {current_sorteo} agregado")
                            
                            current_sorteo += 1
                    else:
                        log(f"[ERROR DATOS] HTML ok pero vacío")
                        # Avanzamos igual para no bloquear
                        update_status_json(current_sorteo, current_date, "ERROR", "HTML sin datos válidos. Saltando.")
                        git_push_changes([STATUS_FILE], f"Status: Error en {current_sorteo}")
                        current_sorteo += 1
                else:
                    log(f"[404] URL no encontrada para {current_sorteo}")
                    update_status_json(current_sorteo, current_date, "MISSING", "URL 404 - Saltando al siguiente")
                    # SUBIDA DE AVISO DE SALTO
                    git_push_changes([STATUS_FILE], f"Status: 404 en {current_sorteo}")
                    
                    # AQUÍ ESTÁ LA CLAVE: AVANZAMOS AUNQUE FALLE
                    current_sorteo += 1
                
                time.sleep(1)
        
        current_date += datetime.timedelta(days=1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'history':
        run_historical_mode()
    else:
        run_historical_mode()
