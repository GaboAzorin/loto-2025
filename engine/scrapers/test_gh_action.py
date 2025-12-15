import os
import requests
import json
import re
import urllib3

# Desactivar advertencias de certificados SSL (común al usar proxies)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("SCRAPERAPI_KEY", "").strip() 
GAME_ID = "5271" # Loto
DRAW_ID = "5360" # Sorteo Objetivo
OUTPUT_FILE = "resultado_nube_final.json"

# CAMBIO CLAVE: Vamos al Home, que es más ligero que /view/resultados
TARGET_URL = "https://www.polla.cl" 
API_INTERNAL = "https://www.polla.cl/es/get/draw/results"

def run_smart_scraper():
    print(f"☁️ INICIANDO SCRAPER OPTIMIZADO (Target: Home)")
    
    if len(TOKEN) < 10:
        print("❌ Error: Token vacío.")
        return

    session = requests.Session()

    # --- CONFIGURACIÓN PROXY SCRAPE.DO ---
    # Usamos el modo Proxy Estándar.
    # Sintaxis: http://token:render=true@proxy.scrape.do:8080
    proxy_auth = f"{TOKEN}:render=true"
    proxy_url = f"http://{proxy_auth}@proxy.scrape.do:8080"
    
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }

    print(f"1️⃣ Solicitando {TARGET_URL} (Buscando Token)...")
    
    try:
        # Petición al Home usando el Proxy
        # verify=False es necesario porque el proxy intercepta el SSL
        resp_home = session.get(TARGET_URL, proxies=proxies, verify=False, timeout=120)
        
        if resp_home.status_code != 200:
            print(f"❌ Falló Carga. Status: {resp_home.status_code}")
            # Si es 502, es culpa de Scrape.do. Si es 403, es Polla.
            print(f"   Respuesta: {resp_home.text[:200]}")
            return

        # Buscar Token
        token_polla = None
        # Buscamos el token en el HTML del home
        m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', resp_home.text)
        if m: 
            token_polla = m.group(1)
            print(f"   ✅ ¡TOKEN CAPTURADO!: {token_polla[:15]}...")
        else:
            print("   ⚠️ No encontré token en el Home.")
            # Guardamos debug
            with open("debug_home.html", "w", encoding="utf-8") as f: f.write(resp_home.text)
            return

        # --- PASO 2: POST A LA API ---
        print(f"2️⃣ Consultando API Sorteo {DRAW_ID}...")
        
        # Para el POST, usamos el MISMO proxy pero desactivamos render si es posible
        # Para simplificar, usamos la misma configuración de proxy (render=true no afecta negativamente al POST si ya tenemos cookies)
        
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

        # Las cookies ya viajan en la 'session' automáticamente
        resp_api = session.post(
            API_INTERNAL, # Atacamos directo a la URL de Polla (el proxy intercepta)
            proxies=proxies,
            headers=headers_polla, 
            data=data_polla,
            verify=False,
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
    run_smart_scraper()