import asyncio
import csv
import os
import json
import requests
import time
import re
import subprocess
from datetime import datetime
from playwright.async_api import async_playwright

# --- IMPORTACIÓN DE PARSERS ---
try:
    from loto_parser_v3 import parse_loto_rich
    from loto_parsers_mix import parse_loto3, parse_loto4, parse_racha
except ImportError:
    print("❌ Error: Faltan los archivos de parsers (loto_parser_v3.py o loto_parsers_mix.py)")
    exit()

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# URL de tu Google Sheet (CSV público)
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQnOXW1U2VkJdNw6DplTvNGb5R3Fc6yNPKuewnBqh9w9C01m9ht2N8dNi3C4oqvIyL6An-coGf0TjhR/pub?output=csv"
JUGADAS_CSV = os.path.join(DATA_DIR, "LOTO_JUGADAS.csv")

API_URL = "https://www.polla.cl/es/get/draw/results"
BASE_URL = "https://www.polla.cl/es/view/resultados"

# CONFIGURACIÓN MAESTRA DE TODOS LOS JUEGOS
GAME_CONFIG = [
    {
        "name": "LOTO",
        "id": "5271",
        "csv": os.path.join(DATA_DIR, "LOTO_HISTORIAL_MAESTRO.csv"),
        "parser": parse_loto_rich,
        "start_draw": 3803,
        "cols": [
            "sorteo", "fecha", "ventas_totales", "boletos_estimados",
            "LOTO_n1", "LOTO_n2", "LOTO_n3", "LOTO_n4", "LOTO_n5", "LOTO_n6", "LOTO_comodin",
            "LOTO_GANADORES", "LOTO_MONTO", "LOTO_POZO_REAL", "LOTO_POZO_ACUMULADO"
        ]
    },
    {
        "name": "LOTO 3",
        "id": "2181",
        "csv": os.path.join(DATA_DIR, "LOTO3_MAESTRO.csv"),
        "parser": parse_loto3,
        "start_draw": 12991,
        "cols": ["sorteo", "fecha", "dia_semana", "hora", "momento", "combinacion", "n1", "n2", "n3"]
    },
    {
        "name": "LOTO 4",
        "id": "5270",
        "csv": os.path.join(DATA_DIR, "LOTO4_MAESTRO.csv"),
        "parser": parse_loto4,
        "start_draw": 4230,
        "cols": ["sorteo", "fecha", "dia_semana", "hora", "n1", "n2", "n3", "n4", "pos1", "pos2", "pos3", "pos4"]
    },
    {
        "name": "RACHA",
        "id": "5272",
        "csv": os.path.join(DATA_DIR, "RACHA_MAESTRO.csv"),
        "parser": parse_racha,
        "start_draw": 2963,
        "cols": ["sorteo", "fecha", "dia_semana", "hora", "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9", "n10"]
    }
]

