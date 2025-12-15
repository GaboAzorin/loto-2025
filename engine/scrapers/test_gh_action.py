import os
import requests
import json
import re

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("SCRAPERAPI_KEY", "").strip() 

GAME_ID = "5271" # Loto
DRAW_ID = "5360" # Sorteo Objetivo
OUTPUT_FILE = "resultado_nube_scrapedou.json"

# URLs
BASE_URL = "https://www.polla.cl/es/view/resultados"
API_INTERNAL = "https://www.polla.cl/es/get/draw/results"
PROXY_URL = "http://api.scrape.do"

def run_scrapedou_test():
    print(f"☁️ INICIANDO BYPASS CON SCRAPE.DO (Versión Limpia)")
    
    if len(TOKEN) < 10:
        print("❌ Error: La llave (Token) parece vacía.")
        return

    print("1️⃣ Obteniendo Token CSRF vía Scrape.do...")
    
    # Parámetros ACEPTADOS por Scrape.do (Sin inventar nada)
    params_home = {
        'token': TOKEN,
        'url': BASE_URL,
        'render': 'true'
    }

    try:
        # GET al Home
        response = requests.get(PROXY_URL, params=params_home, timeout=120)
        
        if response.status_code != 200:
            print(f"❌ Falló Scrape.do en Home. Status: {response.status_code}")
            print(f"   Mensaje: {response.text[:300]}")
            return

        # Buscar el token
        token_polla = None
        m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', response.text)
        if m: 
            token_polla = m.group(1)
            print(f"   ✅ Token encontrado: {token_polla[:15]}...")
        else:
            print("   ⚠️ Token no encontrado. Guardando debug...")
            with open("debug_scrapedou.html", "w", encoding="utf-8") as f: f.write(response.text)
            return

        # 2️⃣ Petición API (POST)
        print(f"2️⃣ Consultando Sorteo {DRAW_ID}...")
        
        # Scrape.do reenvía nuestro POST al destino
        params_api = {
            'token': TOKEN,
            'url': API_INTERNAL,
            'render': 'true'
            # Eliminamos session_id para evitar error 400
        }
        
        headers_polla = {
            "x-requested-with": "XMLHttpRequest",
            "content-type": "application/x-www-form-urlencoded"
        }
        
        data_polla = {
            "gameId": GAME_ID,
            "drawId": DRAW_ID,
            "csrfToken": token_polla
        }

        final_resp = requests.post(
            PROXY_URL, 
            params=params_api, 
            headers=headers_polla, 
            data=data_polla,
            timeout=120
        )

        if final_resp.status_code == 200:
            try:
                data_json = final_resp.json()
                print("   ✅ ¡ÉXITO! JSON Recibido.")
                
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data_json, f, indent=4, ensure_ascii=False)
                
                if data_json.get('results'):
                    print(f"   🎉 Sorteo: {data_json.get('drawDate')}")
                else:
                    print("   ⚠️ JSON válido pero vacío (¿Sorteo no existe?).")
            except:
                print("   ❌ No es JSON válido.")
                print(final_resp.text[:500])
        else:
            print(f"   ❌ Error API Polla: {final_resp.status_code}")
            print(final_resp.text[:300])

    except Exception as e:
        print(f"🔥 Error Crítico: {e}")

if __name__ == "__main__":
    run_scrapedou_test()