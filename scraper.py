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
LOG_FILE = 'ejecucion.log'  # Nuevo archivo de registro
TZ_CHILE = pytz.timezone('America/Santiago')

def log(msg, status="INFO"):
    """Imprime en consola y guarda en archivo al mismo tiempo"""
    now_chile = datetime.datetime.now(TZ_CHILE)
    ts = now_chile.strftime("%H:%M:%S")
    formatted_msg = f"[{ts}] [{status}] {msg}"
    
    # 1. Imprimir en consola (GitHub Actions Logs)
    print(formatted_msg, flush=True)
    
    # 2. Guardar en archivo local (Para descargar después)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except:
        pass

def git_push_bulk(msg_commit):
    """Función específica para subir cambios masivos o logs"""
    try:
        subprocess.run(["git", "config", "--global", "user.name", "LotoBot"], check=False)
        subprocess.run(["git", "config", "--global", "user.email", "bot@noreply.github.com"], check=False)
        
        # Agregamos CSV y el LOG
        subprocess.run(["git", "add", CSV_FILE], check=False)
        subprocess.run(["git", "add", LOG_FILE], check=False)
        
        # Commit y Push
        subprocess.run(["git", "commit", "-m", msg_commit], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True)
        log(f"--> PUSH EXITOSO: {msg_commit}", "GIT")
    except subprocess.CalledProcessError:
        log("Nada que subir (sin cambios en CSV o Log).", "GIT")
    except Exception as e:
        log(f"Error fatal en Git Push: {e}", "CRITICAL")

def get_html(url):
    try:
        response = cureq.get(url, impersonate="chrome110", timeout=30)
        return response.text if response.status_code == 200 else None
    except Exception as e: 
        log(f"Error HTTP {url}: {e}", "ERR")
        return None

def get_target_url_via_search(sorteo_num):
    search_url = f"https://resultadoslotochile.com/?s={sorteo_num}"
    log(f"Buscando URL para sorteo {sorteo_num}...", "SEARCH")
    
    html = get_html(search_url)
    if not html: return None

    soup = BeautifulSoup(html, 'lxml')
    candidates = []
    for art in soup.find_all('article'):
        link = art.find('a', href=True)
        if link: candidates.append(link)
    
    if not candidates:
        candidates = soup.find_all('a', href=True)

    for a in candidates:
        text = a.get_text(" ", strip=True).lower()
        href = a['href']
        if str(sorteo_num) in text and ("sorteo" in text or "resultados" in text):
            if "facebook" in href or "twitter" in href: continue
            log(f"Enlace detectado: {href}", "FOUND")
            return href
    return None

def parse_financial_data(soup, data_dict):
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
    for key in financial_targets:
        data_dict[f'{key}_GANADORES'] = 0
        data_dict[f'{key}_MONTO'] = 0

    table = soup.find('table', class_='table-prizes')
    if not table: return data_dict

    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) >= 3:
            cat_text = cols[0].get_text(" ", strip=True).lower()
            monto = int(re.sub(r'\D', '', cols[1].get_text(strip=True)) or 0)
            ganadores = int(re.sub(r'\D', '', cols[2].get_text(strip=True)) or 0)

            for db_key, search_terms in financial_targets.items():
                if any(term in cat_text for term in search_terms):
                    # Filtros anti-colisión
                    if db_key == 'QUINA_5_ACIERTOS' and 'súper' in cat_text: continue
                    if db_key == 'CUATERNA_4_ACIERTOS' and 'súper' in cat_text: continue
                    if db_key == 'TERNA_3_ACIERTOS' and 'súper' in cat_text: continue
                    
                    data_dict[f'{db_key}_GANADORES'] = ganadores
                    data_dict[f'{db_key}_MONTO'] = monto
                    break
    return data_dict

