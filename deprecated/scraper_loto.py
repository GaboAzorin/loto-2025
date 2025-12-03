import asyncio
import json
import os
import csv
import random
from playwright.async_api import async_playwright
from loto_parser_v3 import parse_loto_flat

# CONFIGURACIÓN
CSV_FILENAME = "LOTO_HISTORIAL_MAESTRO.csv"
BASE_URL = "https://www.polla.cl/es/view/resultados"
API_URL = "https://www.polla.cl/es/get/draw/results"
GAME_ID_LOTO = "5271"
SORTEO_INICIAL = 3803

def get_last_id():
    if not os.path.exists(CSV_FILENAME): return SORTEO_INICIAL - 1
    max_id = 0
    with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('sorteo', '').isdigit():
                draw_id = int(row['sorteo'])
                if draw_id > max_id: max_id = draw_id
    return max_id

def save_data(new_rows):
    if not new_rows: return
    mode = 'a' if os.path.exists(CSV_FILENAME) else 'w'
    
    # Leer headers existentes o crear nuevos
    existing_headers = []
    if os.path.exists(CSV_FILENAME):
        with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_headers = reader.fieldnames or []

    # Unificar headers
    all_keys = set(existing_headers)
    for r in new_rows: all_keys.update(r.keys())
    
    final_headers = list(existing_headers)
    for k in sorted(list(all_keys)):
        if k not in final_headers: final_headers.append(k)

    # Si hay headers nuevos, hay que reescribir todo el archivo (lamentablemente)
    if len(final_headers) > len(existing_headers):
        print("⚠️ Nuevas columnas detectadas. Reescribiendo archivo...")
        all_rows = []
        if os.path.exists(CSV_FILENAME):
            with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
                all_rows = list(csv.DictReader(f))
        all_rows.extend(new_rows)
        
        with open(CSV_FILENAME, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=final_headers)
            writer.writeheader()
            writer.writerows(all_rows)
    else:
        # Si no hay columnas nuevas, solo agregamos al final (más rápido)
        with open(CSV_FILENAME, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=final_headers)
            if mode == 'w': writer.writeheader()
            writer.writerows(new_rows)
            
    print(f"💾 Guardados {len(new_rows)} registros.")

async def run():
    print("--- 🏠 SCRAPER LOCAL (MODO HOGAR) ---")
    current_target = get_last_id() + 1
    print(f"🚀 Iniciando desde sorteo #{current_target}")

    async with async_playwright() as p:
        # Usamos Firefox con cabeza (visible) para que veas qué pasa
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1280, 'height': 720})
        page = await context.new_page()

        print("🔑 Entrando a Polla.cl...")
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await asyncio.sleep(3) # Espera humana

        # Token
        token = await page.evaluate("() => document.querySelector('input[name=\"csrfToken\"]')?.value")
        if not token:
            print("❌ No se encontró token. Revisa si hay Captcha.")
            return
        
        print(f"✅ Token: {token[:10]}...")

        buffer = []
        errors = 0
        
        while True:
            print(f"   Query #{current_target}...", end="\r")
            try:
                resp = await page.request.post(API_URL, data={
                    "gameId": GAME_ID_LOTO, "drawId": current_target, "csrfToken": token
                }, headers={"x-requested-with": "XMLHttpRequest"})

                if resp.status == 200:
                    data = await resp.json()
                    if not data or data.get('drawNumber') != current_target:
                        print(f"\n⚠️ Fin de datos o respuesta vacía ({current_target})")
                        errors += 1
                    else:
                        row = parse_loto_flat(data)
                        buffer.append(row)
                        errors = 0
                        current_target += 1
                        
                        if len(buffer) >= 10:
                            save_data(buffer)
                            buffer = []
                else:
                    print(f"\n❌ Error API: {resp.status}")
                    errors += 1
                
                if errors >= 3: break
                await asyncio.sleep(0.5) # Velocidad normal de casa

            except Exception as e:
                print(f"\n❌ Error: {e}")
                break

        if buffer: save_data(buffer)
        await browser.close()
        print("\n🏁 Listo.")

if __name__ == "__main__":
    asyncio.run(run())