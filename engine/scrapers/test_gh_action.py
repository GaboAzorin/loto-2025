import os
import requests
import json
import re
import time

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("SCRAPERAPI_KEY", "").strip() 
GAME_ID = "5271" # Loto
DRAW_ID = "5360" # Sorteo Objetivo
OUTPUT_FILE = "resultado_nube_final.json"

BASE_URL = "https://www.polla.cl/es/view/resultados"
API_INTERNAL = "https://www.polla.cl/es/get/draw/results"
PROXY_URL = "http://api.scrape.do"

def run_tank_scraper():
    print(f"☁️ INICIANDO SCRAPER ROBUSTO (Con Reintentos)")
    
    if len(TOKEN) < 10:
        print("❌ Error: Token vacío.")
        return

    session = requests.Session()
    token_polla = None
    cookies_home = None

    # --- FASE 1: OBTENER HOME (Con 3 Intentos) ---
    print("1️⃣ Solicitando Home (Buscando Token)...")
    
    for intento in range(1, 4):
        print(f"   🔄 Intento #{intento}...")
        
        params_home = {
            'token': TOKEN,
            'url': BASE_URL,
            'render': 'true',
            'timeout': '15000' # Le pedimos a Scrape.do que espere más
        }

        try:
            resp = session.get(PROXY_URL, params=params_home, timeout=120)
            
            if resp.status_code == 200:
                # Buscar Token
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', resp.text)
                if m:
                    token_polla = m.group(1)
                    cookies_home = resp.cookies
                    print(f"   ✅ ¡Éxito! Token: {token_polla[:15]}...")
                    break # Salimos del bucle si funcionó
                else:
                    print("   ⚠️ Página cargó pero no tiene token (¿Bloqueo?). Reintentando...")
            else:
                print(f"   ⚠️ Falló con Status {resp.status_code}. Reintentando...")
                time.sleep(2) # Esperar 2 segundos antes de reintentar

        except Exception as e:
            print(f"   ⚠️ Error de conexión: {e}")
            time.sleep(2)

    # Si después de 3 intentos no hay token, abortamos
    if not token_polla:
        print("❌ FATAL: No se pudo obtener el token tras 3 intentos.")
        return

    # --- FASE 2: CONSULTAR API (POST) ---
    print(f"2️⃣ Consultando API Sorteo {DRAW_ID}...")

    params_api = {
        'token': TOKEN,
        'url': API_INTERNAL
        # SIN RENDER aquí, para evitar el error 400
    }

    headers_polla = {
        "x-requested-with": "XMLHttpRequest",
        "content-type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    data_polla = {
        "gameId": GAME_ID,
        "drawId": DRAW_ID,
        "csrfToken": token_polla
    }

    try:
        # Usamos la misma sesión y pasamos las cookies explícitamente por si acaso
        resp_api = session.post(
            PROXY_URL, 
            params=params_api, 
            headers=headers_polla, 
            data=data_polla,
            cookies=cookies_home, # CLAVE: Mantener la sesión
            timeout=120
        )

        if resp_api.status_code == 200:
            try:
                data = resp_api.json()
                print("   ✅ ¡VICTORIA! JSON Recibido.")
                
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                if data.get('results'):
                    print(f"   🎉 Datos: {data.get('drawDate')}")
                else:
                    print("   ⚠️ JSON válido pero vacío.")
            except:
                print("   ❌ Error: Respuesta no es JSON válido.")
                print(resp_api.text[:300])
        else:
            print(f"   ❌ Error API: {resp_api.status_code}")
            print(resp_api.text[:300])

    except Exception as e:
        print(f"🔥 Error Crítico en Fase 2: {e}")

if __name__ == "__main__":
    run_tank_scraper()