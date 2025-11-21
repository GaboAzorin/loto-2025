import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import time
import random
import sys
import json
import os

# CONFIGURACIÓN
CSV_FILE = 'LOTO_HISTORIAL_MAESTRO.csv'
URL = 'https://www.polla.cl/es/view/loto_ultimo_sorteo'
DEBUG_HTML_FILE = 'debug_view.html'
STATUS_FILE = 'system_status.json'

def save_status(status, message, details=None):
    """Guarda un JSON que tu página web podrá leer"""
    report = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status, # "OK", "ERROR", "WARNING"
        "message": message,
        "details": details or ""
    }
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False)

def get_soup_robust(url):
    scraper = cloudscraper.create_scraper()
    try:
        print(f"Intentando acceder a: {url}")
        response = scraper.get(url)
        
        # --- EVIDENCIA FORENSE ---
        # Guardamos EXACTAMENTE lo que ve el robot
        with open(DEBUG_HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(f"\n")
            f.write(response.text)
        print(f"Evidencia guardada en {DEBUG_HTML_FILE}")
        # -------------------------

        if response.status_code == 200:
            return BeautifulSoup(response.text, 'lxml')
        else:
            save_status("ERROR", f"Status Code {response.status_code}", "El sitio rechazó la conexión")
            return None
    except Exception as e:
        save_status("ERROR", "Fallo de Conexión", str(e))
        return None

def main():
    print("--- INICIO DIAGNÓSTICO ---")
    soup = get_soup_robust(URL)
    
    if not soup:
        sys.exit(1)

    # BÚSQUEDA DE NÚMEROS (TEST)
    # Buscamos cualquier indicio de número de sorteo para ver si renderizó
    try:
        # Intentamos buscar el bloque de números típico
        balls = soup.find_all('div', class_='balls-content')
        
        if not balls:
            msg = "No se encontraron bolas (Posible sitio dinámico/JS)"
            print(msg)
            # Analizamos si hay scripts que contengan datos JSON ocultos
            scripts = soup.find_all('script')
            has_json_data = any('Loto' in str(s) for s in scripts)
            
            detail = "Se detectaron scripts con datos posibles." if has_json_data else "HTML parece vacío de datos."
            save_status("WARNING", msg, f"Revisa {DEBUG_HTML_FILE}. {detail}")
            sys.exit(0) # Salimos sin romper, solo reportando
            
        # Si llegamos aquí, ¡SÍ HAY DATOS!
        title = soup.find('h2', class_='title-page').text.strip()
        save_status("OK", "Datos detectados correctamente", f"Se encontró: {title} y {len(balls)} grupos de bolas.")
        print("¡ÉXITO! El sitio parece estático o cloudscraper funcionó.")

        # (Aquí iría el resto de tu lógica de guardado CSV que ya tenías...)
        # Por ahora cortamos aquí para validar el diagnóstico.
        
    except Exception as e:
        save_status("ERROR", "Error analizando HTML", str(e))
        print(e)

if __name__ == "__main__":
    main()
