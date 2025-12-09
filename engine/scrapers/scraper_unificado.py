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
    from loto_parser_v3 import parse_loto_rich as parse_loto_flat
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

PRIMOS_LOTO = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41}

# --- NUEVAS COLUMNAS SEPARADAS ---
HEADERS_JUGADAS = [
    "id", "fecha_generacion", "numeros", "jugado_realmente", "estado", 
    "sorteo_objetivo", "aciertos", "delta_suma", "proximidad_prom",
    "paridad_info", "zonas_ok", "terminaciones_ok", 
    "rango_info", "consecutivos_info", "primos_info"
]

# Orden visual MAESTRO. Estas columnas se crearán SIEMPRE.
FIXED_ORDER = [
    "sorteo", "fecha", "ventas_totales", "boletos_estimados",
    "LOTO_n1", "LOTO_n2", "LOTO_n3", "LOTO_n4", "LOTO_n5", "LOTO_n6", "LOTO_comodin",
    "LOTO_GANADORES", "LOTO_MONTO", "LOTO_POZO_ACUMULADO", "LOTO_POZO_REAL",
    "RECARGADO_n1", "RECARGADO_n6", "RECARGADO_6_ACIERTOS_GANADORES", "RECARGADO_POZO_ACUMULADO",
    "REVANCHA_n1", "REVANCHA_n6", "REVANCHA_GANADORES", "REVANCHA_POZO_ACUMULADO",
    "DESQUITE_n1", "DESQUITE_n6", "DESQUITE_GANADORES", "DESQUITE_POZO_ACUMULADO",
    "AHORA_SI_QUE_SI_n1", "AHORA_SI_QUE_SI_n6", "AHORA_SI_QUE_SI_GANADORES", "AHORA_SI_QUE_SI_ACUMULADO"
]

# --- UTILIDADES ---
def parsear_fecha(fecha_str):
    if not fecha_str: return datetime.max
    f = fecha_str.replace("T", " ").replace("Z", "").split(".")[0].strip()
    formatos = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y', '%d-%m-%Y %H:%M:%S', '%d-%m-%Y']
    for fmt in formatos:
        try:
            return datetime.strptime(f, fmt)
        except ValueError:
            continue
    return datetime.max

