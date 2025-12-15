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

def run_api_fix():
    print(f"☁️ INICIANDO MÉTODO API + COOKIES MANUALES")
    
    if len(TOKEN) < 10:
        print("❌ Error: Token de Scrape.do vacío.")
        return

    # 1. OBTENER HOME (Con Render para saltar seguridad)
    print("1️⃣ Solicitando Home (GET + Render)...")
    
    params_home = {
        'token': TOKEN,
        'url': BASE_URL,
        'render': 'true' # Vital para que Incapsula nos deje pasar
    }

    try:
        resp_home = requests.get(PROXY_URL, params=params_home, timeout=120)
        
        if resp_home.status_code != 200:
            print(f"❌ Falló Home. Status: {resp_home.status_code}")
            return

        # A. Extraer Token CSRF
        token_polla = None
        m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', resp_home.text)
        if m: 
            token_polla = m.group(1)
            print(f"   ✅ Token CSRF: {token_polla[:15]}...")
        else:
            print("   ⚠️ No se encontró Token. Guardando HTML debug.")
            print(f"   Fragmento HTML: {resp_home.text[:500]}") # Ver qué devolvió
            return

        # B. Extraer Cookies (¡El Truco!)
        # Scrape.do a veces devuelve las cookies del sitio en sus headers, 
        # o las incrusta. Vamos a intentar usar las cookies que requests capturó.
        cookies_home = resp_home.cookies
        print(f"   🍪 Cookies capturadas: {len(cookies_home)} cookies.")

        # 2. CONSULTAR API (POST Limpio)
        print(f"2️⃣ Consultando Sorteo {DRAW_ID}...")

        # Parámetros para Scrape.do (SIN RENDER para POST)
        params_api = {
            'token': TOKEN,
            'url': API_INTERNAL,
            # 'render': 'true' <--- ELIMINADO. Esto causaba el error 400.
        }

        # Datos para Polla
        data_polla = {
            "gameId": GAME_ID,
            "drawId": DRAW_ID,
            "csrfToken": token_polla
        }
        
        headers_polla = {
            "x-requested-with": "XMLHttpRequest",
            "content-type": "application/x-www-form-urlencoded",
            # Intentamos pasar el User-Agent para parecer el mismo navegador
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36" 
        }

        # Hacemos el POST pasando las cookies de la etapa 1
        resp_api = requests.post(
            PROXY_URL, 
            params=params_api, 
            headers=headers_polla, 
            data=data_polla,
            cookies=cookies_home, # <--- Aquí está la clave de la continuidad
            timeout=120
        )

        if resp_api.status_code == 200:
            try:
                data_json = resp_api.json()
                print("   ✅ ¡ÉXITO! JSON Recibido.")
                
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data_json, f, indent=4, ensure_ascii=False)
                
                if data_json.get('results'):
                    print(f"   🎉 DATOS REALES: {data_json.get('drawDate')}")
                    print("   💰 ¡Tenemos datos! El flujo funciona.")
                else:
                    print("   ⚠️ JSON válido pero vacío (¿Sorteo no existe?).")
            except:
                print("   ❌ Respuesta no es JSON.")
                print(resp_api.text[:500])
        else:
            print(f"   ❌ Error API Polla: {resp_api.status_code}")
            print(f"   Cuerpo Error: {resp_api.text[:500]}")

    except Exception as e:
        print(f"🔥 Error Crítico: {e}")

if __name__ == "__main__":
    run_api_fix()