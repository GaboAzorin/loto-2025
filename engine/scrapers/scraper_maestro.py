import asyncio
import csv
import os
import json
import requests
import time
from datetime import datetime
from playwright.async_api import async_playwright

# --- IMPORTACIÓN DE PARSERS ---
# Asegúrate de tener loto_parser_v3.py y loto_parsers_mix.py en la misma carpeta
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

# URL de tu Google Sheet (CSV público) para sincronizar jugadas
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
        "cols": [ # Columnas base del Loto v3
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

# --- 1. MÓDULO DE SINCRONIZACIÓN DE JUGADAS (DEL SCRAPER UNIFICADO) ---
def sincronizar_jugadas():
    print("\n☁️  Sincronizando jugadas desde la nube (Google Sheets)...")
    try:
        response = requests.get(GOOGLE_SHEET_CSV_URL, timeout=10)
        if response.status_code != 200:
            print("   ⚠️ No se pudo conectar a Sheets.")
            return

        # Leemos lo que ya tenemos localmente
        jugadas_locales = set()
        headers_local = []
        if os.path.exists(JUGADAS_CSV):
            with open(JUGADAS_CSV, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers_local = next(reader, [])
                for row in reader:
                    if len(row) > 1: jugadas_locales.add(f"{row[0]}_{row[1]}") # Usamos fecha+numeros como ID simple

        # Procesamos la nube
        filas_nube = list(csv.reader(response.text.splitlines()))
        if not filas_nube: return

        # Detectar headers nube (a veces la primera fila es header)
        start_idx = 1 if "fecha" in filas_nube[0][0].lower() else 0
        
        nuevas = 0
        modos_append = 'a' if os.path.exists(JUGADAS_CSV) else 'w'
        
        # Estructura objetivo
        HEADERS_JUGADAS = ["id", "fecha_generacion", "numeros", "jugado_realmente", "estado", "sorteo_objetivo", "juego"]

        with open(JUGADAS_CSV, modos_append, encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS_JUGADAS)
            if modos_append == 'w': writer.writeheader()

            for i in range(start_idx, len(filas_nube)):
                try:
                    # Asumimos formato del Google Script: Fecha, Numeros, Jugado
                    fila = filas_nube[i]
                    if len(fila) < 3: continue
                    
                    fecha_raw, nums_str, jugado = fila[0], fila[1], fila[2]
                    key = f"{fecha_raw}_{nums_str}"
                    
                    if key in jugadas_locales: continue # Ya existe
                    
                    # Crear nueva entrada
                    row_data = {
                        "id": int(time.time()) + nuevas,
                        "fecha_generacion": fecha_raw.replace("T", " ").split(".")[0],
                        "numeros": json.dumps([int(n) for n in nums_str.split('-')]),
                        "jugado_realmente": jugado,
                        "estado": "PENDIENTE",
                        "juego": "LOTO" # Por defecto Loto si viene del script antiguo
                    }
                    writer.writerow(row_data)
                    nuevas += 1
                except: continue
        
        if nuevas > 0: print(f"   📥 {nuevas} jugadas nuevas descargadas.")
        else: print("   ✅ Jugadas locales al día.")

    except Exception as e:
        print(f"   ❌ Error sync nube: {e}")

# --- 2. MÓDULO DE SCRAPING DE RESULTADOS (DEL SCRAPER MULTIVERSO) ---
def get_start_id(config):
    """Busca el último ID en el CSV local para saber desde dónde seguir."""
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

async def run_scraper():
    print("\n🕷️  INICIANDO SCRAPER MAESTRO (Manual/Local)...")
    
    # 1. Sincronizar Jugadas (Priority 1)
    sincronizar_jugadas()

    async with async_playwright() as p:
        # Lanzamos navegador (Headless = True para que no moleste, False para ver qué hace)
        browser = await p.chromium.launch(headless=True) 
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()

        # 2. Obtener Token CSRF (Se reutiliza para todos)
        try:
            print("🔑 Obteniendo token de sesión Polla.cl...")
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
            if not token: raise Exception("No se encontró token CSRF")
            print("✅ Token obtenido.")
        except Exception as e:
            print(f"❌ Error fatal conectando: {e}")
            await browser.close()
            return

        # 3. Iterar por cada juego
        for game in GAME_CONFIG:
            current_id = get_start_id(game)
            print(f"\n🚀 {game['name']} (ID {game['id']}) | Buscando desde #{current_id}")
            
            consecutive_errors = 0
            
            while consecutive_errors < 5:
                try:
                    # Llamada API
                    response = await page.request.post(API_URL, data={
                        "gameId": game['id'], "drawId": current_id, "csrfToken": token
                    }, headers={"x-requested-with": "XMLHttpRequest"})

                    if response.status == 200:
                        try: json_data = await response.json()
                        except: 
                            print("   ⚠️ JSON inválido.")
                            consecutive_errors += 1; continue

                        # Validar contenido
                        if not json_data or not json_data.get('results'):
                            # Verificar si es futuro
                            ts = json_data.get('drawDate')
                            if ts and datetime.fromtimestamp(ts/1000) > datetime.now():
                                print(f"   🛑 Sorteo #{current_id} es futuro. Deteniendo {game['name']}.")
                                break
                            
                            # Es un hueco o error
                            # print(f"   ⚠️ Sorteo #{current_id} vacío. Saltando.")
                            current_id += 1
                            consecutive_errors += 1
                            continue

                        # Parsear
                        row = game['parser'](json_data)
                        
                        # Guardar (Modo Append inteligente)
                        file_exists = os.path.exists(game['csv'])
                        
                        # Manejo de columnas dinámicas (ej: Loto tiene muchas premios variables)
                        # Leemos keys actuales + las nuevas
                        fieldnames = list(game['cols'])
                        for k in row.keys():
                            if k not in fieldnames: fieldnames.append(k)

                        # Si el archivo existe y tiene columnas viejas, hay que tener cuidado
                        # Aquí simplificamos: append con extrasaction='ignore' si usáramos DictWriter estricto
                        # pero usaremos un truco: leer headers existentes si existen
                        
                        existing_headers = []
                        if file_exists:
                            with open(game['csv'], 'r', encoding='utf-8') as f:
                                existing_headers = csv.DictReader(f).fieldnames or []
                            # Si hay columnas nuevas, idealmente reescribiríamos el header, 
                            # pero para scraping diario, asumimos consistencia.
                            # Si row trae algo nuevo, lo agregamos a los headers de escritura
                            final_headers = existing_headers if existing_headers else fieldnames
                            for k in row.keys(): 
                                if k not in final_headers: final_headers.append(k)
                        else:
                            final_headers = fieldnames

                        with open(game['csv'], 'a', encoding='utf-8', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=final_headers)
                            if not file_exists: writer.writeheader()
                            # Si cambiaron los headers en medio del append, DictWriter ignorará los nuevos si no están en fieldnames iniciales
                            # Solución robusta manual para este caso es compleja, asumimos standard.
                            writer.writerow(row)

                        print(f"   💾 #{row['sorteo']} Guardado OK")
                        current_id += 1
                        consecutive_errors = 0
                        # await asyncio.sleep(0.1) # Pequeña pausa opcional

                    else:
                        print(f"   ❌ HTTP {response.status}")
                        consecutive_errors += 1
                        await asyncio.sleep(1)

                except Exception as e:
                    print(f"   🔥 Error en ciclo: {e}")
                    consecutive_errors += 1
                    await asyncio.sleep(1)

        await browser.close()
        print("\n🏁 PROCESO FINALIZADO.")

if __name__ == "__main__":
    asyncio.run(run_scraper())