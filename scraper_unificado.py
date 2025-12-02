import asyncio
import json
import os
import csv
import time
import requests
from datetime import datetime
from collections import Counter
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

# ⚠️ TU ENLACE DE GOOGLE SHEETS ⚠️
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

# --- UTILIDAD: PARSEO DE FECHAS ROBUSTO ---
def parsear_fecha(fecha_str):
    """Intenta interpretar la fecha en varios formatos (ISO o DD/MM/YYYY)."""
    if not fecha_str: return datetime.max
    # Limpieza previa
    f = fecha_str.replace("T", " ").replace("Z", "").split(".")[0].strip()
    formatos = [
        '%Y-%m-%d %H:%M:%S', # Formato estándar CSV
        '%Y-%m-%d',          # Formato fecha simple
        '%d/%m/%Y %H:%M:%S', # Formato Google Sheets típico
        '%d/%m/%Y',          # Formato Google Sheets corto
        '%d-%m-%Y %H:%M:%S',
        '%d-%m-%Y'
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(f, fmt)
        except ValueError:
            continue
    return datetime.max # Si falla todo, devolvemos futuro lejano para no auditar por error

# --- UTILIDAD: CÁLCULO DE MÉTRICAS ---
def calcular_metricas(pred_nums, sorteo_real):
    """Compara números predichos vs sorteo real y devuelve diccionario de resultados."""
    real_nums = [int(sorteo_real[f'LOTO_n{i}']) for i in range(1,7)]
    real_nums.sort()
    
    # Métricas del Real
    real_pares = len([n for n in real_nums if n % 2 == 0])
    real_terminaciones = [n % 10 for n in real_nums]
    real_decenas = [n // 10 for n in real_nums]

    # Cálculos
    aciertos = len(set(real_nums) & set(pred_nums))
    diff_total = sum(abs(r - p) for r, p in zip(real_nums, pred_nums))
    prox = round(diff_total / 6, 1)
    delta_suma = sum(pred_nums) - sum(real_nums)

    # Estructura Avanzada
    pred_pares = len([n for n in pred_nums if n % 2 == 0])
    match_paridad = (pred_pares == real_pares)
    
    pred_decenas = [n // 10 for n in pred_nums]
    c_real = Counter(real_decenas)
    c_pred = Counter(pred_decenas)
    interseccion_zonas = sum((c_real & c_pred).values())

    pred_term = [n % 10 for n in pred_nums]
    aciertos_term = len(set(real_terminaciones) & set(pred_term))

    analisis = {
        "estructura_paridad": "OK" if match_paridad else "FALLO",
        "pares_predichos": pred_pares,
        "pares_reales": real_pares,
        "aciertos_zonas": interseccion_zonas, 
        "aciertos_terminaciones": aciertos_term
    }

    return {
        "aciertos": aciertos,
        "proximidad": prox,
        "delta_suma": delta_suma,
        "analisis_json": json.dumps(analisis),
        "analisis_obj": analisis # Para imprimir en consola
    }

# --- FUNCIONES PRINCIPALES ---

def sincronizar_nube_a_local():
    """Descarga jugadas nuevas desde Google Sheets y las guarda localmente."""
    print("☁️ Sincronizando jugadas desde la nube...")
    try:
        response = requests.get(GOOGLE_SHEET_CSV_URL)
        response.raise_for_status()
        
        lineas = response.text.splitlines()
        filas_nube = list(csv.reader(lineas))
        
        if len(filas_nube) > 0 and "fecha" in filas_nube[0][0].lower():
            filas_nube.pop(0)

        if not filas_nube:
            print("   ✅ No hay datos nuevos en la nube.")
            return

        jugadas_existentes = set()
        if os.path.exists(PREDICTIONS_CSV):
            with open(PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = f"{row.get('fecha_generacion','')}_{row.get('numeros','')}"
                    jugadas_existentes.add(key)
        else:
            with open(PREDICTIONS_CSV, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["id", "fecha_generacion", "numeros", "jugado_realmente", "estado", "sorteo_objetivo", "aciertos", "delta_suma", "proximidad_prom", "analisis_extra"])

        nuevas = 0
        with open(PREDICTIONS_CSV, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for fila in filas_nube:
                try:
                    fecha_raw, nums_str, jugado = fila[0], fila[1], fila[2]
                    # Normalizamos la fecha visualmente para el CSV, pero mantenemos formato origen
                    fecha_fmt = fecha_raw.replace("T", " ").replace("Z", "").split(".")[0]
                    
                    nums_list = [int(n) for n in nums_str.split('-')]
                    nums_json = json.dumps(nums_list)
                    
                    key = f"{fecha_fmt}_{nums_json}"
                    if key in jugadas_existentes: continue
                    
                    id_gen = int(time.time()) + nuevas
                    writer.writerow([id_gen, fecha_fmt, nums_json, jugado, "PENDIENTE", "", "", "", "", ""])
                    jugadas_existentes.add(key)
                    nuevas += 1
                except: continue
        
        if nuevas > 0: print(f"   📥 Se descargaron {nuevas} jugadas nuevas.")
        else: print("   ✅ Base de datos local al día.")

    except Exception as e:
        print(f"❌ Error descargando nube: {e}")

def auditoria_retroactiva_inteligente():
    """
    Recorre TODAS las jugadas PENDIENTES y busca en TODO el historial 
    el sorteo exacto que le corresponde (el inmediatamente posterior a la jugada).
    """
    if not os.path.exists(PREDICTIONS_CSV) or not os.path.exists(CSV_FILENAME): return

    print("   🧠 Ejecutando auditoría cronológica inteligente...")
    
    # 1. Cargar Historial Completo y ordenarlo por fecha
    historial = []
    with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
        historial = list(csv.DictReader(f))
    
    # Aseguramos orden ascendente (antiguo -> nuevo) para buscar el "siguiente" sorteo
    historial.sort(key=lambda x: int(x['sorteo']))

    # 2. Cargar Jugadas y Procesar
    jugadas = []
    with open(PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
        jugadas = list(csv.DictReader(f))
        
    campos = jugadas[0].keys() if jugadas else []
    if 'analisis_extra' not in campos and jugadas:
        # Corrección si falta columna
        campos = list(jugadas[0].keys()) + ['analisis_extra']

    cambios = False
    
    for jugada in jugadas:
        if jugada['estado'] == 'PENDIENTE':
            fecha_jugada = parsear_fecha(jugada['fecha_generacion'])
            
            # Buscamos el sorteo correspondiente (Timeline Matching)
            sorteo_objetivo = None
            
            for sorteo in historial:
                fecha_sorteo = parsear_fecha(sorteo['fecha'])
                
                # REGLA DE ORO: El sorteo debe ser POSTERIOR a la jugada
                if fecha_sorteo > fecha_jugada:
                    sorteo_objetivo = sorteo
                    break # Encontramos el primero siguiente, paramos de buscar.

            if sorteo_objetivo:
                # Si encontramos un sorteo futuro válido, calculamos métricas
                pred_nums = json.loads(jugada['numeros'])
                pred_nums.sort()
                
                res = calcular_metricas(pred_nums, sorteo_objetivo)
                
                # Actualizamos la jugada
                jugada['sorteo_objetivo'] = sorteo_objetivo['sorteo']
                jugada['aciertos'] = res['aciertos']
                jugada['delta_suma'] = res['delta_suma']
                jugada['proximidad_prom'] = res['proximidad']
                jugada['analisis_extra'] = res['analisis_json']
                jugada['estado'] = 'FINALIZADO'
                
                cambios = True
                print(f"      🎯 Jugada {jugada['id']} ({jugada['fecha_generacion']}) -> Sorteo #{sorteo_objetivo['sorteo']}: {res['aciertos']} aciertos")
            else:
                # Si no encontramos sorteo (ej: jugada de hoy vs historial hasta ayer)
                # Se mantiene PENDIENTE silenciosamente
                pass

    if cambios:
        with open(PREDICTIONS_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(jugadas)
        print("      💾 Auditoría cronológica guardada correctamente.")

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
    # Al guardar uno nuevo, volvemos a correr la auditoría inteligente
    auditoria_retroactiva_inteligente()

async def run():
    print("--- 🌀 INICIANDO SISTEMA INTEGRAL LOTO AI ---")
    
    # 1. Sincronizar Nube
    sincronizar_nube_a_local()
    
    # 2. Auditoría Inteligente (Revisión Histórica Correcta)
    auditoria_retroactiva_inteligente()
    
    # 3. Scraping Polla
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