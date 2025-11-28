import asyncio
import json
import os
import csv
import random
import time
from datetime import datetime
from playwright.async_api import async_playwright

from loto_parser_v3 import parse_loto_flat

# --- CONFIGURACIÓN ---
CSV_FILENAME = "LOTO_HISTORIAL_MAESTRO.csv"
BASE_URL = "https://www.polla.cl/es/view/resultados"
API_URL = "https://www.polla.cl/es/get/draw/results"
GAME_ID_LOTO = "5271"
SORTEO_INICIAL_DEFAULT = 3803 

# 1. ORDEN FIJO (Metadata + Loto + Divisiones)
FIXED_START_ORDER = [
    "sorteo", "fecha", "dia", "mes", "anio", "dia_semana",
    "LOTO_n1", "LOTO_n2", "LOTO_n3", "LOTO_n4", "LOTO_n5", "LOTO_n6", "LOTO_comodin",
    "LOTO_GANADORES", "LOTO_MONTO", "LOTO_POZO_ACUMULADO",
    "SUPER_QUINA_5_ACIERTOS_COMODIN_GANADORES", "SUPER_QUINA_5_ACIERTOS_COMODIN_MONTO",
    "QUINA_5_ACIERTOS_GANADORES", "QUINA_5_ACIERTOS_MONTO",
    "SUPER_CUATERNA_4_ACIERTOS_COMODIN_GANADORES", "SUPER_CUATERNA_4_ACIERTOS_COMODIN_MONTO",
    "CUATERNA_4_ACIERTOS_GANADORES", "CUATERNA_4_ACIERTOS_MONTO",
    "SUPER_TERNA_3_ACIERTOS_COMODIN_GANADORES", "SUPER_TERNA_3_ACIERTOS_COMODIN_MONTO",
    "TERNA_3_ACIERTOS_GANADORES", "TERNA_3_ACIERTOS_MONTO",
    "SUPER_DUPLA_2_ACIERTOS_COMODIN_GANADORES", "SUPER_DUPLA_2_ACIERTOS_COMODIN_MONTO"
]

# 2. ORDEN SEMIESTÁTICO (Juegos Principales Adicionales)
# Aquí definimos el orden lógico de la tómbola:
# Loto -> [Ahora Si Que Si / Recargado] -> Revancha -> Desquite
PREFERRED_GAMES_ORDER = [
    # AHORA SÍ QUE SÍ (Juego antiguo, prioridad alta antes de Revancha)
    "AHORA_SI_QUE_SI_n1", "AHORA_SI_QUE_SI_n2", "AHORA_SI_QUE_SI_n3", "AHORA_SI_QUE_SI_n4", "AHORA_SI_QUE_SI_n5", "AHORA_SI_QUE_SI_n6",
    "AHORA_SI_QUE_SI_GANADORES", "AHORA_SI_QUE_SI_MONTO", "AHORA_SI_QUE_SI_ACUMULADO",
    
    # RECARGADO (El sucesor moderno)
    "RECARGADO_n1", "RECARGADO_n2", "RECARGADO_n3", "RECARGADO_n4", "RECARGADO_n5", "RECARGADO_n6",
    "RECARGADO_6_ACIERTOS_GANADORES", "RECARGADO_6_ACIERTOS_MONTO", "RECARGADO_POZO_ACUMULADO",
    
    # REVANCHA
    "REVANCHA_n1", "REVANCHA_n2", "REVANCHA_n3", "REVANCHA_n4", "REVANCHA_n5", "REVANCHA_n6",
    "REVANCHA_GANADORES", "REVANCHA_MONTO", "REVANCHA_POZO_ACUMULADO",
    
    # DESQUITE
    "DESQUITE_n1", "DESQUITE_n2", "DESQUITE_n3", "DESQUITE_n4", "DESQUITE_n5", "DESQUITE_n6",
    "DESQUITE_GANADORES", "DESQUITE_MONTO", "DESQUITE_POZO_ACUMULADO"
]

