import sys
import datetime
import re
import time
import subprocess
import pandas as pd
from curl_cffi import requests as cureq
from bs4 import BeautifulSoup
import pytz # Necesario para la hora de Chile

# --- CONFIGURACIÓN ---
CSV_FILE = 'LOTO_HISTORIAL_MAESTRO.csv'
TZ_CHILE = pytz.timezone('America/Santiago')

def log(msg, status="INFO"):
    # Timestamp en hora Chile
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
        log(f"Git push omitido (probablemente sin cambios): {e}", "WARN")

def get_html(url):
    try:
        # Usamos chrome110 para pasar desapercibidos
        response = cureq.get(url, impersonate="chrome110", timeout=30)
        return response.text if response.status_code == 200 else None
    except Exception as e: 
        log(f"Error HTTP: {e}", "ERR")
        return None

def get_target_url_via_search(sorteo_num):
    """
    Estrategia: Busca en ?s=[NUM] y extrae el link del artículo.
    Basado en la estructura de resultadoslotochile.com
    """
    search_url = f"https://resultadoslotochile.com/?s={sorteo_num}"
    log(f"Buscando enlace para sorteo {sorteo_num} en: {search_url}...", "SEARCH")
    
    html = get_html(search_url)
    if not html: return None

    soup = BeautifulSoup(html, 'lxml')
    
    # Buscamos artículos. Según tu estructura, suelen ser <article> -> <h2> -> <a>
    articles = soup.find_all('article')
    
    candidates = []
    
    # Estrategia 1: Buscar dentro de articles (Más preciso)
    for art in articles:
        link = art.find('a', href=True)
        if link:
            candidates.append(link)
            
    # Estrategia 2: Si falla, buscar todos los links en el main (Fallback)
    if not candidates:
        main_content = soup.find('main') or soup.body
        if main_content:
            candidates = main_content.find_all('a', href=True)

    # Filtrado final por texto
    for a in candidates:
        text = a.get_text(" ", strip=True).lower()
        href = a['href']
        
        # Debe contener el número del sorteo Y la palabra sorteo o resultados
        # Y NO debe ser un link a "paginas" (page/2) o comentarios
        if str(sorteo_num) in text and ("sorteo" in text or "resultados" in text):
            # Excluir enlaces basura si los hubiera
            if "facebook" in href or "twitter" in href: continue
            
            log(f"Enlace encontrado: {href}", "SUCCESS")
            return href

    log("No se encontró enlace en los resultados de búsqueda.", "404")
    return None

def parse_financial_data(soup, data_dict):
    """Extrae la tabla de premios si existe"""
    # Inicializar en 0
    financial_cols = [
        'LOTO', 'SUPER_QUINA_5_ACIERTOS_COMODIN', 'QUINA_5_ACIERTOS', 
        'SUPER_CUATERNA_4_ACIERTOS_COMODIN', 'CUATERNA_4_ACIERTOS', 
        'SUPER_TERNA_3_ACIERTOS_COMODIN', 'TERNA_3_ACIERTOS', 
        'SUPER_DUPLA_2_ACIERTOS_COMODIN', 'RECARGADO_6_ACIERTOS', 
        'REVANCHA', 'DESQUITE', 'JUBILAZO', 'JUBILAZO_50'
    ]
    for col in financial_cols:
        data_dict[f'{col}_GANADORES'] = 0
        data_dict[f'{col}_MONTO'] = 0

    table = soup.find('table', class_='table-prizes')
    if not table: return data_dict

    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) >= 3:
            cat = cols[0].get_text(" ", strip=True).lower()
            monto_raw = cols[1].get_text(strip=True)
            gan_raw = cols[2].get_text(strip=True)
            
            monto = int(re.sub(r'\D', '', monto_raw) or 0)
            ganadores = int(re.sub(r'\D', '', gan_raw) or 0)

            target = None
            if 'loto' in cat and '6 aciertos' in cat: target = 'LOTO'
            elif 'súper quina' in cat: target = 'SUPER_QUINA_5_ACIERTOS_COMODIN'
            elif 'quina' in cat: target = 'QUINA_5_ACIERTOS'
            elif 'súper cuaterna' in cat: target = 'SUPER_CUATERNA_4_ACIERTOS_COMODIN'
            elif 'cuaterna' in cat: target = 'CUATERNA_4_ACIERTOS'
            elif 'súper terna' in cat: target = 'SUPER_TERNA_3_ACIERTOS_COMODIN'
            elif 'terna' in cat: target = 'TERNA_3_ACIERTOS'
            elif 'súper dupla' in cat: target = 'SUPER_DUPLA_2_ACIERTOS_COMODIN'
            elif 'recargado' in cat: target = 'RECARGADO_6_ACIERTOS'
            elif 'revancha' in cat: target = 'REVANCHA'
            elif 'desquite' in cat: target = 'DESQUITE'
            
            if target:
                data_dict[f'{target}_GANADORES'] = ganadores
                data_dict[f'{target}_MONTO'] = monto
                
    return data_dict

