import asyncio
import csv
import os
import json
from datetime import datetime
from playwright.async_api import async_playwright

# Importamos los parsers del archivo vecino
try:
    from loto_parsers_mix import parse_loto3, parse_loto4, parse_racha
except ImportError:
    # Parche por si se ejecuta desde otro contexto
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from loto_parsers_mix import parse_loto3, parse_loto4, parse_racha

# --- CONFIGURACIÓN DE RUTAS ROBUSTA (EL ARREGLO) ---
# 1. Dónde estoy: engine/scrapers/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 2. Dónde voy: Subir dos niveles (engine -> root) y entrar a data
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')

# --- CONFIGURACIÓN MAESTRA DEL MULTIVERSO ---
GAME_CONFIG = [
    {
        "name": "LOTO 3",
        "id": "2181",
        "csv": os.path.join(DATA_DIR, "LOTO3_MAESTRO.csv"), # <--- CORREGIDO
        "start_draw": 12991, 
        "parser": parse_loto3,
        "cols": [
            "sorteo", "fecha", "dia_semana", "hora", "momento", "combinacion",
            "n1", "n2", "n3",
            "EXACTA_GANADORES", "EXACTA_MONTO",
            "TRIO_PAR_GANADORES", "TRIO_PAR_MONTO",
            "TRIO_AZAR_GANADORES", "TRIO_AZAR_MONTO",
            "PAR_GANADORES", "PAR_MONTO",
            "TERMINACION_GANADORES", "TERMINACION_MONTO"
        ]
    },
    {
        "name": "LOTO 4",
        "id": "5270",
        "csv": os.path.join(DATA_DIR, "LOTO4_MAESTRO.csv"), # <--- CORREGIDO
        "start_draw": 4230, 
        "parser": parse_loto4,
        "cols": [
            "sorteo", "fecha", "dia_semana", "hora",
            "n1", "n2", "n3", "n4",
            "pos1", "pos2", "pos3", "pos4",
            "4_PUNTOS_GANADORES", "4_PUNTOS_MONTO",
            "3_PUNTOS_GANADORES", "3_PUNTOS_MONTO",
            "2_PUNTOS_GANADORES", "2_PUNTOS_MONTO"
        ]
    },
    {
        "name": "RACHA",
        "id": "5272", # ID de Polla confirmado para Racha
        "csv": os.path.join(DATA_DIR, "RACHA_MAESTRO.csv"), # <--- CORREGIDO
        "start_draw": 2963, 
        "parser": parse_racha,
        "cols": [
            "sorteo", "fecha", "dia_semana", "hora",
            # 10 números ordenados
            "n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "n9", "n10",
            # 10 posiciones físicas
            "pos1", "pos2", "pos3", "pos4", "pos5", "pos6", "pos7", "pos8", "pos9", "pos10",
            # Categorías Espejo
            "ACIERTO_10_GANADORES", "ACIERTO_10_MONTO",
            "ACIERTO_0_GANADORES", "ACIERTO_0_MONTO",
            "ACIERTO_9_GANADORES", "ACIERTO_9_MONTO",
            "ACIERTO_1_GANADORES", "ACIERTO_1_MONTO",
            "ACIERTO_8_GANADORES", "ACIERTO_8_MONTO",
            "ACIERTO_2_GANADORES", "ACIERTO_2_MONTO",
            "ACIERTO_7_GANADORES", "ACIERTO_7_MONTO",
            "ACIERTO_3_GANADORES", "ACIERTO_3_MONTO"
        ]
    }
]

BASE_URL = "https://www.polla.cl/es/view/resultados"
API_URL = "https://www.polla.cl/es/get/draw/results"

