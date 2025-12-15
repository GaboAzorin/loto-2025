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

# URLs
TARGET_URL = "https://www.polla.cl" # Home
API_INTERNAL = "https://www.polla.cl/es/get/draw/results"
PROXY_ENDPOINT = "http://api.scrape.do"

def run_mobile_resilient_scraper():
    print(f"☁️ INICIANDO SCRAPER MÓVIL (Con Reintentos)")
    
    if len(TOKEN) < 10:
        print("❌ Error: Token vacío.")
        return

    # --- PASO 1: OBTENER HOME (Bucle de Intentos) ---
    token_polla = None
    cookies_home = None
    
    # Intentaremos hasta 10 veces si es necesario (el 502 es temporal)
    MAX_RETRIES = 10 
    
    for i in range(1, MAX_RETRIES + 1):
        print(f"\n🔄 Intento {i}/{MAX_RETRIES} conectando a Polla...")
        
        params_home = {
            'token': TOKEN,
            'url': TARGET_URL,
            'render': 'true', 
            'timeout': '25000' # Pedimos más tiempo
        }
        
        # Simulamos ser un celular Android (sitio más ligero = menos error 502)
        headers_mobile = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
        }

        try:
            resp_home = requests.get(
                PROXY_ENDPOINT, 
                params=params_home, 
                headers=headers_mobile, 
                timeout=120
            )
            
            if resp_home.status_code == 200:
                # Buscar Token
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', resp_home.text)
                if m: 
                    token_polla = m.group(1)
                    cookies_home = resp_home.cookies
                    print(f"   ✅ ¡CONEXIÓN ESTABLECIDA! Token: {token_polla[:15]}...")
                    break # ¡Éxito! Salimos del bucle
                else:
                    print("   ⚠️ Página cargó pero no veo el token. Reintentando...")
            
            elif resp_home.status_code == 502:
                print("   ⚠️ Error 502 (Scrape.do saturado). Esperando 5s...")
                time.sleep(5)
            
            else:
                print(f"   ⚠️ Error {resp_home.status_code}. Reintentando...")
                time.sleep(2)

        except Exception as e:
            print(f"   🔥 Excepción de conexión: {e}")
            time.sleep(5)

    if not token_polla:
        print("\n❌ FALLO FATAL: No se pudo conectar tras todos los intentos.")
        return

    # --- PASO 2: POST A LA API (Ya tenemos el token) ---
    print(f"\n2️⃣ Consultando API Sorteo {DRAW_ID}...")

    params_api = {
        'token': TOKEN,
        'url': API_INTERNAL
        # Sin render aquí
    }

    data_polla = {
        "gameId": GAME_ID,
        "drawId": DRAW_ID,
        "csrfToken": token_polla
    }
    
    headers_polla = {
        "x-requested-with": "XMLHttpRequest",
        "content-type": "application/x-www-form-urlencoded",
        # Mantenemos el User-Agent móvil
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
    }

    try:
        resp_api = requests.post(
            PROXY_ENDPOINT, 
            params=params_api, 
            headers=headers_polla, 
            data=data_polla,
            cookies=cookies_home, # Cookies capturadas arriba
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
        print(f"🔥 Error Crítico Fase 2: {e}")

if __name__ == "__main__":
    run_mobile_resilient_scraper()