def sincronizar_jugadas():
    print("\n☁️  Sincronizando jugadas desde la nube (Google Sheets)...")
    try:
        response = requests.get(GOOGLE_SHEET_CSV_URL, timeout=10)
        if response.status_code != 200:
            print("   ⚠️ No se pudo conectar a Sheets.")
            return

        # 1. Cargar huellas digitales existentes (Fecha + Números)
        jugadas_existentes = set()
        
        if os.path.exists(JUGADAS_CSV):
            with open(JUGADAS_CSV, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, []) # Saltar header
                for row in reader:
                    # row[1] es fecha, row[2] son numeros "[1, 2, 3]"
                    if len(row) > 2:
                        # Limpieza agresiva para normalizar comparación
                        fecha_clean = row[1].strip()
                        nums_clean = row[2].replace(" ", "") # "[1,2,3]" sin espacios
                        key = f"{fecha_clean}|{nums_clean}"
                        jugadas_existentes.add(key)

        filas_nube = list(csv.reader(response.text.splitlines()))
        if not filas_nube: return

        # Detectar inicio de datos
        start_idx = 1 if len(filas_nube) > 0 and "fecha" in filas_nube[0][0].lower() else 0
        
        nuevas = 0
        modos_append = 'a' if os.path.exists(JUGADAS_CSV) else 'w'
        
        # Estructura COMPLETA para evitar romper columnas antiguas
        # (Aunque DictWriter solo escribe las que le damos, el append es seguro)
        HEADERS_NUEVOS = ["id", "fecha_generacion", "numeros", "jugado_realmente", "estado", "sorteo_objetivo", "juego"]

        with open(JUGADAS_CSV, modos_append, encoding='utf-8', newline='') as f:
            # Importante: Si el archivo ya existe y tiene más columnas (auditoría),
            # DictWriter simplemente escribirá las columnas que coincidan y dejará el resto vacío.
            # Esto es aceptable para el append.
            writer = csv.DictWriter(f, fieldnames=HEADERS_NUEVOS, extrasaction='ignore')
            if modos_append == 'w': writer.writeheader()

            for i in range(start_idx, len(filas_nube)):
                try:
                    fila = filas_nube[i]
                    if len(fila) < 3: continue
                    
                    # Formato Google Sheet: Fecha ISO, 1-2-3-4-5-6, SI
                    fecha_raw = fila[0].replace("T", " ").replace("Z", "").split(".")[0] # Normalizar fecha
                    nums_str = fila[1] # "2-13-17..."
                    jugado = fila[2]

                    # Convertir a formato lista JSON para comparar con lo local
                    try:
                        lista_nums = [int(n) for n in nums_str.split('-')]
                        nums_json = json.dumps(lista_nums) # "[2, 13, 17...]"
                    except: continue # Si falla el parseo de números, saltar

                    # Generar clave de comparación
                    key_check = f"{fecha_raw}|{nums_json.replace(' ', '')}"
                    
                    if key_check in jugadas_existentes: 
                        continue # ¡DUPLICADO DETECTADO! Saltar.
                    
                    # Si no existe, crear fila
                    row_data = {
                        "id": int(time.time()) + nuevas,
                        "fecha_generacion": fecha_raw,
                        "numeros": nums_json,
                        "jugado_realmente": jugado,
                        "estado": "PENDIENTE",
                        "juego": "LOTO", # Asumimos Loto por defecto desde la sheet
                        "sorteo_objetivo": "" # Se llenará luego con auditoría o manual
                    }
                    writer.writerow(row_data)
                    nuevas += 1
                    print(f"   ✨ Nueva jugada importada: {fecha_raw}")
                    
                except Exception as e: 
                    print(f"   ⚠️ Error en fila {i}: {e}")
                    continue
        
        if nuevas > 0: print(f"   📥 {nuevas} jugadas nuevas agregadas correctamente.")
        else: print("   ✅ Sincronización al día (0 duplicados).")

    except Exception as e:
        print(f"   ❌ Error sync nube: {e}")

def get_start_id(config):
    if not os.path.exists(config['csv']): return config['start_draw']
    max_id = 0
    try:
        with open(config['csv'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('sorteo') and row['sorteo'].isdigit():
                    sid = int(row['sorteo'])
                    if sid > max_id: max_id = sid
    except: pass
    return max_id + 1 if max_id > 0 else config['start_draw']

def subir_cambios_a_github():
    print("\n📦 SUBIENDO DATOS A GITHUB...")
    try:
        # Verificar si hay cambios
        status = subprocess.check_output(["git", "status", "--porcelain"], text=True)
        if not status:
            print("   ✅ No hay datos nuevos para subir.")
            return

        # Comandos git automáticos
        subprocess.run(["git", "add", "."], check=True)
        
        mensaje = f"🤖 Update local: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", mensaje], check=True)
        
        subprocess.run(["git", "push"], check=True)
        print("   🚀 ¡Listo! Los datos ya están en la web.")
        
    except Exception as e:
        print(f"   ⚠️ No se pudo subir a GitHub (¿Tienes internet?): {e}")

