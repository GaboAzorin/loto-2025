import sys
import datetime
import re
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
    print(f"[{ts}] [{status}] {msg}", flush=True)

def git_push_live(sorteo_num):
    try:
        subprocess.run(["git", "config", "--global", "user.name", "LotoBot"], check=False)
        subprocess.run(["git", "config", "--global", "user.email", "bot@noreply.github.com"], check=False)
        
        subprocess.run(["git", "add", CSV_FILE], check=True)
        msg = f"DATA: Sorteo {sorteo_num} capturado"
        subprocess.run(["git", "commit", "-m", msg], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True)
        log(f"--> Sorteo {sorteo_num} subido a GitHub.", "GIT")
    except Exception as e:
        log(f"Git push omitido (¿Sin cambios?): {e}", "WARN")

def get_html(url):
    try:
        # Usamos chrome110 simple, sin headers manuales para evitar huellas rotas
        response = cureq.get(url, impersonate="chrome110", timeout=30)
        return response.text if response.status_code == 200 else None
    except Exception as e: 
        log(f"Error HTTP: {e}", "ERR")
        return None

def get_target_url_via_search(sorteo_num):
    """Busca ?s=[NUM] y extrae el link real."""
    search_url = f"https://resultadoslotochile.com/?s={sorteo_num}"
    log(f"Buscando enlace para sorteo {sorteo_num}...", "SEARCH")
    
    html = get_html(search_url)
    if not html: return None

    soup = BeautifulSoup(html, 'lxml')
    candidates = []
    
    # Prioridad: Artículos
    for art in soup.find_all('article'):
        link = art.find('a', href=True)
        if link: candidates.append(link)
    
    # Fallback: Todos los links
    if not candidates:
        candidates = soup.find_all('a', href=True)

    for a in candidates:
        text = a.get_text(" ", strip=True).lower()
        href = a['href']
        if str(sorteo_num) in text and ("sorteo" in text or "resultados" in text):
            if "facebook" in href or "twitter" in href: continue
            log(f"Enlace encontrado: {href}", "SUCCESS")
            return href
    return None

def parse_financial_data(soup, data_dict):
    """Extrae montos y ganadores (Logica mejorada)"""
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

    # Inicializar en 0
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
                    # Evitar colisiones (Ej: Súper Quina vs Quina)
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
    
    # Fecha
    meta_date = soup.find('meta', property='article:published_time')
    if meta_date:
        try:
            dt = datetime.datetime.fromisoformat(meta_date['content'])
            data.update({'anio': dt.year, 'mes': dt.month, 'dia': dt.day, 'dia_semana': dt.strftime('%A')})
        except: pass
    
    if 'anio' not in data:
        now = datetime.datetime.now(TZ_CHILE)
        data.update({'anio': now.year, 'mes': now.month, 'dia': now.day, 'dia_semana': now.strftime('%A')})

    # Bolitas
    def get_nums(header_regex):
        h = soup.find(['h3', 'h2'], string=re.compile(header_regex, re.IGNORECASE))
        if not h: return []
        div = h.find_next('div', class_='bolitas')
        return [int(p.text) for p in div.find_all('p') if p.text.strip().isdigit()] if div else []

    data['LOTO'] = get_nums('Loto')
    if not data['LOTO']:
        div = soup.find('div', class_='bolitas')
        if div: data['LOTO'] = [int(p.text) for p in div.find_all('p')]

    if not data['LOTO']: return None # Si no hay Loto, abortamos

    c_div = soup.find('div', class_='comodin')
    data['COMODIN'] = int(c_div.find('p').text) if c_div and c_div.find('p') else 0

    data['RECARGADO'] = get_nums('Recargado')
    data['REVANCHA'] = get_nums('Revancha')
    data['DESQUITE'] = get_nums('Desquite')
    
    # Financiero
    data = parse_financial_data(soup, data)
    
    return data

def save_to_csv(data_dict):
    try:
        try: df = pd.read_csv(CSV_FILE, sep=';')
        except: df = pd.DataFrame()
        
        # Si ya existe, lo reemplazamos
        if 'sorteo' in df.columns:
            df = df[df['sorteo'] != data_dict['sorteo']]

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
            if 'GANADORES' in k or 'MONTO' in k:
                row[k] = v

        df_final = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df_final['sorteo'] = df_final['sorteo'].astype(int)
        df_final.sort_values(by='sorteo', ascending=True, inplace=True)
        df_final.to_csv(CSV_FILE, sep=';', index=False)
        return True
    except Exception as e:
        log(f"Error CSV: {e}", "CRITICAL")
        return False

def run_daily_check():
    log("--- INICIANDO MODO DIARIO ---")
    
    # Verificación horaria simple (evitar runs muertos en la mañana)
    now = datetime.datetime.now(TZ_CHILE)
    if now.hour < 21 and now.hour > 9:
        log("Fuera de horario de sorteo. Terminando.")
        return

    # 1. ¿Qué sorteo toca?
    try:
        df = pd.read_csv(CSV_FILE, sep=';')
        last_sorteo = int(df['sorteo'].max())
        target_sorteo = last_sorteo + 1
    except:
        target_sorteo = 5210

    log(f"Objetivo: Sorteo {target_sorteo}")

    # 2. Buscar
    target_url = get_target_url_via_search(target_sorteo)
    
    if target_url:
        # 3. Extraer
        data = extract_sorteo_data(target_url, target_sorteo)
        if data:
            # 4. Guardar y Push
            if save_to_csv(data):
                log(f"¡ÉXITO! Sorteo {target_sorteo} guardado.", "SUCCESS")
                git_push_live(target_sorteo)
            else:
                log("Falló el guardado en CSV.", "ERR")
        else:
            log("Enlace encontrado pero sin datos válidos.", "WARN")
    else:
        log(f"Sorteo {target_sorteo} aún no disponible.", "WAITING")

if __name__ == "__main__":
    # Sin argumentos, sin historial, solo daily.
    run_daily_check()