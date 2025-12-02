import asyncio
import json
import os
import csv
import time
import requests
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
PREDICTIONS_CSV = "LOTO_JUGADAS.csv"

# ⚠️ PEGA AQUÍ EL ENLACE DE "PUBLICAR EN LA WEB" (FORMATO CSV) DE TU GOOGLE SHEET ⚠️
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQnOXW1U2VkJdNw6DplTvNGb5R3Fc6yNPKuewnBqh9w9C01m9ht2N8dNi3C4oqvIyL6An-coGf0TjhR/pub?output=csv"

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

def sincronizar_nube_a_local():
    """Descarga jugadas nuevas desde Google Sheets y las guarda localmente."""
    if "PEGAR_AQUI" in GOOGLE_SHEET_CSV_URL:
        print("⚠️ SALTO: No has configurado la URL de Google Sheets en el script.")
        return

    print("☁️ Sincronizando jugadas desde la nube...")
    try:
        response = requests.get(GOOGLE_SHEET_CSV_URL)
        response.raise_for_status()
        
        # Leemos los datos de la nube
        lineas = response.text.splitlines()
        filas_nube = list(csv.reader(lineas))
        
        # Saltamos encabezado si existe
        if len(filas_nube) > 0 and "fecha" in filas_nube[0][0].lower():
            filas_nube.pop(0)

        if not filas_nube:
            print("   ✅ No hay datos nuevos en la nube.")
            return

        # Cargamos jugadas locales para no repetir
        jugadas_existentes = set()
        if os.path.exists(PREDICTIONS_CSV):
            with open(PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Usamos fecha+numeros como ID único
                    key = f"{row.get('fecha_generacion','')}_{row.get('numeros','')}"
                    jugadas_existentes.add(key)
        else:
            # Crear archivo si no existe
            with open(PREDICTIONS_CSV, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["id", "fecha_generacion", "numeros", "jugado_realmente", "estado", "sorteo_objetivo", "aciertos", "delta_suma", "proximidad_prom"])

        nuevas = 0
        with open(PREDICTIONS_CSV, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for fila in filas_nube:
                try:
                    # Google manda: [fecha_iso, "1-2-3...", "SI/NO"]
                    fecha_raw, nums_str, jugado = fila[0], fila[1], fila[2]
                    
                    # Limpieza básica de fecha
                    fecha_fmt = fecha_raw.replace("T", " ").replace("Z", "").split(".")[0]
                    
                    # Convertir números "1-2-3" a array JSON "[1, 2, 3]"
                    nums_list = [int(n) for n in nums_str.split('-')]
                    nums_json = json.dumps(nums_list)
                    
                    key = f"{fecha_fmt}_{nums_json}"
                    if key in jugadas_existentes: continue
                    
                    # Guardar nueva jugada
                    id_gen = int(time.time()) + nuevas # ID simple
                    writer.writerow([id_gen, fecha_fmt, nums_json, jugado, "PENDIENTE", "", "", "", ""])
                    jugadas_existentes.add(key)
                    nuevas += 1
                except: continue
        
        if nuevas > 0: print(f"   📥 Se descargaron {nuevas} jugadas nuevas.")
        else: print("   ✅ Base de datos local al día.")

    except Exception as e:
        print(f"❌ Error descargando nube: {e}")

def auditar_predicciones(sorteo_real):
    """Compara jugadas PENDIENTES contra el sorteo recién bajado."""
    if not os.path.exists(PREDICTIONS_CSV): return

    print(f"   🕵️ Auditando predicciones contra Sorteo #{sorteo_real['sorteo']}...")
    filas_todas = []
    cambios = False
    
    real_nums = [int(sorteo_real[f'LOTO_n{i}']) for i in range(1,7)]
    real_nums.sort()
    fecha_sorteo = datetime.strptime(sorteo_real['fecha'], '%Y-%m-%d %H:%M:%S')

    with open(PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        campos = reader.fieldnames
        for row in reader:
            if row['estado'] == 'PENDIENTE':
                try:
                    fecha_gen = datetime.strptime(row['fecha_generacion'], '%Y-%m-%d %H:%M:%S')
                except:
                    # Si falla el parseo de fecha, asumimos que es vieja y la auditamos igual
                    fecha_gen = datetime.min

                # Solo auditamos si la jugada fue ANTES del sorteo
                if fecha_gen < fecha_sorteo:
                    pred_nums = json.loads(row['numeros'])
                    pred_nums.sort()
                    
                    # 1. Aciertos
                    aciertos = len(set(real_nums) & set(pred_nums))
                    
                    # 2. Proximidad (Diferencia promedio por bola)
                    diff_total = sum(abs(r - p) for r, p in zip(real_nums, pred_nums))
                    prox = round(diff_total / 6, 1)

                    row['sorteo_objetivo'] = sorteo_real['sorteo']
                    row['aciertos'] = aciertos
                    row['delta_suma'] = sum(pred_nums) - sum(real_nums)
                    row['proximidad_prom'] = prox
                    row['estado'] = 'FINALIZADO'
                    
                    cambios = True
                    print(f"      🎯 Jugada {row['id']}: {aciertos} aciertos (Desv: {prox})")
            
            filas_todas.append(row)

    if cambios:
        with open(PREDICTIONS_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(filas_todas)
        print("      💾 Auditoría guardada en LOTO_JUGADAS.csv")

def get_last_draw_id():
    if not os.path.exists(CSV_FILENAME): return SORTEO_INICIAL_DEFAULT - 1
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
            filtered_row = {k: v for k, v in row.items() if k in headers_to_use}
            writer.writerow(filtered_row)
            
    print(f"💾 Guardado sorteo #{new_rows[0]['sorteo']} ({new_rows[0]['fecha']})")
    # --- TRIGGER DE AUDITORÍA ---
    auditar_predicciones(new_rows[0])

async def run():
    print("--- 🌀 INICIANDO SISTEMA INTEGRAL LOTO AI ---")
    
    # 1. Sincronizar Nube
    sincronizar_nube_a_local()
    
    # 2. Scraping Polla
    last_id = get_last_draw_id()
    current_target = last_id + 1
    print(f"🔎 Buscando sorteo Polla #{current_target}...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

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
            print("❌ Error de conexión con Polla.")
            await browser.close()
            return
        
        while True:
            try:
                await asyncio.sleep(0.5)
                response = await page.request.post(API_URL, data={
                    "gameId": GAME_ID_LOTO, "drawId": current_target, "csrfToken": token
                }, headers={"x-requested-with": "XMLHttpRequest"})

                if response.status == 200:
                    try: json_data = await response.json()
                    except: json_data = {}

                    if not json_data: break
                    
                    draw_date_ms = json_data.get('drawDate')
                    if draw_date_ms:
                        if (draw_date_ms / 1000) > time.time():
                            print(f"✅ Sistema actualizado. Próximo sorteo pendiente: #{current_target}")
                            break
                    
                    flat_row = parse_loto_flat(json_data)
                    save_row([flat_row])
                    current_target += 1
                else:
                    break
            except Exception as e:
                print(f"❌ Error técnico: {e}")
                break
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())