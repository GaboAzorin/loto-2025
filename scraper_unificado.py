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

PRIMOS_LOTO = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41}

# --- NUEVAS COLUMNAS SEPARADAS ---
HEADERS_JUGADAS = [
    "id", "fecha_generacion", "numeros", "jugado_realmente", "estado", 
    "sorteo_objetivo", "aciertos", "delta_suma", "proximidad_prom",
    # Columnas nuevas desglosadas para mejor visualización
    "paridad_info", "zonas_ok", "terminaciones_ok", 
    "rango_info", "consecutivos_info", "primos_info"
]

# Orden visual para mantener tu CSV maestro ordenado
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
    if not fecha_str: return datetime.max
    f = fecha_str.replace("T", " ").replace("Z", "").split(".")[0].strip()
    formatos = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y', '%d-%m-%Y %H:%M:%S', '%d-%m-%Y']
    for fmt in formatos:
        try:
            return datetime.strptime(f, fmt)
        except ValueError:
            continue
    return datetime.max

# --- UTILIDAD: CÁLCULO DE MÉTRICAS AVANZADAS ---
def calcular_metricas(pred_nums, sorteo_real):
    """Compara predicción vs realidad y devuelve valores planos para CSV."""
    real_nums = [int(sorteo_real[f'LOTO_n{i}']) for i in range(1,7)]
    real_nums.sort()
    
    # 1. Métricas Básicas
    aciertos = len(set(real_nums) & set(pred_nums))
    diff_total = sum(abs(r - p) for r, p in zip(real_nums, pred_nums))
    prox = round(diff_total / 6, 1)
    delta_suma = sum(pred_nums) - sum(real_nums)

    # 2. Análisis Estructural
    pred_pares = len([n for n in pred_nums if n % 2 == 0])
    real_pares = len([n for n in real_nums if n % 2 == 0])
    # Formato visual: "3P/3I vs 2P/4I"
    paridad_str = f"Pred:{pred_pares}P - Real:{real_pares}P"

    pred_decenas = [n // 10 for n in pred_nums]
    real_decenas = [n // 10 for n in real_nums]
    c_real = Counter(real_decenas)
    c_pred = Counter(pred_decenas)
    interseccion_zonas = sum((c_real & c_pred).values())

    pred_term = [n % 10 for n in pred_nums]
    real_term = [n % 10 for n in real_nums]
    aciertos_term = len(set(real_term) & set(pred_term))

    # 3. Nuevos Indicadores
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

    # Devolvemos diccionario plano listo para escribir en CSV
    return {
        "aciertos": aciertos,
        "proximidad_prom": prox,
        "delta_suma": delta_suma,
        "paridad_info": paridad_str,
        "zonas_ok": interseccion_zonas,
        "terminaciones_ok": aciertos_term,
        "rango_info": rango_str,
        "consecutivos_info": cons_str,
        "primos_info": primos_str
    }

# --- FUNCIONES DE SINCRONIZACIÓN Y AUDITORÍA ---

def sincronizar_nube_a_local():
    print("☁️ Sincronizando jugadas desde la nube...")
    try:
        response = requests.get(GOOGLE_SHEET_CSV_URL)
        response.raise_for_status()
        lineas = response.text.splitlines()
        filas_nube = list(csv.reader(lineas))
        
        if len(filas_nube) > 0 and "fecha" in filas_nube[0][0].lower(): filas_nube.pop(0)
        if not filas_nube: 
            print("   ✅ No hay datos nuevos en la nube.")
            return

        jugadas_existentes = set()
        
        # Verificar si el archivo existe y tiene las cabeceras correctas
        if os.path.exists(PREDICTIONS_CSV):
            with open(PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # Si las columnas no coinciden con las nuevas, forzamos re-creación (backup manual recomendado)
                if reader.fieldnames != HEADERS_JUGADAS:
                    print("   ⚠️ Estructura de columnas antigua detectada. Se actualizará el archivo.")
                    # Aquí podrías implementar migración, pero por simplicidad reescribiremos
                else:
                    for row in reader:
                        key = f"{row.get('fecha_generacion','')}_{row.get('numeros','')}"
                        jugadas_existentes.add(key)

        # Si no existe o se decidió reescribir, creamos con nuevos headers
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
                    
                    # Creamos fila vacía con estructura
                    row_data = {col: "" for col in HEADERS_JUGADAS}
                    row_data.update({
                        "id": id_gen,
                        "fecha_generacion": fecha_fmt,
                        "numeros": nums_json,
                        "jugado_realmente": jugado,
                        "estado": "PENDIENTE"
                    })
                    
                    writer.writerow(row_data)
                    jugadas_existentes.add(key)
                    nuevas += 1
                except: continue
        
        if nuevas > 0: print(f"   📥 Se descargaron {nuevas} jugadas nuevas.")
        else: print("   ✅ Base de datos local al día.")
    except Exception as e: print(f"❌ Error descargando nube: {e}")

def auditoria_retroactiva_inteligente():
    if not os.path.exists(PREDICTIONS_CSV) or not os.path.exists(CSV_FILENAME): return

    print("   🧠 Ejecutando auditoría cronológica inteligente...")
    historial = []
    with open(CSV_FILENAME, 'r', encoding='utf-8') as f:
        historial = list(csv.DictReader(f))
    # Ordenar historial por fecha para asegurar cronología
    historial.sort(key=lambda x: parsear_fecha(x['fecha']))

    jugadas = []
    with open(PREDICTIONS_CSV, 'r', encoding='utf-8') as f:
        jugadas = list(csv.DictReader(f))
    
    if not jugadas: return
    # Asegurar headers
    campos = list(jugadas[0].keys())
    # Si falta alguna columna nueva en el archivo viejo, la agregamos a la lista de campos
    for col in HEADERS_JUGADAS:
        if col not in campos: campos.append(col)

    cambios = False
    pendientes_ignoradas = 0

    for jugada in jugadas:
        if jugada['estado'] == 'PENDIENTE':
            fecha_jugada = parsear_fecha(jugada['fecha_generacion'])
            sorteo_objetivo = None
            
            # Buscamos el PRIMER sorteo cuya fecha sea estrictamente posterior a la jugada
            for sorteo in historial:
                if parsear_fecha(sorteo['fecha']) > fecha_jugada:
                    sorteo_objetivo = sorteo
                    break

            if sorteo_objetivo:
                # ¡ENCONTRAMOS SORTEO! PROCEDEMOS A CALCULAR
                pred_nums = json.loads(jugada['numeros'])
                pred_nums.sort()
                
                res = calcular_metricas(pred_nums, sorteo_objetivo)
                
                # Actualizar campos
                jugada['sorteo_objetivo'] = sorteo_objetivo['sorteo']
                jugada['estado'] = 'FINALIZADO'
                # Rellenar datos
                for k, v in res.items():
                    jugada[k] = v
                
                cambios = True
                print(f"      🎯 Jugada {jugada['id']} auditada vs Sorteo #{sorteo_objetivo['sorteo']}")
            else:
                # AUN NO HAY SORTEO (CASO CORRECTO PARA TU JUGADA DE AYER)
                pendientes_ignoradas += 1

    if pendientes_ignoradas > 0:
        print(f"      ⏳ {pendientes_ignoradas} jugadas se mantienen PENDIENTES (esperando sorteo futuro).")

    if cambios:
        with open(PREDICTIONS_CSV, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS_JUGADAS)
            writer.writeheader()
            # Al escribir, nos aseguramos de que cada fila tenga todos los campos
            for j in jugadas:
                row_completa = {col: j.get(col, "") for col in HEADERS_JUGADAS}
                writer.writerow(row_completa)
        print("      💾 Base de datos actualizada con nuevas auditorías.")
        
# --- SCRAPER ---
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
    auditoria_retroactiva_inteligente()

async def run():
    print("--- 🌀 INICIANDO SISTEMA INTEGRAL LOTO AI v4.0 ---")
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
                    
                    # --- VALIDACIÓN CRÍTICA DE FECHA FUTURA ---
                    draw_date_ms = json_data.get('drawDate')
                    
                    # 1. Chequear si es fecha futura
                    if draw_date_ms:
                        draw_date_dt = datetime.fromtimestamp(draw_date_ms / 1000)
                        if draw_date_dt > datetime.now():
                            print(f"🛑 DETENIDO: El sorteo #{current_target} es futuro ({draw_date_dt}).")
                            print("   ✅ Tu base de datos está actualizada al máximo.")
                            break

                    # 2. Chequear si el resultado está vacío (polla a veces publica el ID sin numeros)
                    # Si no hay resultados de la tómbola principal, es un sorteo no jugado o inválido
                    results_list = json_data.get('results', [])
                    if not results_list:
                         print(f"⚠️ El sorteo #{current_target} existe pero no tiene resultados aún.")
                         break

                    flat_row = parse_loto_flat(json_data)
                    
                    # 3. Doble chequeo de que parseo algo útil
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