def get_start_id(config):
    """Determina desde qué sorteo empezar escaneando el CSV local"""
    filename = config['csv']
    default_start = config['start_draw']
    
    if not os.path.exists(filename):
        # Crear CSV si no existe
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=config['cols'])
            writer.writeheader()
        return default_start
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
            if not rows: return default_start
            
            # Buscar el ID más alto
            last_id = 0
            for r in rows:
                try:
                    curr = int(r['sorteo'])
                    if curr > last_id: last_id = curr
                except: continue
            
            if last_id > 0:
                print(f"   ↳ {config['name']}: Encontrado historial hasta #{last_id}. Continuando...")
                return last_id + 1
    except: pass
    
    return default_start

async def run():
    print("🌌 INICIANDO SISTEMA SCRAPER MULTIVERSO v1.0")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Usar user-agent real para evitar bloqueos
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()

        # 1. Obtener Token Global (Sirve para todos los juegos)
        try:
            print("🔑 Obteniendo credenciales de acceso...")
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            
            token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
            if not token:
                # Fallback regex
                content = await page.content()
                import re
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
                if m: token = m.group(1)
            
            if not token: raise Exception("Token no encontrado")
            print("✅ Credenciales aceptadas.")
            
        except Exception as e:
            print(f"❌ Error fatal de conexión: {e}")
            await browser.close()
            return

        # 2. Iterar por cada Universo (Juego)
        for game in GAME_CONFIG:
            print(f"\n🚀 SINTONIZANDO UNIVERSO: {game['name']} (ID {game['id']})")
            
            current_target = get_start_id(game)
            parser_func = game['parser']
            consecutive_errors = 0
            
            while consecutive_errors < 5:
                try:
                    # Request rápido
                    response = await page.request.post(API_URL, data={
                        "gameId": game['id'], 
                        "drawId": current_target, 
                        "csrfToken": token
                    }, headers={"x-requested-with": "XMLHttpRequest"})

                    if response.status == 200:
                        try:
                            json_data = await response.json()
                        except:
                            # JSON mal formado
                            print("   ⚠️ Respuesta corrupta.")
                            consecutive_errors += 1
                            continue

                        # Validaciones
                        if not json_data or not json_data.get('results'):
                            # Verificar fecha futura
                            ts = json_data.get('drawDate')
                            if ts:
                                dt = datetime.fromtimestamp(ts/1000)
                                if dt > datetime.now():
                                    print(f"   🛑 Límite temporal alcanzado ({dt}). Sorteo futuro.")
                                    break
                            
                            # Si no es futuro, es un hueco en la data
                            # print(f"   ⚠️ Sorteo #{current_target} vacío. Saltando.")
                            current_target += 1
                            consecutive_errors += 1
                            continue

                        # Parsear
                        flat_row = parser_func(json_data)
                        
                        # Guardar (Append mode)
                        with open(game['csv'], 'a', encoding='utf-8', newline='') as f:
                            writer = csv.DictWriter(f, fieldnames=game['cols'], extrasaction='ignore')
                            writer.writerow(flat_row)
                        
                        # Log visual compacto
                        log_extra = ""
                        if 'combinacion' in flat_row: log_extra = flat_row['combinacion']
                        elif 'n1' in flat_row: log_extra = f"{flat_row.get('n1')}-{flat_row.get('n2')}..."
                        
                        print(f"   💾 {game['name']} #{flat_row['sorteo']} OK [{log_extra}]")
                        
                        consecutive_errors = 0 # Reset racha de errores
                        current_target += 1
                        
                        # Pausa micrométrica para no saturar CPU local
                        # await asyncio.sleep(0.05) 

                    else:
                        print(f"   ❌ Error HTTP {response.status}")
                        consecutive_errors += 1
                        await asyncio.sleep(1)

                except Exception as e:
                    print(f"   🔥 Excepción: {e}")
                    consecutive_errors += 1
                    await asyncio.sleep(1)
            
            print(f"🏁 Sincronización de {game['name']} finalizada.")

        await browser.close()
        print("\n✅ TAREA COMPLETADA. Bases de datos actualizadas.")

if __name__ == "__main__":
    asyncio.run(run())