def extract_sorteo_data(url, expected_sorteo):
    html = get_html(url)
    if not html: return None
    soup = BeautifulSoup(html, 'lxml')
    data = {'sorteo': expected_sorteo}
    
    meta_date = soup.find('meta', property='article:published_time')
    if meta_date:
        try:
            dt = datetime.datetime.fromisoformat(meta_date['content'])
            data.update({'anio': dt.year, 'mes': dt.month, 'dia': dt.day, 'dia_semana': dt.strftime('%A')})
        except: pass
    
    if 'anio' not in data:
        now = datetime.datetime.now(TZ_CHILE)
        data.update({'anio': now.year, 'mes': now.month, 'dia': now.day, 'dia_semana': now.strftime('%A')})

    def get_nums(header_regex):
        h = soup.find(['h3', 'h2'], string=re.compile(header_regex, re.IGNORECASE))
        if not h: return []
        div = h.find_next('div', class_='bolitas')
        return [int(p.text) for p in div.find_all('p') if p.text.strip().isdigit()] if div else []

    data['LOTO'] = get_nums('Loto')
    if not data['LOTO']:
        div = soup.find('div', class_='bolitas')
        if div: data['LOTO'] = [int(p.text) for p in div.find_all('p')]

    if not data['LOTO']: return None

    c_div = soup.find('div', class_='comodin')
    data['COMODIN'] = int(c_div.find('p').text) if c_div and c_div.find('p') else 0
    data['RECARGADO'] = get_nums('Recargado')
    data['REVANCHA'] = get_nums('Revancha')
    data['DESQUITE'] = get_nums('Desquite')
    data = parse_financial_data(soup, data)
    return data

def save_to_csv(data_dict):
    try:
        try: df = pd.read_csv(CSV_FILE, sep=';')
        except: df = pd.DataFrame()
        
        if 'sorteo' in df.columns: df = df[df['sorteo'] != data_dict['sorteo']]
        
        row = {
            'sorteo': data_dict['sorteo'],
            'anio': data_dict['anio'], 'mes': data_dict['mes'], 'dia': data_dict['dia'],
            'dia_semana': data_dict['dia_semana'],
            'LOTO_comodin': data_dict['COMODIN'],
        }
        nums = data_dict.get('LOTO', [])
        for i in range(6): row[f'LOTO_n{i+1}'] = nums[i] if i<len(nums) else 0
        for g in ['RECARGADO','REVANCHA','DESQUITE']:
            nums = data_dict.get(g, [])
            for i in range(6): row[f'{g}_n{i+1}'] = nums[i] if i<len(nums) else 0
        for k, v in data_dict.items():
            if 'GANADORES' in k or 'MONTO' in k: row[k] = v

        df_final = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df_final['sorteo'] = df_final['sorteo'].astype(int)
        df_final.sort_values(by='sorteo', ascending=True, inplace=True)
        df_final.to_csv(CSV_FILE, sep=';', index=False)
        return True
    except Exception as e:
        log(f"Error CSV: {e}", "CRITICAL")
        return False

def run_daily_check():
    log("=== MODO DIARIO ===")
    now = datetime.datetime.now(TZ_CHILE)
    # Lógica de horario (Opcional, la puedes comentar si quieres testear forzado)
    if now.hour < 21 and now.hour > 6:
        log("Fuera de horario de sorteo. Terminando.")
        return

    try:
        df = pd.read_csv(CSV_FILE, sep=';')
        target = int(df['sorteo'].max()) + 1
    except: target = 5210
    
    url = get_target_url_via_search(target)
    if url:
        data = extract_sorteo_data(url, target)
        if data and save_to_csv(data):
            git_push_bulk(f"DIARIO: Sorteo {target} agregado")
        else: log("Fallo en extracción/guardado")
    else: log("No encontrado")

def run_history_mode(start=5210, end=5360):
    log(f"=== MODO HISTÓRICO ({start}-{end}) ===")
    count = 0
    for s in range(start, end + 1):
        url = get_target_url_via_search(s)
        if url:
            data = extract_sorteo_data(url, s)
            if data and save_to_csv(data):
                log(f"Sorteo {s} recuperado.", "OK")
                count += 1
            else: log(f"Sorteo {s} error data.", "ERR")
        else: log(f"Sorteo {s} sin URL.", "404")
        time.sleep(1.5)
    
    # AL FINALIZAR EL BUCLE, SUBIMOS TODO DE UNA VEZ
    if count > 0:
        git_push_bulk(f"HISTORIAL: {count} sorteos actualizados")
    else:
        log("Fin del proceso histórico sin nuevos datos.")

if __name__ == "__main__":
    # Limpiamos el log anterior al iniciar una nueva ejecución
    with open(LOG_FILE, "w") as f: f.write(f"Inicio ejecución: {datetime.datetime.now()}\n")

    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == 'history':
            run_history_mode(5210, 5360) # <--- OJO: Ajusta este rango según necesites
        else:
            run_daily_check()
    else:
        run_daily_check()
