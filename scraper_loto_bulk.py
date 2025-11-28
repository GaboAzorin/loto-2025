import asyncio
import json
import os
import csv
import random
import time
from datetime import datetime
from playwright.async_api import async_playwright

# Importamos tu parser (asegúrate de que loto_parser_v3.py esté en la misma carpeta)
from loto_parser_v3 import parse_loto_flat

# --- CONFIGURACIÓN ---
CSV_FILENAME = "LOTO_HISTORIAL_MAESTRO.csv"
BASE_URL = "https://www.polla.cl/es/view/resultados"
API_URL = "https://www.polla.cl/es/get/draw/results"
GAME_ID_LOTO = "5271"

# Sorteo inicial histórico (2016)
SORTEO_INICIAL_DEFAULT = 3803 

def get_last_draw_id():
    """
    Determina desde qué número empezar.
    """
    if not os.path.exists(CSV_FILENAME):
        print("📂 No se encontró base de datos. Se creará una nueva desde cero.")
        return SORTEO_INICIAL_DEFAULT - 1
    
    max_id = 0
    try:
        with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('sorteo') and row['sorteo'].isdigit():
                    draw_id = int(row['sorteo'])
                    if draw_id > max_id:
                        max_id = draw_id
    except Exception as e:
        print(f"⚠️ Error leyendo CSV: {e}")
        return SORTEO_INICIAL_DEFAULT - 1
        
    return max_id

def append_to_csv(new_rows):
    """
    Guarda los datos en el CSV, manejando la creación de columnas dinámicas.
    """
    if not new_rows:
        return

    existing_rows = []
    existing_headers = []
    
    if os.path.exists(CSV_FILENAME):
        with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                existing_headers = reader.fieldnames
            existing_rows = list(reader)

    # Detectar nuevas columnas
    all_keys = set(existing_headers)
    for row in new_rows:
        all_keys.update(row.keys())
    
    final_headers = list(existing_headers)
    for k in sorted(list(all_keys)):
        if k not in final_headers:
            final_headers.append(k)
            
    # Orden cosmético
    priority_cols = ['sorteo', 'fecha', 'dia', 'mes', 'anio', 'dia_semana']
    for p in reversed(priority_cols):
        if p in final_headers:
            final_headers.remove(p)
            final_headers.insert(0, p)

    all_rows = existing_rows + new_rows

    print(f"💾 Guardando {len(new_rows)} registros nuevos (Total acumulado: {len(all_rows)})...")
    with open(CSV_FILENAME, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=final_headers)
        writer.writeheader()
        writer.writerows(all_rows)

async def run():
    print("--- 🏗️ INICIANDO CARGA MASIVA DE DATOS (BULK LOAD V3) ---")
    
    last_id = get_last_draw_id()
    current_target = last_id + 1
    print(f"🚀 Objetivo inicial: Sorteo #{current_target}")

    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        print("🔑 Obteniendo credenciales en Polla.cl...")
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            print("⏳ Esperando 5 segundos para carga inicial...")
            await asyncio.sleep(5)
            
            token = await page.evaluate("""() => {
                let input = document.querySelector('input[name="csrfToken"]');
                return input ? input.value : null;
            }""")
            
            if not token:
                content = await page.content()
                import re
                match = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
                token = match.group(1) if match else None

            if not token:
                print("❌ No se encontró token. Revisa el navegador abierto por si hay Captcha.")
                await asyncio.sleep(30)
                raise Exception("No se pudo obtener el Token CSRF tras espera")
                
        except Exception as e:
            print(f"❌ Error obteniendo token: {e}")
            await browser.close()
            return

        print(f"✅ Token capturado. Iniciando descarga masiva desde #{current_target}...")

        consecutive_errors = 0
        new_data_buffer = []
        
        while True:
            print(f"   -> Descargando sorteo #{current_target}...", end=" ")
            
            try:
                # Retardo aleatorio
                await asyncio.sleep(random.uniform(0.5, 1.5))

                response = await page.request.post(API_URL, data={
                    "gameId": GAME_ID_LOTO,
                    "drawId": current_target,
                    "csrfToken": token
                }, headers={
                    "x-requested-with": "XMLHttpRequest",
                    "content-type": "application/json",
                    "origin": "https://www.polla.cl",
                    "referer": BASE_URL
                })

                if response.status == 200:
                    response_text = await response.text()
                    try:
                        json_data = json.loads(response_text)
                    except:
                        json_data = {}
                    
                    # CORRECCIÓN DE LA VALIDACIÓN
                    # Ya no validamos json_data.get('id') porque suele ser null en sorteos viejos
                    draw_num_res = json_data.get('drawNumber')
                    
                    if not json_data or draw_num_res != current_target:
                         # Si el número devuelto no es el que pedimos, es un error real.
                         preview = response_text[:100].replace('\n', ' ')
                         print(f"⚠️ Mismatch. Pedido: {current_target}, Recibido: {draw_num_res}. Resp: {preview}...")
                         consecutive_errors += 1
                    else:
                        print("✅ OK")
                        flat_row = parse_loto_flat(json_data)
                        new_data_buffer.append(flat_row)
                        consecutive_errors = 0 

                        # Guardamos cada 10 sorteos
                        if len(new_data_buffer) >= 10:
                            append_to_csv(new_data_buffer)
                            new_data_buffer = []

                        current_target += 1
                        
                else:
                    print(f"❌ HTTP {response.status}")
                    consecutive_errors += 1

            except Exception as e:
                print(f"❌ Error: {e}")
                consecutive_errors += 1

            # Si fallamos 5 veces seguidas, paramos
            if consecutive_errors >= 5:
                print("\n🛑 Fin del scraping (5 errores consecutivos o fin de historial).")
                break
            
        # Guardar lo último que quedó en memoria
        if new_data_buffer:
            append_to_csv(new_data_buffer)

        await browser.close()
        print("🏁 Base de datos actualizada con éxito.")

if __name__ == "__main__":
    asyncio.run(run())