async def run_scraper():
    print("\n🕷️  INICIANDO SCRAPER MAESTRO (Manual/Local)...")
    sincronizar_jugadas()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) 
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()

        try:
            print("🔑 Obteniendo token de sesión Polla.cl...")
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            await asyncio.sleep(3) # Un segundo extra por seguridad
            
            # --- 2. RESTAURACIÓN DE LÓGICA DE EXTRACCIÓN ROBUSTA ---
            # Intento A: Vía DOM (Input hidden)
            token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
            
            # Intento B: Vía Fuerza Bruta (Regex en el HTML)
            if not token:
                print("   ⚠️ Token no encontrado en DOM. Intentando extracción profunda...")
                content = await page.content()
                # Regex que busca csrfToken: "valor" o csrfToken = "valor"
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
                if m: 
                    token = m.group(1)
                    print("   ✅ Token recuperado vía Regex.")
            
            if not token: raise Exception("No se encontró token CSRF por ningún método.")
            print("✅ Token validado.")
            
        except Exception as e:
            print(f"❌ Error fatal conectando: {e}")
            await browser.close()
            return

        for game in GAME_CONFIG:
            current_id = get_start_id(game)
            print(f"\n🚀 {game['name']} (ID {game['id']}) | Buscando desde #{current_id}")
            consecutive_errors = 0
            
            while consecutive_errors < 5:
                try:
                    response = await page.request.post(API_URL, data={
                        "gameId": game['id'], "drawId": current_id, "csrfToken": token
                    }, headers={"x-requested-with": "XMLHttpRequest"})

                    if response.status == 200:
                        try: json_data = await response.json()
                        except: 
                            print("   ⚠️ JSON inválido.")
                            consecutive_errors += 1; continue

                        if not json_data or not json_data.get('results'):
                            ts = json_data.get('drawDate')
                            if ts and datetime.fromtimestamp(ts/1000) > datetime.now():
                                print(f"   🛑 Sorteo #{current_id} es futuro. Deteniendo {game['name']}.")
                                break
                            current_id += 1
                            consecutive_errors += 1
                            continue

                        row = game['parser'](json_data)
                        
                        file_exists = os.path.exists(game['csv'])
                        fieldnames = list(game['cols'])
                        for k in row.keys():
                            if k not in fieldnames: fieldnames.append(k)

                        existing_headers = []
                        if file_exists:
                            with open(game['csv'], 'r', encoding='utf-8') as f:
                                existing_headers = csv.DictReader(f).fieldnames or []
                            final_headers = existing_headers if existing_headers else fieldnames
                            for k in row.keys(): 
                                if k not in final_headers: final_headers.append(k)
                        else:
                            final_headers = fieldnames

                        with open(game['csv'], 'a', encoding='utf-8', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=final_headers)
                            if not file_exists: writer.writeheader()
                            writer.writerow(row)

                        print(f"   💾 #{row['sorteo']} Guardado OK")
                        current_id += 1
                        consecutive_errors = 0
                    else:
                        print(f"   ❌ HTTP {response.status}")
                        consecutive_errors += 1
                        await asyncio.sleep(1)

                except Exception as e:
                    print(f"   🔥 Error en ciclo: {e}")
                    consecutive_errors += 1
                    await asyncio.sleep(1)

        await browser.close()
        # ==============================================================================
        # 🧠 NUEVO BLOQUE: RECONSTRUCCIÓN TEMPORAL (ESTRATEGIA 1)
        # ==============================================================================
        print("\n⏳ EJECUTANDO RECONSTRUCCIÓN TEMPORAL (Aprendizaje Secuencial)...")
        try:

            import reconstructor_temporal
            import importlib
            
            importlib.reload(reconstructor_temporal) 
            
            reconstructor_temporal.reconstruir_linea_tiempo()
            
        except ImportError:
            print("   ⚠️  ALERTA: No se encontró 'reconstructor_temporal.py'.")
            print("       El scraping terminó bien, pero no se actualizó la IA.")
        except Exception as e:
            print(f"   ❌ ERROR CRÍTICO EN RECONSTRUCTOR: {e}")
        # ==============================================================================

        # Finalmente, subimos todo (CSVs nuevos + JSON del genoma actualizado)
        subir_cambios_a_github()
        print("\n🏁 PROCESO FINALIZADO.")

if __name__ == "__main__":
    asyncio.run(run_scraper())