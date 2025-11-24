import sys
import datetime
import re
import time
import subprocess
import pandas as pd
from curl_cffi import requests as cureq
from bs4 import BeautifulSoup
import pytz 

# --- CONFIGURACIÓN ---
CSV_FILE = 'LOTO_HISTORIAL_MAESTRO.csv'
TZ_CHILE = pytz.timezone('America/Santiago')

def log(msg, status="INFO"):
    now_chile = datetime.datetime.now(TZ_CHILE)
    ts = now_chile.strftime("%H:%M:%S")
    print(f"[{ts}] [{status}] {msg}")

def git_push_live(sorteo_num):
    try:
        subprocess.run(["git", "config", "--global", "user.name", "LotoBot"], check=False)
        subprocess.run(["git", "config", "--global", "user.email", "bot@noreply.github.com"], check=False)
        
        subprocess.run(["git", "add", CSV_FILE], check=True)
        msg = f"DATA: Sorteo {sorteo_num} agregado automágicamente"
        subprocess.run(["git", "commit", "-m", msg], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True)
        log(f"--> Sorteo {sorteo_num} subido a GitHub.", "GIT")
    except Exception as e:
        log(f"Git push omitido: {e}", "WARN")

def get_html(url):
    try:
        response = cureq.get(url, impersonate="chrome110", timeout=30)
        return response.text if response.status_code == 200 else None
    except Exception as e: 
        log(f"Error HTTP: {e}", "ERR")
        return None

def get_target_url_via_search(sorteo_num):
    """
    Busca en ?s=[NUM] para encontrar la URL canónica del sorteo.
    """
    search_url = f"https://resultadoslotochile.com/?s={sorteo_num}"
    log(f"Buscando enlace para sorteo {sorteo_num}...", "SEARCH")
    
    html = get_html(search_url)
    if not html: return None

    soup = BeautifulSoup(html, 'lxml')
    candidates = []
    
    # Busca dentro de articles (estructura típica de WordPress en el sitio)
    for art in soup.find_all('article'):
        link = art.find('a', href=True)
        if link: candidates.append(link)
            
    # Fallback general
    if not candidates:
        candidates = soup.find_all('a', href=True)

    for a in candidates:
        text = a.get_text(" ", strip=True).lower()
        href = a['href']
        # Validación estricta del texto del enlace
        if str(sorteo_num) in text and ("sorteo" in text or "resultados" in text):
            if "facebook" in href or "twitter" in href: continue
            log(f"Enlace encontrado: {href}", "SUCCESS")
            return href

    return None

def parse_financial_data(soup, data_dict):
    """
    Extrae premios basándose en el código fuente del sorteo 5351.
    """
    # 1. Definir columnas base en 0
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

    # Inicializar
    for key in financial_targets:
        data_dict[f'{key}_GANADORES'] = 0
        data_dict[f'{key}_MONTO'] = 0

    table = soup.find('table', class_='table-prizes')
    if not table: return data_dict

    # 2. Iterar filas de la tabla
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) >= 3:
            # Según tu JSON: td[0]=Categoría, td[1]=Monto, td[2]=Ganadores
            cat_text = cols[0].get_text(" ", strip=True).lower()
            monto_raw = cols[1].get_text(strip=True)
            gan_raw = cols[2].get_text(strip=True)
            
            # Limpieza de números (eliminar puntos y signo $)
            monto = int(re.sub(r'\D', '', monto_raw) or 0)
            ganadores = int(re.sub(r'\D', '', gan_raw) or 0)

            # 3. Matching exacto
            for db_key, search_terms in financial_targets.items():
                # Si alguno de los términos de búsqueda está en la categoría...
                if any(term in cat_text for term in search_terms):
                    # Evitar conflictos (ej: "Súper Quina" contiene "Quina")
                    # La lógica aquí es: Si ya encontré "Súper Quina", no busco "Quina" para esta fila.
                    
                    # Refinamiento para 'Quina' vs 'Súper Quina':
                    if db_key == 'QUINA_5_ACIERTOS' and 'súper' in cat_text:
                        continue # Es super quina, no quina normal
                    if db_key == 'CUATERNA_4_ACIERTOS' and 'súper' in cat_text:
                        continue
                    if db_key == 'TERNA_3_ACIERTOS' and 'súper' in cat_text:
                        continue

                    data_dict[f'{db_key}_GANADORES'] = ganadores
                    data_dict[f'{db_key}_MONTO'] = monto
                    break # Pasamos a la siguiente fila de la tabla

    return data_dict

