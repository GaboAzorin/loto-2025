import sys
import datetime
import json
import re
import pandas as pd
from curl_cffi import requests as cureq
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
CSV_FILE = 'LOTO_HISTORIAL_MAESTRO.csv'
# Fuente: Sección de Loto de 24Horas (TVN)
SOURCE_URL = 'https://www.24horas.cl/tesirve/loto'
DEBUG_HTML_FILE = 'debug_view.html'
STATUS_FILE = 'system_status.json'

def save_status(status, message, details=""):
    report = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "message": message,
        "details": details
    }
    print(f"[{status}] {message}")
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False)

def get_html(url):
    """Navegador robusto que simula ser un humano leyendo noticias"""
    try:
        print(f"Consultando fuente: {url}...")
        response = cureq.get(url, impersonate="chrome110", timeout=30)
        return response.text
    except Exception as e:
        print(f"Error de red: {e}")
        return None

def extract_numbers_from_text(text, label):
    """Busca patrones como 'Loto: 1, 2, 3...' usando Regex inteligente"""
    # Patrón: Palabra clave + (espacios/dos puntos) + 6 números separados por guion, coma o espacio
    # Ej: "Loto: 5-10-16-23-26-29" o "Revancha 1, 2, 3..."
    pattern = rf"{label}.*?(\d{{1,2}})[\s\-,]+(\d{{1,2}})[\s\-,]+(\d{{1,2}})[\s\-,]+(\d{{1,2}})[\s\-,]+(\d{{1,2}})[\s\-,]+(\d{{1,2}})"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return [int(n) for n in match.groups()]
    return []

def parse_news_article(html):
    soup = BeautifulSoup(html, 'lxml')
    
    # 1. Extraer Texto Completo de la Noticia
    # Los sitios de noticias suelen poner el contenido en <article> o clases 'article-body'
    article_body = soup.find('article') or soup.find('div', class_=re.compile('body|content'))
    if not article_body:
        return None, "No se encontró el cuerpo de la noticia"
    
    text = article_body.get_text(" ", strip=True)
    
    # 2. Extraer Sorteo (Del título o texto)
    title = soup.title.string
    sorteo_match = re.search(r'sorteo.*?(\d{4})', title + text, re.IGNORECASE)
    sorteo_num = int(sorteo_match.group(1)) if sorteo_match else 0
    
    if sorteo_num == 0:
        return None, "No se pudo identificar el número de sorteo"

    # 3. Extraer Números (La magia del Regex)
    data = {
        'sorteo': sorteo_num,
        'LOTO': extract_numbers_from_text(text, 'Loto'),
        'RECARGADO': extract_numbers_from_text(text, 'Recargado'),
        'REVANCHA': extract_numbers_from_text(text, 'Revancha'),
        'DESQUITE': extract_numbers_from_text(text, 'Desquite')
    }

    # Comodín (Suele estar tras los números del Loto o mencionado aparte)
    # Buscamos "comodín el (número)" o patrón similar
    comodin_match = re.search(r'comod[ií]n.*?(\d{{1,2}})', text, re.IGNORECASE)
    data['COMODIN'] = int(comodin_match.group(1)) if comodin_match else 0

    return data, "Extracción exitosa"

def main():
    print("--- INICIANDO PROTOCOLO DE PRENSA ---")
    
    # 1. Ir a la portada de Loto en 24Horas
    index_html = get_html(SOURCE_URL)
    if not index_html:
        sys.exit(0)

    # 2. Buscar el enlace a la noticia más reciente
    soup_index = BeautifulSoup(index_html, 'lxml')
    # Buscamos enlaces que digan "Resultados Loto" y "sorteo"
    latest_link = None
    for a in soup_index.find_all('a', href=True):
        link_text = a.get_text().lower()
        if 'resultados loto' in link_text and 'sorteo' in link_text:
            latest_link = a['href']
            print(f"Noticia encontrada: {link_text.strip()}")
            break
    
    if not latest_link:
        save_status("WARNING", "No se encontraron noticias recientes de sorteos.")
        sys.exit(0)

    # Corregir URL si es relativa
    if latest_link.startswith('/'):
        latest_link = 'https://www.24horas.cl' + latest_link

    # 3. Entrar a la noticia
    article_html = get_html(latest_link)
    
    # Guardar evidencia para debug
    with open(DEBUG_HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(article_html)

    # 4. Procesar Datos
    extracted_data, msg = parse_news_article(article_html)
    
    if not extracted_data:
        save_status("ERROR", "Fallo al leer noticia", msg)
        sys.exit(0)

    if not extracted_data['LOTO']:
        save_status("ERROR", "Lectura incompleta", "Se encontró el artículo pero no los números del Loto.")
        sys.exit(0)

    print(f"Datos extraídos: {extracted_data}")

    # 5. GUARDAR EN CSV (Lógica Maestra)
    try:
        df = pd.read_csv(CSV_FILE, sep=';')
        
        # Verificar duplicados
        if extracted_data['sorteo'] in df['sorteo'].values:
            save_status("OK", f"Sorteo {extracted_data['sorteo']} ya estaba registrado.")
            sys.exit(0)

        # Fecha (Usamos la de hoy, ya que la noticia es 'reciente')
        now = datetime.datetime.now()
        
        # Construir fila
        new_row = {
            'sorteo': extracted_data['sorteo'],
            'anio': now.year,
            'mes': now.month,
            'dia': now.day,
            'dia_semana': now.strftime('%A'),
            'LOTO_n1': extracted_data['LOTO'][0], 'LOTO_n2': extracted_data['LOTO'][1],
            'LOTO_n3': extracted_data['LOTO'][2], 'LOTO_n4': extracted_data['LOTO'][3],
            'LOTO_n5': extracted_data['LOTO'][4], 'LOTO_n6': extracted_data['LOTO'][5],
            'LOTO_comodin': extracted_data['COMODIN'],
            # Sub juegos
            'RECARGADO_n1': extracted_data['RECARGADO'][0] if extracted_data['RECARGADO'] else 0,
            # ... (Llenar resto de recargado en bucle idealmente, aquí simplificado)
            'LOTO_GANADORES': 0, 'LOTO_MONTO': 0 # Datos financieros no siempre están en la noticia
        }
        
        # Rellenar resto de columnas Recargado/Revancha/Desquite
        for game in ['RECARGADO', 'REVANCHA', 'DESQUITE']:
            nums = extracted_data.get(game, [])
            for i in range(6):
                col_name = f'{game}_n{i+1}'
                new_row[col_name] = nums[i] if i < len(nums) else 0

        # Guardar
        new_df = pd.DataFrame([new_row])
        # Alinear columnas
        for col in df.columns:
            if col not in new_df.columns:
                new_df[col] = 0
        
        df_final = pd.concat([df, new_df[df.columns]], ignore_index=True)
        df_final.to_csv(CSV_FILE, sep=';', index=False)
        
        save_status("OK", f"¡Sorteo {extracted_data['sorteo']} agregado desde 24Horas!")

    except Exception as e:
        save_status("ERROR", "Error guardando CSV", str(e))
        print(e)

    sys.exit(0)

if __name__ == "__main__":
    main()
