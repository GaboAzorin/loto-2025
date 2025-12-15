import os
import requests
import json
import re

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("SCRAPERAPI_KEY", "").strip() 
GAME_ID = "5271" # Loto
DRAW_ID = "5360" # Sorteo Objetivo
OUTPUT_FILE = "resultado_nube_final.json"

# URLs
TARGET_URL = "https://www.polla.cl" # Home (Ligero)
API_INTERNAL = "https://www.polla.cl/es/get/draw/results"
PROXY_ENDPOINT = "http://api.scrape.do"

def run_hybrid_scraper():
    print(f"☁️ INICIANDO SCRAPER HÍBRIDO (Modo API + Cookies)")
    
    if len(TOKEN) < 10:
        print("❌ Error: Token vacío.")
        return

    # --- PASO 1: OBTENER HOME (Modo API) ---
    # Usamos la configuración exacta que funcionó en tu Imagen 4
    print("1️⃣ Solicitando Home (Buscando Token)...")
    
    params_home = {
        'token': TOKEN,
        'url': TARGET_URL,
        'render': 'true',  # Activamos navegador
        'timeout': '20000' # Damos 20s a Scrape.do para que no corte
    }

    try:
        # GET a la API de Scrape.do
        resp_home = requests.get(PROXY_ENDPOINT, params=params_home, timeout=120)
        
        if resp_home.status_code != 200:
            print(f"❌ Falló Home. Status: {resp_home.status_code}")
            print(f"   Msg: {resp_home.text[:200]}")
            return

        # A. Extraer Token
        token_polla = None
        m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', resp_home.text)
        if m: 
            token_polla = m.group(1)
            print(f"   ✅ ¡TOKEN CAPTURADO!: {token_polla[:15]}...")
        else:
            print("   ⚠️ Token no encontrado en HTML.")
            return

        # B. Extraer Cookies (CRUCIAL)
        # Las cookies vienen en la respuesta de Scrape.do
        cookies_home = resp_home.cookies
        print(f"   🍪 Cookies capturadas: {len(cookies_home)}")

        # --- PASO 2: POST A LA API (Modo API) ---
        print(f"2️⃣ Consultando API Sorteo {DRAW_ID}...")

        # Configuración para el POST
        # NO usamos 'render=true' aquí para evitar el error 400 anterior
        params_api = {
            'token': TOKEN,
            'url': API_INTERNAL
        }

        data_polla = {
            "gameId": GAME_ID,
            "drawId": DRAW_ID,
            "csrfToken": token_polla
        }
        
        headers_polla = {
            "x-requested-with": "XMLHttpRequest",
            "content-type": "application/x-www-form-urlencoded"
        }

        # Hacemos POST a Scrape.do, pasándole las cookies del paso 1
        resp_api = requests.post(
            PROXY_ENDPOINT, 
            params=params_api, 
            headers=headers_polla, 
            data=data_polla,
            cookies=cookies_home, # <--- El pegamento que mantiene la sesión
            timeout=120
        )

        if resp_api.status_code == 200:
            try:
                data = resp_api.json()
                print("   ✅ ¡VICTORIA! JSON Recibido.")
                
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                if data.get('results'):
                    print(f"   🎉 Fecha Sorteo: {data.get('drawDate')}")
                else:
                    print("   ⚠️ JSON válido pero vacío.")
            except:
                print("   ❌ Error: Respuesta no es JSON.")
                print(resp_api.text[:300])
        else:
            print(f"   ❌ Error API: {resp_api.status_code}")
            print(resp_api.text[:300])

    except Exception as e:
        print(f"🔥 Error Crítico: {e}")

if __name__ == "__main__":
    run_hybrid_scraper()