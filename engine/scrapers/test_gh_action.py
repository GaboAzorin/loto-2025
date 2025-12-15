import os
import requests
import json
import re

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("SCRAPERAPI_KEY", "").strip() 
GAME_ID = "5271" # Loto
DRAW_ID = "5360" # Sorteo Objetivo
OUTPUT_FILE = "resultado_nube_final.json"

BASE_URL = "https://www.polla.cl/es/view/resultados"
API_INTERNAL = "https://www.polla.cl/es/get/draw/results"
PROXY_URL = "http://api.scrape.do"

def run_lightweight_scraper():
    print(f"☁️ INICIANDO SCRAPER LIGERO (Sin Render)")
    
    if len(TOKEN) < 10:
        print("❌ Error: Token vacío.")
        return

    # --- PASO 1: GET SIMPLE (Sin Render) ---
    print("1️⃣ Solicitando Home (Modo Texto)...")
    
    params_home = {
        'token': TOKEN,
        'url': BASE_URL,
        # 'render': 'true' <--- ELIMINADO. Probemos si la IP residencial es suficiente.
    }

    try:
        # Usamos requests directo (sin Session) para imitar tu éxito anterior
        resp_home = requests.get(PROXY_URL, params=params_home, timeout=60)
        
        if resp_home.status_code != 200:
            print(f"❌ Falló Home. Status: {resp_home.status_code}")
            return

        # Buscamos Token
        token_polla = None
        m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', resp_home.text)
        if m: 
            token_polla = m.group(1)
            print(f"   ✅ ¡TOKEN ENCONTRADO!: {token_polla[:15]}...")
        else:
            print("   ⚠️ No hay token. (Probablemente Incapsula pide JS).")
            print("   📉 Si ves esto, significa que SÍ o SÍ necesitamos render=true.")
            return

        # Capturamos cookies manualmente de la respuesta
        cookies_home = resp_home.cookies
        print(f"   🍪 Cookies obtenidas: {len(cookies_home)}")

        # --- PASO 2: POST ---
        print(f"2️⃣ Consultando API Sorteo {DRAW_ID}...")
        
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

        # Enviamos las cookies manualmente
        resp_api = requests.post(
            PROXY_URL, 
            params=params_api, 
            headers=headers_polla, 
            data=data_polla,
            cookies=cookies_home,
            timeout=60
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
                print("   ❌ Respuesta no es JSON.")
        else:
            print(f"   ❌ Error API: {resp_api.status_code}")
            print(resp_api.text[:300])

    except Exception as e:
        print(f"🔥 Error Crítico: {e}")

if __name__ == "__main__":
    run_lightweight_scraper()