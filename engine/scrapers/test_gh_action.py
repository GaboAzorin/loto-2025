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
TARGET_URL = "https://www.polla.cl" # Home (Más ligero)
API_INTERNAL = "https://www.polla.cl/es/get/draw/results"
PROXY_ENDPOINT = "http://api.scrape.do"

def run_scrapedou_sniper():
    print(f"☁️ INICIANDO SCRAPER FRANCOTIRADOR (Target: US Node)")
    
    if len(TOKEN) < 10:
        print("❌ Error: Token vacío.")
        return

    # --- PASO 1: OBTENER HOME (Bucle de intentos) ---
    token_polla = None
    cookies_home = None
    
    # Intentaremos 5 veces buscando un nodo estable en USA
    for i in range(1, 6):
        print(f"\n🔄 Intento {i}/5 (Node US)...")
        
        params_home = {
            'token': TOKEN,
            'url': TARGET_URL,
            'render': 'true', 
            'geoCode': 'us', # FORZAMOS USA: Suelen ser servidores más potentes
            'timeout': '25000'
        }
        
        try:
            # Petición limpia: Sin headers manuales, dejamos que Scrape.do decida
            resp = requests.get(PROXY_ENDPOINT, params=params_home, timeout=90)
            
            if resp.status_code == 200:
                # Buscar Token
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', resp.text)
                if m:
                    token_polla = m.group(1)
                    cookies_home = resp.cookies
                    print(f"   ✅ ¡BLANCO! Token capturado: {token_polla[:15]}...")
                    break 
                else:
                    print("   ⚠️ HTML descargado pero sin token (¿Falta JS?). Reintentando...")
            
            elif resp.status_code == 502:
                print("   ⚠️ Error 502 (Proxy sobrecargado). Esperando 3s...")
                time.sleep(3)
            
            else:
                print(f"   ⚠️ Error {resp.status_code}. Reintentando...")

        except Exception as e:
            print(f"   🔥 Error conexión: {e}")
            time.sleep(2)

    if not token_polla:
        print("\n❌ MISIÓN FALLIDA: No se pudo obtener token.")
        print("   Diagnóstico: Scrape.do no está logrando renderizar Polla.cl hoy.")
        return

    # --- PASO 2: POST A LA API ---
    print(f"\n2️⃣ Consultando API Sorteo {DRAW_ID}...")

    params_api = {
        'token': TOKEN,
        'url': API_INTERNAL,
        'geoCode': 'us' # Mantenemos coherencia de zona
    }

    # Headers mínimos para el POST
    headers_polla = {
        "x-requested-with": "XMLHttpRequest",
        "content-type": "application/x-www-form-urlencoded"
    }

    data_polla = {
        "gameId": GAME_ID,
        "drawId": DRAW_ID,
        "csrfToken": token_polla
    }

    try:
        # Pasamos las cookies capturadas
        resp_api = requests.post(
            PROXY_ENDPOINT, 
            params=params_api, 
            headers=headers_polla, 
            data=data_polla,
            cookies=cookies_home,
            timeout=90
        )

        if resp_api.status_code == 200:
            try:
                data = resp_api.json()
                print("   ✅ ¡ÉXITO TOTAL! JSON Recibido.")
                
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
            print(resp_api.text[:500])

    except Exception as e:
        print(f"🔥 Error Crítico Fase 2: {e}")

if __name__ == "__main__":
    run_scrapedou_sniper()