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
    full_msg = f"[{ts}] [{status}] {msg}"
    print(full_msg, flush=True)
    # Opcional: Escribir a archivo si lo deseas para el artefacto
    with open("ejecucion.log", "a") as f:
        f.write(full_msg + "\n")

def git_push_live(sorteo_num):
    try:
        subprocess.run(["git", "config", "--global", "user.name", "LotoBot"], check=False)
        subprocess.run(["git", "config", "--global", "user.email", "bot@noreply.github.com"], check=False)
        
        subprocess.run(["git", "add", CSV_FILE], check=True)
        # Verificamos si hay cambios antes de commitear para evitar errores
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not status.stdout.strip():
            log("No hay cambios nuevos para subir.", "GIT")
            return

        msg = f"DATA: Sorteo {sorteo_num} capturado"
        subprocess.run(["git", "commit", "-m", msg], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push"], check=True)
        log(f"--> Sorteo {sorteo_num} subido a GitHub.", "GIT")
    except Exception as e:
        log(f"Git push omitido o falló: {e}", "WARN")

def get_html(url):
    try:
        response = cureq.get(url, impersonate="chrome110", timeout=30)
        return response.text if response.status_code == 200 else None
    except Exception as e: 
        log(f"Error HTTP: {e}", "ERR")
        return None

def get_target_url_via_search(sorteo_num):
    search_url = f"https://resultadoslotochile.com/?s={sorteo_num}"
    log(f"Buscando enlace para sorteo {sorteo_num}...", "SEARCH")
    
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
        # Validamos que sea el sorteo correcto y no uno viejo o relacionado
        if str(sorteo_num) in text and ("sorteo" in text or "resultados" in text):
            if "facebook" in href or "twitter" in href: continue
            log(f"Enlace potencial encontrado: {href}", "SUCCESS")
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

    # --- NUEVA VALIDACIÓN: ¿ESTÁ EL RESULTADO PENDIENTE? ---
    # Buscamos el texto exacto que aparece en tu archivo 'codigo_fuente_sin_resultado.txt'
    pending_text = soup.find(string=re.compile("ESTAMOS ESPERANDO LOS RESULTADOS", re.IGNORECASE))
    if pending_text:
        log("La página existe, pero los resultados AÚN NO ESTÁN PUBLICADOS (Estado: Esperando).", "WAITING")
        return None

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
    
    # Segunda validación: Si no hay números de Loto, asumimos que no es válido
    if not data['LOTO']: 
        # Intento de fallback generico
        div = soup.find('div', class_='bolitas')
        if div: data['LOTO'] = [int(p.text) for p in div.find_all('p') if p.text.strip().isdigit()]
    
    if not data['LOTO']:
        log("Página accedida pero no se encontraron bolitas de Loto válidas.", "WARN")
        return None

    c_div = soup.find('div', class_='comodin')
    data['COMODIN'] = int(c_div.find('p').text) if c_div and c_div.find('p') else 0

    data['RECARGADO'] = get_nums('Recargado')
    data['REVANCHA'] = get_nums('Revancha')
    data['DESQUITE'] = get_nums('Desquite')
    
    data = parse_financial_data(soup, data)
    
    return data

def save_to_csv(data_dict):
    try:
        try: df = pd.read_csv(CSV_FILE, sep=',')
        except: df = pd.DataFrame()
        
        if 'sorteo' in df.columns:
            # Eliminamos si ya existe para sobrescribirlo con la data fresca
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
        df_final.to_csv(CSV_FILE, sep=',', index=False)
        return True
    except Exception as e:
        log(f"Error CSV: {e}", "CRITICAL")
        return False

def run_daily_check():
    log("--- INICIANDO MODO DIARIO ---")
    
    # 1. Determinar el último sorteo registrado
    try:
        df = pd.read_csv(CSV_FILE, sep=',')
        last_sorteo = int(df['sorteo'].max())
        target_sorteo = last_sorteo + 1
    except:
        target_sorteo = 5352 # Fallback si no hay CSV

    # --- OPTIMIZACIÓN IMPORTANTE ---
    # Si el script corre cada 30 min, debemos asegurarnos de no procesar lo que ya tenemos.
    # Pero como target_sorteo es last + 1, si ya lo tenemos, el target será el siguiente.
    # El problema es si corremos el script un Martes, encontramos el sorteo 5000.
    # A la media hora corre de nuevo, target será 5001. Pero 5001 es JUEVES.
    # No queremos buscar 5001 el martes a las 23:00.
    
    # Lógica simple: Intentamos buscar target_sorteo.
    log(f"Objetivo actual según CSV: Sorteo {target_sorteo}")

    target_url = get_target_url_via_search(target_sorteo)
    
    if target_url:
        data = extract_sorteo_data(target_url, target_sorteo)
        if data:
            if save_to_csv(data):
                log(f"¡ÉXITO! Sorteo {target_sorteo} guardado.", "SUCCESS")
                git_push_live(target_sorteo)
            else:
                log("Falló el guardado en CSV.", "ERR")
        else:
            # Aquí cae si devuelve None por "ESTAMOS ESPERANDO RESULTADOS" o falta de bolitas
            log("Datos no extraídos (Página en espera o estructura inválida).", "SKIP")
    else:
        log(f"Sorteo {target_sorteo} aún no indexado o no encontrado en búsqueda.", "WAITING")

if __name__ == "__main__":
    # Capturar argumentos del sistema (pasados por scrape.yml)
    mode = sys.argv[1] if len(sys.argv) > 1 else 'daily'
    
    if mode == 'daily':
        run_daily_check()
    elif mode == 'history':
        log("Modo histórico no implementado en este snippet, usa el loop antiguo si es necesario.", "INFO")
    else:
        # Por defecto daily si falla algo
        run_daily_check()