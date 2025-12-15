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

def run_simple_fix():
    print(f"☁️ INICIANDO SCRAPER SIMPLE (Configuración Exitosa)")
    
    if len(TOKEN) < 10:
        print("❌ Error: Token vacío.")
        return

    # Usamos session para manejar cookies automáticamente
    session = requests.Session()

    # --- PASO 1: LA CONFIGURACIÓN EXACTA QUE FUNCIONÓ ---
    print("1️⃣ Solicitando Home (GET + Render)...")
    
    # En la imagen b878e1.png (la exitosa), solo usamos estos parámetros:
    params_home = {
        'token': TOKEN,
        'url': BASE_URL,
        'render': 'true' 
        # SIN timeout, SIN session_id, SIN wait. Simple.
    }

    try:
        resp_home = session.get(PROXY_URL, params=params_home, timeout=120)
        
        if resp_home.status_code != 200:
            print(f"❌ Falló Home. Status: {resp_home.status_code}")
            print(f"   Msg: {resp_home.text[:300]}")
            return

        # Buscamos el Token
        token_polla = None
        m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', resp_home.text)
        if m: 
            token_polla = m.group(1)
            print(f"   ✅ ¡TOKEN ENCONTRADO!: {token_polla[:15]}...")
        else:
            print("   ⚠️ No hay token en el HTML. (Posible bloqueo visual)")
            return

        # --- PASO 2: EL POST (Corregido) ---
        print(f"2️⃣ Consultando API Sorteo {DRAW_ID}...")
        
        # Aquí NO usamos render (porque es POST), pero pasamos las cookies
        # que 'session' capturó en el paso 1.
        
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

        resp_api = session.post(
            PROXY_URL, 
            params=params_api, 
            headers=headers_polla, 
            data=data_polla,
            timeout=120
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
                print(resp_api.text[:300])
        else:
            print(f"   ❌ Error API: {resp_api.status_code}")
            print(resp_api.text[:300])

    except Exception as e:
        print(f"🔥 Error Crítico: {e}")

if __name__ == "__main__":
    run_simple_fix()