def calcular_metricas(pred_nums, sorteo_real):
    real_nums = [int(sorteo_real[f'LOTO_n{i}']) for i in range(1,7)]
    real_nums.sort()
    aciertos = len(set(real_nums) & set(pred_nums))
    diff_total = sum(abs(r - p) for r, p in zip(real_nums, pred_nums))
    prox = round(diff_total / 6, 1)
    delta_suma = sum(pred_nums) - sum(real_nums)
    pred_pares = len([n for n in pred_nums if n % 2 == 0])
    real_pares = len([n for n in real_nums if n % 2 == 0])
    paridad_str = f"Pred:{pred_pares}P - Real:{real_pares}P"
    pred_decenas = [n // 10 for n in pred_nums]
    real_decenas = [n // 10 for n in real_nums]
    c_real = Counter(real_decenas)
    c_pred = Counter(pred_decenas)
    interseccion_zonas = sum((c_real & c_pred).values())
    pred_term = [n % 10 for n in pred_nums]
    real_term = [n % 10 for n in real_nums]
    aciertos_term = len(set(real_term) & set(pred_term))
    rango_pred = pred_nums[-1] - pred_nums[0]
    rango_real = real_nums[-1] - real_nums[0]
    rango_str = f"P:{rango_pred} / R:{rango_real}"
    def contar_consecutivos(lista):
        count = 0
        for i in range(len(lista)-1):
            if lista[i+1] == lista[i] + 1: count += 1
        return count
    cons_pred = contar_consecutivos(pred_nums)
    cons_real = contar_consecutivos(real_nums)
    cons_str = f"P:{cons_pred} / R:{cons_real}"
    primos_pred = len(set(pred_nums) & PRIMOS_LOTO)
    primos_real = len(set(real_nums) & PRIMOS_LOTO)
    primos_str = f"P:{primos_pred} / R:{primos_real}"
    return {
        "aciertos": aciertos, "proximidad_prom": prox, "delta_suma": delta_suma,
        "paridad_info": paridad_str, "zonas_ok": interseccion_zonas, "terminaciones_ok": aciertos_term,
        "rango_info": rango_str, "consecutivos_info": cons_str, "primos_info": primos_str
    }

def sincronizar_nube_a_local():
    print("☁️ Sincronizando jugadas desde la nube...")
    try:
        response = requests.get(GOOGLE_SHEET_CSV_URL, timeout=10)
        if response.status_code == 200:
            lineas = response.text.splitlines()
            filas_nube = list(csv.reader(lineas))
            if len(filas_nube) > 0 and "fecha" in filas_nube[0][0].lower(): filas_nube.pop(0)
            if not filas_nube: 
                print("   ✅ No hay datos nuevos en la nube.")
                return
            jugadas_existentes = set()
            if os.path.exists(PREDICTIONS_CSV):
                with open(PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
                    try:
                        reader = csv.DictReader(f)
                        if reader.fieldnames != HEADERS_JUGADAS:
                            print("   ⚠️ Estructura antigua detectada. Se actualizará.")
                        else:
                            for row in reader:
                                key = f"{row.get('fecha_generacion','')}_{row.get('numeros','')}"
                                jugadas_existentes.add(key)
                    except: pass
            if not os.path.exists(PREDICTIONS_CSV) or len(jugadas_existentes) == 0:
                with open(PREDICTIONS_CSV, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=HEADERS_JUGADAS)
                    writer.writeheader()
            nuevas = 0
            with open(PREDICTIONS_CSV, 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=HEADERS_JUGADAS)
                for fila in filas_nube:
                    try:
                        fecha_raw, nums_str, jugado = fila[0], fila[1], fila[2]
                        fecha_fmt = fecha_raw.replace("T", " ").replace("Z", "").split(".")[0]
                        nums_list = [int(n) for n in nums_str.split('-')]
                        nums_json = json.dumps(nums_list)
                        key = f"{fecha_fmt}_{nums_json}"
                        if key in jugadas_existentes: continue
                        id_gen = int(time.time()) + nuevas
                        row_data = {col: "" for col in HEADERS_JUGADAS}
                        row_data.update({
                            "id": id_gen, "fecha_generacion": fecha_fmt, "numeros": nums_json,
                            "jugado_realmente": jugado, "estado": "PENDIENTE"
                        })
                        writer.writerow(row_data)
                        jugadas_existentes.add(key)
                        nuevas += 1
                    except: continue
            if nuevas > 0: print(f"   📥 Se descargaron {nuevas} jugadas nuevas.")
            else: print("   ✅ Base de datos local al día.")
        else: print("   ⚠️ No se pudo conectar a Sheets. Usando archivo local.")
    except Exception as e: print(f"❌ Error descargando nube: {e}")

def auditoria_retroactiva_inteligente():
    if not os.path.exists(PREDICTIONS_CSV) or not os.path.exists(CSV_FILENAME): return
    historial = []
    with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
        historial = list(csv.DictReader(f))
    historial.sort(key=lambda x: parsear_fecha(x['fecha']))
    jugadas = []
    with open(PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
        jugadas = list(csv.DictReader(f))
    if not jugadas: return
    campos = list(jugadas[0].keys())
    for col in HEADERS_JUGADAS:
        if col not in campos: campos.append(col)
    cambios = False
    for jugada in jugadas:
        if jugada['estado'] == 'PENDIENTE':
            fecha_jugada = parsear_fecha(jugada['fecha_generacion'])
            sorteo_objetivo = None
            for sorteo in historial:
                if parsear_fecha(sorteo['fecha']) > fecha_jugada:
                    sorteo_objetivo = sorteo
                    break
            if sorteo_objetivo:
                pred_nums = json.loads(jugada['numeros'])
                pred_nums.sort()
                res = calcular_metricas(pred_nums, sorteo_objetivo)
                jugada['sorteo_objetivo'] = sorteo_objetivo['sorteo']
                jugada['estado'] = 'FINALIZADO'
                for k, v in res.items(): jugada[k] = v
                cambios = True
                print(f"      🎯 Jugada {jugada['id']} auditada vs Sorteo #{sorteo_objetivo['sorteo']}")
    if cambios:
        with open(PREDICTIONS_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS_JUGADAS)
            writer.writeheader()
            for j in jugadas:
                row_completa = {col: j.get(col, "") for col in HEADERS_JUGADAS}
                writer.writerow(row_completa)
        print("      💾 Base de datos actualizada con nuevas auditorías.")

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

# --- MODIFICACIÓN CLAVE: ESQUEMA AUTORITARIO ---
def save_row(new_rows):
    if not new_rows: return
    file_exists = os.path.exists(CSV_FILENAME)
    
    # 1. ¿Qué columnas trae la nueva data?
    data_keys = list(new_rows[0].keys())
    
    headers_to_use = []
    
    if file_exists:
        # Modo actualización (Auto-Healing)
        with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
            existing_headers = csv.DictReader(f).fieldnames or []
            
        missing_cols = [k for k in data_keys if k not in existing_headers]
        
        if missing_cols:
            print(f"✨ Detectada nueva columna {missing_cols}. Actualizando archivo maestro...")
            with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
                data = list(csv.DictReader(f))
            
            # Recalculamos headers usando FIXED_ORDER como base + extras
            all_known_keys = set(existing_headers) | set(data_keys)
            # Primero las fijas
            final_headers = [k for k in FIXED_ORDER if k in all_known_keys]
            # Luego las nuevas desconocidas
            for k in all_known_keys:
                if k not in final_headers: final_headers.append(k)
            # Y si falta alguna del FIXED_ORDER que no estaba en 'existing', la agregamos al final para no romper?
            # Mejor: Asegurar que todo FIXED_ORDER esté presente
            for k in FIXED_ORDER:
                 if k not in final_headers: final_headers.append(k)

            # Reescribir
            with open(CSV_FILENAME, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=final_headers)
                writer.writeheader()
                writer.writerows(data)
            
            headers_to_use = final_headers
            file_exists = True 
        else:
            headers_to_use = existing_headers
    else:
        # MODO CREACIÓN (El que se ejecutará ahora)
        # Forzamos que FIXED_ORDER sea la base, aunque falten datos en la primera fila
        headers_to_use = list(FIXED_ORDER)
        
        # Agregamos extras que traiga el dato (ej: JUBILAZO_1_pos1)
        new_cols = [k for k in data_keys if k not in headers_to_use]
        headers_to_use.extend(new_cols)

    with open(CSV_FILENAME, 'a', encoding='utf-8', newline='') as f:
        # extrasaction='ignore' solo ignora si sobran datos, pero aquí ya los incluimos.
        # Lo importante es que DictWriter escribirá '' (vacío) si falta el dato en el diccionario (ej: 3803 sin pozo real)
        writer = csv.DictWriter(f, fieldnames=headers_to_use, extrasaction='ignore')
        if not file_exists: writer.writeheader()
        writer.writerows(new_rows)
            
    print(f"💾 Guardado sorteo #{new_rows[0]['sorteo']} ({new_rows[0]['fecha']})")
    auditoria_retroactiva_inteligente()

async def run():
    print("--- 🌀 INICIANDO SISTEMA INTEGRAL LOTO AI v4.5 (ESQUEMA AUTORITARIO) ---")
    sincronizar_nube_a_local()
    auditoria_retroactiva_inteligente()
    
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
                response = await page.request.post(API_URL, data={"gameId": GAME_ID_LOTO, "drawId": current_target, "csrfToken": token}, headers={"x-requested-with": "XMLHttpRequest"})
                
                if response.status == 200:
                    try: json_data = await response.json()
                    except: json_data = {}
                    if not json_data: break
                    
                    draw_date_ms = json_data.get('drawDate')
                    if draw_date_ms:
                        draw_date_dt = datetime.fromtimestamp(draw_date_ms / 1000)
                        if draw_date_dt > datetime.now():
                            print(f"🛑 DETENIDO: El sorteo #{current_target} es futuro ({draw_date_dt}).")
                            break

                    results_list = json_data.get('results', [])
                    if not results_list:
                         print(f"⚠️ El sorteo #{current_target} existe pero no tiene resultados aún.")
                         break

                    flat_row = parse_loto_flat(json_data)
                    if not flat_row.get('LOTO_n1'):
                         print(f"⚠️ Datos incompletos en sorteo #{current_target}. Saltando.")
                         break

                    save_row([flat_row])
                    current_target += 1
                else: break
            except Exception as e:
                print(f"❌ Error técnico: {e}")
                break
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())