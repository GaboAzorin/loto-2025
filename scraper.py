import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import time
import random
import sys
import json
import re

# --- CONFIGURACIÓN ---
CSV_FILE = 'LOTO_HISTORIAL_MAESTRO.csv'
# URL corregida según tu indicación
URL = 'https://www.polla.cl/es/view/resultados' 

# Archivos de reporte para ver en el celular
DEBUG_HTML_FILE = 'debug_view.html'
STATUS_FILE = 'system_status.json'

def save_status(status, message, details=None):
    """Escribe el estado para que tu página web lo muestre"""
    report = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status, 
        "message": message,
        "details": details or ""
    }
    print(f"[{status}] {message}")
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False)

def get_soup_robust(url):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    try:
        print(f"Conectando a: {url} ...")
        response = scraper.get(url, timeout=30)
        
        # 1. GUARDAR EVIDENCIA (Vital para depurar desde el celular)
        with open(DEBUG_HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(f"\n")
            f.write(response.text)
        
        if response.status_code != 200:
            save_status("ERROR", f"Error {response.status_code}", "La página no cargó correctamente.")
            return None

        return BeautifulSoup(response.text, 'lxml')

    except Exception as e:
        save_status("ERROR", "Fallo de Conexión", str(e))
        return None

def extract_json_from_scripts(soup):
    """Intenta encontrar la 'base interna' oculta en el HTML"""
    scripts = soup.find_all('script')
    for i, script in enumerate(scripts):
        if script.string:
            # Buscamos patrones comunes de datos embebidos
            if 'Loto' in script.string or 'results' in script.string:
                return f"¡Datos detectados en Script #{i}! (Ver debug_view.html)"
    return None

def main():
    print("--- INICIANDO PROTOCOLO DE DIAGNÓSTICO V2 ---")
    
    # 1. Obtener Web
    soup = get_soup_robust(URL)
    if not soup:
        sys.exit(1)

    # 2. Análisis Forense
    page_title = soup.title.string.strip() if soup.title else "Sin Título"
    print(f"Título de la página: {page_title}")

    # Buscamos las bolas visualmente
    balls = soup.find_all('div', class_='balls-content')
    
    if balls:
        # CASO 1: Datos Visibles (Fácil)
        msg = f"ÉXITO: Se encontraron {len(balls)} grupos de bolas en el HTML."
        save_status("OK", "Conexión Exitosa", msg)
        print(msg)
        # (Aquí iría la lógica de extracción normal, por ahora validamos conexión)
        
    else:
        # CASO 2: Datos Ocultos / Dinámicos (Difícil)
        print("⚠️ No se vieron bolas en el HTML simple.")
        
        # Intentamos detectar si los datos están escondidos en un JSON
        json_hint = extract_json_from_scripts(soup)
        
        if json_hint:
            save_status("WARNING", "Sitio Dinámico Detectado", f"HTML vacío pero {json_hint}")
        else:
            save_status("ERROR", "HTML Vacío", "La página cargó pero no tiene datos visibles ni scripts obvios.")

if __name__ == "__main__":
    main()