def extract_sorteo_data(url, expected_sorteo):
    html = get_html(url)
    if not html: return None
    soup = BeautifulSoup(html, 'lxml')

    # Validación básica de seguridad
    if str(expected_sorteo) not in soup.text:
        log("El HTML destino no parece contener el número de sorteo esperado.", "WARN")
        # Continuamos igual por si acaso está en una imagen o estructura rara, 
        # pero es una advertencia.

    data = {'sorteo': expected_sorteo}
    
    # 1. Fecha
    meta_date = soup.find('meta', property='article:published_time')
    if meta_date:
        try:
            dt = datetime.datetime.fromisoformat(meta_date['content'])
            data.update({'anio': dt.year, 'mes': dt.month, 'dia': dt.day, 'dia_semana': dt.strftime('%A')})
        except: pass
    
    # Si falla la fecha meta, usar fallback de hoy (se corregirá en historial si es necesario)
    if 'anio' not in data:
        now = datetime.datetime.now(TZ_CHILE)
        data.update({'anio': now.year, 'mes': now.month, 'dia': now.day, 'dia_semana': now.strftime('%A')})

    # 2. Números (Función auxiliar)
    def get_nums(header_regex):
        # Busca h3 o h2 que contenga el texto
        h = soup.find(['h3', 'h2'], string=re.compile(header_regex, re.IGNORECASE))
        if not h: return []
        div = h.find_next('div', class_='bolitas')
        if not div: return []
        return [int(p.text) for p in div.find_all('p') if p.text.strip().isdigit()]

    data['LOTO'] = get_nums('Loto')
    # Fallback si Loto es el primer bloque sin header claro
    if not data['LOTO']:
        first_bolitas = soup.find('div', class_='bolitas')
        if first_bolitas: 
            data['LOTO'] = [int(p.text) for p in first_bolitas.find_all('p') if p.text.strip().isdigit()]

    if not data['LOTO']:
        log("No se pudieron extraer los números del Loto.", "ERR")
        return None

    # Comodín
    c_div = soup.find('div', class_='comodin')
    data['COMODIN'] = int(c_div.find('p').text) if c_div and c_div.find('p') else 0

    data['RECARGADO'] = get_nums('Recargado')
    data['REVANCHA'] = get_nums('Revancha')
    data['DESQUITE'] = get_nums('Desquite')
    data['JUBILAZO'] = get_nums('Jubilazo') # A veces hay

    # 3. Datos Financieros
    data = parse_financial_data(soup, data)
    
    return data

def save_to_csv(data_dict):
    try:
        try: df = pd.read_csv(CSV_FILE, sep=';')
        except: df = pd.DataFrame()

        # Evitar duplicados: Si ya existe, lo borramos para actualizarlo
        if 'sorteo' in df.columns:
            df = df[df['sorteo'] != data_dict['sorteo']]

        # Aplanar fila
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
        
        # Ordenar y guardar
        df_final['sorteo'] = df_final['sorteo'].astype(int)
        df_final.sort_values(by='sorteo', ascending=True, inplace=True)
        df_final.to_csv(CSV_FILE, sep=';', index=False)
        return True
    except Exception as e:
        log(f"Error escribiendo CSV: {e}", "CRITICAL")
        return False

def run_daily_check():
    log("--- INICIANDO MODO DIARIO (SNIPER) ---")
    
    # 1. Obtener último sorteo del CSV
    try:
        df = pd.read_csv(CSV_FILE, sep=';')
        last_sorteo = int(df['sorteo'].max())
        target_sorteo = last_sorteo + 1
    except:
        log("No se pudo leer el último sorteo. Por defecto buscando 5210.", "WARN")
        target_sorteo = 5210

    log(f"Buscando Sorteo Objetivo: {target_sorteo}")

    # 2. Buscar URL
    target_url = get_target_url_via_search(target_sorteo)
    
    if target_url:
        # 3. Extraer
        data = extract_sorteo_data(target_url, target_sorteo)
        if data:
            # 4. Guardar
            if save_to_csv(data):
                log(f"¡ÉXITO! Sorteo {target_sorteo} guardado.", "SUCCESS")
                git_push_live(target_sorteo)
            else:
                log("Falló el guardado en CSV.", "ERR")
        else:
            log("Enlace encontrado pero falló la extracción de datos (¿Estructura incompleta?)", "ERR")
    else:
        log(f"Sorteo {target_sorteo} aún no disponible en el buscador.", "WAITING")

def run_history_mode(start=5210, end=5360):
    log(f"--- MODO HISTÓRICO ({start} - {end}) ---")
    for s in range(start, end + 1):
        target_url = get_target_url_via_search(s)
        if target_url:
            data = extract_sorteo_data(target_url, s)
            if data and save_to_csv(data):
                log(f"Sorteo {s} recuperado.", "SUCCESS")
            else:
                log(f"Sorteo {s} falló en extracción.", "ERR")
        else:
            log(f"Sorteo {s} no encontrado.", "MISSING")
        time.sleep(2) # Respeto al servidor

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == 'history':
            # Puedes ajustar estos números manualmente si necesitas reparar un rango
            run_history_mode(5210, 5360)
        else:
            run_daily_check()
    else:
        # Por defecto
        run_daily_check()
