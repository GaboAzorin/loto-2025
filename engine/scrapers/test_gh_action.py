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

def run_resilient_scraper():
    print(f"☁️ INICIANDO SCRAPER RESILIENTE (Reintentos Automáticos)")
    
    if len(TOKEN) < 10:
        print("❌ Error: Token vacío.")
        return

    # Variables para guardar lo que logremos capturar
    token_polla = None
    cookies_home = None

    # --- FASE 1: OBTENER HOME (Bucle de intentos) ---
    max_retries = 5
    
    for i in range(1, max_retries + 1):
        print(f"\n🔄 Intento {i}/{max_retries} para obtener Home...")
        
        # Volvemos a la configuración que SÍ funcionó (con render)
        params_home = {
            'token': TOKEN,
            'url': BASE_URL,
            'render': 'true' # Necesario para Incapsula
        }

        try:
            # Sin session, requests directo para forzar limpieza
            resp = requests.get(PROXY_URL, params=params_home, timeout=90)
            
            if resp.status_code == 200:
                # Buscar Token
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', resp.text)
                if m:
                    token_polla = m.group(1)
                    cookies_home = resp.cookies
                    print(f"   ✅ ¡ÉXITO! Token capturado: {token_polla[:15]}...")
                    break # Salimos del bucle
                else:
                    print("   ⚠️ Página cargó (200 OK) pero no veo el token. Reintentando...")
            
            elif resp.status_code == 502:
                print("   ⚠️ Error 502 (Proxy inestable). Probando otra IP en 5 seg...")
                time.sleep(5)
            
            else:
                print(f"   ⚠️ Error {resp.status_code}. Reintentando...")
                time.sleep(2)

        except Exception as e:
            print(f"   🔥 Error de conexión: {e}")
            time.sleep(5)

    if not token_polla:
        print("\n❌ FALLO TOTAL: No se pudo entrar tras 5 intentos.")
        return

    # --- FASE 2: EL POST (Solo si tuvimos éxito arriba) ---
    print(f"\n2️⃣ Consultando API Sorteo {DRAW_ID}...")
    
    # Parámetros para el POST (Sin render, con cookies)
    params_api = {
        'token': TOKEN,
        'url': API_INTERNAL
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

    try:
        # Importante: Pasamos las cookies capturadas en la Fase 1
        resp_api = requests.post(
            PROXY_URL, 
            params=params_api, 
            headers=headers_polla, 
            data=data_polla,
            cookies=cookies_home,
            timeout=90
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
            print(resp_api.text[:500])

    except Exception as e:
        print(f"🔥 Error Crítico Fase 2: {e}")

if __name__ == "__main__":
    run_resilient_scraper()