def get_last_draw_id():
    if not os.path.exists(CSV_FILENAME):
        print("📂 Base de datos no encontrada. Creando nueva...")
        return SORTEO_INICIAL_DEFAULT - 1
    
    max_id = 0
    try:
        with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('sorteo') and row['sorteo'].isdigit():
                    draw_id = int(row['sorteo'])
                    if draw_id > max_id: max_id = draw_id
    except: pass
    return max_id

def append_to_csv(new_rows):
    if not new_rows: return

    existing_rows = []
    if os.path.exists(CSV_FILENAME):
        with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)

    # Detectar claves totales
    all_keys = set()
    if existing_rows: all_keys.update(existing_rows[0].keys())
    for row in new_rows: all_keys.update(row.keys())

    # Eliminar precio_carton
    if 'precio_carton' in all_keys: all_keys.remove('precio_carton')

    # --- CONSTRUCCIÓN INTELIGENTE DEL HEADER ---
    final_headers = []
    
    # 1. Bloque Fijo (Loto)
    for col in FIXED_START_ORDER:
        final_headers.append(col)
        if col in all_keys: all_keys.remove(col)
        
    # 2. Bloque Semiestático (Juegos conocidos en orden lógico)
    for col in PREFERRED_GAMES_ORDER:
        # Los agregamos SIEMPRE al header maestro para mantener la estructura visual ordenada,
        # incluso si están vacíos en algunos sorteos.
        final_headers.append(col)
        if col in all_keys: all_keys.remove(col)

    # 3. Bloque Dinámico (Jubilazos, Multiplicar y sorpresas)
    # Ordenamos lo que sobra alfabéticamente (JUBILAZO_1, JUBILAZO_2...)
    for col in sorted(list(all_keys)):
        final_headers.append(col)

    all_rows = existing_rows + new_rows
    print(f"💾 Guardando {len(new_rows)} nuevos (Total: {len(all_rows)})...")
    
    with open(CSV_FILENAME, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=final_headers)
        writer.writeheader()
        writer.writerows(all_rows)

async def run():
    print("--- 🏗️ INICIANDO CARGA MASIVA (ORDEN LÓGICO) ---")
    
    last_id = get_last_draw_id()
    current_target = last_id + 1
    print(f"🚀 Objetivo inicial: Sorteo #{current_target}")

    async with async_playwright() as p:
        print("Lanzando navegador...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        print("🔑 Obteniendo credenciales...")
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            await asyncio.sleep(5)
            
            token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
            if not token:
                c = await page.content()
                import re
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', c)
                token = m.group(1) if m else None

            if not token: raise Exception("Token no encontrado")
        except Exception as e:
            print(f"❌ Error Token: {e}")
            await browser.close()
            return

        print(f"✅ Token capturado. Iniciando descarga...")

        consecutive_errors = 0
        new_data_buffer = []
        
        while True:
            print(f"   -> Sorteo #{current_target}...", end=" ")
            try:
                await asyncio.sleep(random.uniform(0.5, 1.5)) 

                response = await page.request.post(API_URL, data={
                    "gameId": GAME_ID_LOTO, "drawId": current_target, "csrfToken": token
                }, headers={
                    "x-requested-with": "XMLHttpRequest",
                    "content-type": "application/json",
                    "origin": "https://www.polla.cl",
                    "referer": BASE_URL
                })

                if response.status == 200:
                    txt = await response.text()
                    try: json_data = json.loads(txt)
                    except: json_data = {}
                    
                    draw_num = json_data.get('drawNumber')
                    if not json_data or draw_num != current_target:
                         # Solo imprimimos warning si hay mismatch
                         # preview = txt[:50].replace('\n', ' ')
                         print(f"⚠️ Mismatch ({draw_num}).")
                         consecutive_errors += 1
                    else:
                        print("✅ OK")
                        flat_row = parse_loto_flat(json_data)
                        if 'precio_carton' in flat_row: del flat_row['precio_carton']
                        
                        new_data_buffer.append(flat_row)
                        consecutive_errors = 0 

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

            if consecutive_errors >= 5:
                print("\n🛑 Fin del scraping.")
                break
            
        if new_data_buffer: append_to_csv(new_data_buffer)
        await browser.close()
        print("🏁 Proceso finalizado.")

if __name__ == "__main__":
    asyncio.run(run())