def extract_sorteo_data(url, expected_sorteo):
    html = get_html(url)
    if not html: return None
    soup = BeautifulSoup(html, 'lxml')

    data = {'sorteo': expected_sorteo}
    
    # 1. Fecha (Meta Tag)
    meta_date = soup.find('meta', property='article:published_time')
    if meta_date:
        try:
            dt = datetime.datetime.fromisoformat(meta_date['content'])
            data.update({'anio': dt.year, 'mes': dt.month, 'dia': dt.day, 'dia_semana': dt.strftime('%A')})
        except: pass
    
    if 'anio' not in data:
        now = datetime.datetime.now(TZ_CHILE)
        data.update({'anio': now.year, 'mes': now.month, 'dia': now.day, 'dia_semana': now.strftime('%A')})

    # 2. Extracción de Bolitas
    def get_nums(header_regex):
        # Busca h3 (o h2) que contenga el texto (ej: "Loto", "Revancha")
        # En tu JSON son <h3>Loto</h3>
        h = soup.find(['h3', 'h2'], string=re.compile(header_regex, re.IGNORECASE))
        if not h: return []
        
        # El div con las bolitas es el hermano siguiente
        div = h.find_next('div', class_='bolitas')
        if not div: return []
        
        return [int(p.text) for p in div.find_all('p') if p.text.strip().isdigit()]

    data['LOTO'] = get_nums('Loto')
    # Fallback por si el header es imagen o distinto
    if not data['LOTO']:
        first_div = soup.find('div', class_='bolitas')
        if first_div: data['LOTO'] = [int(p.text) for p in first_div.find_all('p')]

    if not data['LOTO']:
        log("ERROR CRÍTICO: No se encontraron bolitas Loto.", "ERR")
        return None

    # Comodín (Clase específica 'comodin')
    c_div = soup.find('div', class_='comodin')
    data['COMODIN'] = int(c_div.find('p').text) if c_div and c_div.find('p') else 0

    data['RECARGADO'] = get_nums('Recargado')
    data['REVANCHA'] = get_nums('Revancha')
    data['DESQUITE'] = get_nums('Desquite')
    
    # 3. Extracción Financiera
    data = parse_financial_data(soup, data)
    
    return data

def save_to_csv(data_dict):
    try:
        try: df = pd.read_csv(CSV_FILE, sep=';')
        except: df = pd.DataFrame()

        if 'sorteo' in df.columns:
            df = df[df['sorteo'] != data_dict['sorteo']]

        row = {
            'sorteo': data_dict['sorteo'],
            'anio': data_dict['anio'], 'mes': data_dict['mes'], 'dia': data_dict['dia'],
            'dia_semana': data_dict['dia_semana'],
            'LOTO_comodin': data_dict['COMODIN'],
        }
        
        # Bolitas Loto
        nums = data_dict.get('LOTO', [])
        for i in range(6): row[f'LOTO_n{i+1}'] = nums[i] if i<len(nums) else 0

        # Bolitas Otros
        for g in ['RECARGADO','REVANCHA','DESQUITE']:
            nums = data_dict.get(g, [])
            for i in range(6): row[f'{g}_n{i+1}'] = nums[i] if i<len(nums) else 0

        # Financieros
        for k, v in data_dict.items():
            if 'GANADORES' in k or 'MONTO' in k:
                row[k] = v

        new_df = pd.DataFrame([row])
        df_final = pd.concat([df, new_df], ignore_index=True)
        
        df_final['sorteo'] = df_final['sorteo'].astype(int)
        df_final.sort_values(by='sorteo', ascending=True, inplace=True)
        df_final.to_csv(CSV_FILE, sep=';', index=False)
        return True
    except Exception as e:
        log(f"Error CSV: {e}", "CRITICAL")
        return False

def run_daily_check():
    log("--- INICIANDO MODO DIARIO ---")
    
    # Verificación de horario (Evitar ejecuciones fantasma en invierno)
    # Si son antes de las 21:00 CL, probablemente es un run programado de "madrugada" UTC que cayó muy temprano local
    now = datetime.datetime.now(TZ_CHILE)
    if now.hour < 21 and now.hour > 6:
        log("Hora local fuera de rango de sorteo. Esperando...", "SLEEP")
        # Opcional: return, pero como tu cron es nocturno, está bien.
    
    try:
        df = pd.read_csv(CSV_FILE, sep=';')
        last_sorteo = int(df['sorteo'].max())
        target_sorteo = last_sorteo + 1
    except:
        target_sorteo = 5210

    log(f"Objetivo: Sorteo {target_sorteo}")

    target_url = get_target_url_via_search(target_sorteo)
    
    if target_url:
        data = extract_sorteo_data(target_url, target_sorteo)
        if data:
            if save_to_csv(data):
                log(f"Sorteo {target_sorteo} capturado.", "SUCCESS")
                git_push_live(target_sorteo)
            else:
                log("Error guardando CSV.", "ERR")
        else:
            log("Datos incompletos en la web.", "WARN")
    else:
        log("Sorteo no disponible aún.", "WAITING")

def run_history_mode(start=5210, end=5360):
    log(f"--- MODO HISTÓRICO ({start}-{end}) ---")
    for s in range(start, end + 1):
        target_url = get_target_url_via_search(s)
        if target_url:
            data = extract_sorteo_data(target_url, s)
            if data and save_to_csv(data):
                log(f"Sorteo {s} OK.", "SUCCESS")
        time.sleep(1.5)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'history':
            run_history_mode(5210, 5360) # Ajusta este rango si necesitas
        else:
            run_daily_check()
    else:
        run_daily_check()
