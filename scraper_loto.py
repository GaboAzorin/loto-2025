import asyncio
import json
import os
import csv
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

# Sorteo inicial histórico si no hay CSV (El del 2016 que vimos)
SORTEO_INICIAL_DEFAULT = 3803 

def get_last_draw_id():
    """
    Lee el CSV actual y encuentra el número de sorteo más alto registrado.
    Si el archivo no existe, retorna el sorteo anterior al inicial por defecto.
    """
    if not os.path.exists(CSV_FILENAME):
        return SORTEO_INICIAL_DEFAULT - 1
    
    max_id = 0
    try:
        with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Nos aseguramos de leer la columna 'sorteo' y que sea un número
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
    Agrega filas al CSV manejando columnas dinámicas.
    Si aparecen columnas nuevas (ej: un juego nuevo), reescribe el encabezado.
    """
    if not new_rows:
        return

    existing_rows = []
    existing_headers = []
    
    # 1. Leer datos existentes para no perder nada
    if os.path.exists(CSV_FILENAME):
        with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                existing_headers = reader.fieldnames
            existing_rows = list(reader)

    # 2. Detectar todas las columnas necesarias (Viejas + Nuevas)
    all_keys = set(existing_headers)
    for row in new_rows:
        all_keys.update(row.keys())
    
    # 3. Ordenar encabezados: 
    # Mantenemos el orden original y agregamos las nuevas al final alfabéticamente
    final_headers = list(existing_headers)
    for k in sorted(list(all_keys)):
        if k not in final_headers:
            final_headers.append(k)
            
    # Reordenar cosmético: Forzamos columnas clave al principio para que sea legible
    priority_cols = ['sorteo', 'fecha', 'dia', 'mes', 'anio', 'dia_semana']
    for p in reversed(priority_cols):
        if p in final_headers:
            final_headers.remove(p)
            final_headers.insert(0, p)

    # 4. Unificar filas
    all_rows = existing_rows + new_rows

    # 5. Escribir todo de nuevo (Schema Evolution)
    print(f"💾 Guardando {len(all_rows)} registros totales en {CSV_FILENAME}...")
    with open(CSV_FILENAME, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=final_headers)
        writer.writeheader()
        writer.writerows(all_rows)

async def run():
    print("--- 🤖 INICIANDO ACTUALIZADOR AUTOMÁTICO DE LOTO ---")
    
    # 1. Determinar desde qué número empezar
    last_id = get_last_draw_id()
    current_target = last_id + 1
    print(f"📂 Último sorteo en BD: {last_id}")
    print(f"🚀 Objetivo inicial: Buscar sorteo #{current_target}")

    # Configuración de entorno (Local vs Github Actions)
    is_github_actions = os.getenv("GITHUB_ACTIONS") == "true"
    headless_mode = True if is_github_actions else False 

    async with async_playwright() as p:
        # Lanzamos navegador
        browser = await p.chromium.launch(headless=headless_mode)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        # 2. Obtener Token (Solo una vez al principio)
        print("🔑 Conectando a Polla.cl para obtener credenciales...")
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            await asyncio.sleep(2) # Espera técnica para carga de scripts
            
            # Intentamos extraer el token del input oculto
            token = await page.evaluate("""() => {
                let input = document.querySelector('input[name="csrfToken"]');
                return input ? input.value : null;
            }""")
            
            # Fallback: Si no está en el input, buscar en el HTML crudo
            if not token:
                content = await page.content()
                import re
                match = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
                token = match.group(1) if match else None

            if not token:
                raise Exception("No se pudo obtener el Token CSRF")
                
        except Exception as e:
            print(f"❌ Error fatal obteniendo token: {e}")
            await browser.close()
            return

        print(f"✅ Credenciales obtenidas. Iniciando barrido...")

        # 3. Ciclo de Scraping
        consecutive_errors = 0
        new_data_buffer = []
        
        while True:
            print(f"   -> Consultando sorteo #{current_target}...", end=" ")
            
            try:
                # Petición directa a la API usando la sesión del navegador
                response = await page.request.post(API_URL, data={
                    "gameId": GAME_ID_LOTO,
                    "drawId": current_target,
                    "csrfToken": token
                }, headers={
                    "x-requested-with": "XMLHttpRequest",
                    "content-type": "application/json"
                })

                if response.status == 200:
                    json_data = await response.json()
                    
                    # Validar si el sorteo es válido
                    # Polla a veces devuelve 200 OK con un JSON vacío o con datos del sorteo "actual" por defecto si no encuentra el ID
                    if not json_data or not json_data.get('id') or json_data.get('drawNumber') != current_target:
                         print("⚠️ Respuesta vacía o número incorrecto (Posible fin de historial).")
                         consecutive_errors += 1
                    else:
                        print("✅ ¡Encontrado!")
                        
                        # --- PARSEO EN MEMORIA ---
                        # Usamos tu parser híbrido pasando el diccionario directamente
                        flat_row = parse_loto_flat(json_data)
                        
                        new_data_buffer.append(flat_row)
                        consecutive_errors = 0 # Reset de errores al tener éxito

                        # Guardar cada 5 registros para seguridad
                        if len(new_data_buffer) >= 5:
                            append_to_csv(new_data_buffer)
                            new_data_buffer = []

                        current_target += 1
                        
                else:
                    print(f"❌ Error API {response.status}")
                    consecutive_errors += 1

            except Exception as e:
                print(f"❌ Error de red/script: {e}")
                consecutive_errors += 1

            # CONDICIÓN DE PARADA
            # Si fallamos 3 veces seguidas (ej: sorteo 5001, 5002, 5003 dan error), asumimos que no hay más datos.
            if consecutive_errors >= 3:
                print("\n🛑 Se detuvo el scraping (3 intentos fallidos consecutivos).")
                break
            
            # Pequeña pausa para ser amables con el servidor
            await asyncio.sleep(0.5)

        # Guardar cualquier dato remanente en el buffer
        if new_data_buffer:
            append_to_csv(new_data_buffer)

        await browser.close()
        print("🏁 Proceso finalizado con éxito.")

if __name__ == "__main__":
    asyncio.run(run())