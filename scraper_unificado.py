import asyncio
import json
import os
import csv
import time
from datetime import datetime
from playwright.async_api import async_playwright

# Importamos tu parser existente
try:
    from loto_parser_v3 import parse_loto_flat
except ImportError:
    print("❌ ERROR: Falta 'loto_parser_v3.py'.")
    exit()

# --- CONFIGURACIÓN ---
CSV_FILENAME = "LOTO_HISTORIAL_MAESTRO.csv"
BASE_URL = "https://www.polla.cl/es/view/resultados"
API_URL = "https://www.polla.cl/es/get/draw/results"
GAME_ID_LOTO = "5271"
SORTEO_INICIAL_DEFAULT = 3803 

# Orden visual para mantener tu CSV ordenado
FIXED_ORDER = [
    "sorteo", "fecha", "LOTO_n1", "LOTO_n2", "LOTO_n3", "LOTO_n4", "LOTO_n5", "LOTO_n6", "LOTO_comodin",
    "LOTO_GANADORES", "LOTO_MONTO", "LOTO_POZO_ACUMULADO",
    "RECARGADO_n1", "RECARGADO_n6", "RECARGADO_6_ACIERTOS_GANADORES", "RECARGADO_POZO_ACUMULADO",
    "REVANCHA_n1", "REVANCHA_n6", "REVANCHA_GANADORES", "REVANCHA_POZO_ACUMULADO",
    "DESQUITE_n1", "DESQUITE_n6", "DESQUITE_GANADORES", "DESQUITE_POZO_ACUMULADO",
    "AHORA_SI_QUE_SI_n1", "AHORA_SI_QUE_SI_n6", "AHORA_SI_QUE_SI_GANADORES", "AHORA_SI_QUE_SI_ACUMULADO"
]

def get_last_draw_id():
    if not os.path.exists(CSV_FILENAME): return SORTEO_INICIAL_DEFAULT - 1
    max_id = 0
    try:
        with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Validamos que el ID sea numérico para evitar errores
                if row.get('sorteo') and row['sorteo'].isdigit():
                    draw_id = int(row['sorteo'])
                    if draw_id > max_id: max_id = draw_id
    except: pass
    return max_id

def save_row(new_rows):
    if not new_rows: return
    file_exists = os.path.exists(CSV_FILENAME)
    
    existing_headers = []
    if file_exists:
        with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
            existing_headers = csv.DictReader(f).fieldnames or []
    
    headers_to_use = existing_headers if existing_headers else FIXED_ORDER

    with open(CSV_FILENAME, 'a', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers_to_use)
        if not file_exists: writer.writeheader()
        
        for row in new_rows:
            # Solo escribimos columnas que existan en el header para evitar errores
            filtered_row = {k: v for k, v in row.items() if k in headers_to_use}
            writer.writerow(filtered_row)
            
    print(f"💾 Guardado sorteo #{new_rows[0]['sorteo']} ({new_rows[0]['fecha']})")

async def run():
    print("--- ⏳ SCRAPER CRONOLÓGICO ---")
    
    last_id = get_last_draw_id()
    current_target = last_id + 1
    print(f"🔎 Buscando siguiente sorteo válido: #{current_target}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("🔑 Obteniendo token...")
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
            if not token: 
                c = await page.content()
                import re
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', c)
                if m: token = m.group(1)
            
            if not token: raise Exception("No token")
        except:
            print("❌ Error de conexión.")
            await browser.close()
            return

        print("✅ Token OK.")
        
        while True:
            try:
                await asyncio.sleep(0.5)
                response = await page.request.post(API_URL, data={
                    "gameId": GAME_ID_LOTO, "drawId": current_target, "csrfToken": token
                }, headers={"x-requested-with": "XMLHttpRequest"})

                if response.status == 200:
                    try: json_data = await response.json()
                    except: json_data = {}

                    if not json_data:
                        print(f"🚫 API vacía.")
                        break
                    
                    # --- VALIDACIÓN TEMPORAL ESTRICTA ---
                    # La fecha viene en milisegundos (timestamp)
                    draw_date_ms = json_data.get('drawDate')
                    
                    if draw_date_ms:
                        # Convertimos a segundos
                        draw_timestamp = draw_date_ms / 1000
                        now_timestamp = time.time() # Hora actual del sistema
                        
                        draw_dt = datetime.fromtimestamp(draw_timestamp)
                        
                        # Si la fecha del sorteo es MAYOR que ahora, detenemos todo.
                        if draw_timestamp > now_timestamp:
                            print(f"\n🛑 DETENIDO: El sorteo #{current_target} está programado para el futuro.")
                            print(f"   📅 Fecha Sorteo: {draw_dt}")
                            print(f"   ⌚ Hora Actual:  {datetime.now()}")
                            print("✅ Tu base de datos está actualizada hasta el último sorteo jugado.")
                            break
                    
                    # Si pasamos la validación de tiempo, guardamos
                    flat_row = parse_loto_flat(json_data)
                    save_row([flat_row])
                    
                    current_target += 1

                else:
                    print(f"❌ Error HTTP {response.status}")
                    break

            except Exception as e:
                print(f"❌ Error técnico: {e}")
                break
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())