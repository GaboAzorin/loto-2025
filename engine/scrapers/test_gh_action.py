import os
import requests
import json
import re
import time
import random

# --- CONFIGURACIÓN ---
# Usamos la variable que ya tienes configurada, pero ahora sabemos que es de Scrape.do
TOKEN = os.environ.get("SCRAPERAPI_KEY", "").strip() 

GAME_ID = "5271" # Loto
DRAW_ID = "5360" # Sorteo Objetivo
OUTPUT_FILE = "resultado_nube_scrapedou.json"

# URLs
BASE_URL = "https://www.polla.cl/es/view/resultados"
API_INTERNAL = "https://www.polla.cl/es/get/draw/results"
PROXY_URL = "http://api.scrape.do"

def run_scrapedou_test():
    print(f"☁️ INICIANDO BYPASS CON SCRAPE.DO")
    
    if len(TOKEN) < 10:
        print("❌ Error: La llave (Token) parece vacía.")
        return

    # Generamos un ID de sesión aleatorio.
    # Esto obliga a Scrape.do a usar la MISMA IP para todas las peticiones de este script.
    # Si cambiamos de IP a mitad de camino, Polla invalidará el token.
    session_id = str(random.randint(100000, 999999))
    print(f"🔄 Sesión Persistente ID: {session_id}")

    print("1️⃣ Obteniendo Token CSRF vía Scrape.do...")
    
    # Parámetros para la primera llamada (Home)
    params_home = {
        'token': TOKEN,
        'url': BASE_URL,
        'render': 'true',       # Activa navegador real
        'session_id': session_id, # Mantiene la IP/Cookies
        'wait': '5000'          # Esperar 5 seg a que cargue el JS de seguridad
    }

    try:
        # GET al Home
        response = requests.get(PROXY_URL, params=params_home, timeout=120)
        
        if response.status_code != 200:
            print(f"❌ Falló Scrape.do en Home. Status: {response.status_code}")
            if response.status_code == 401:
                print("   ⛔ Error 401: Verifica tu Token de Scrape.do")
            if response.status_code == 403:
                print("   ⛔ Error 403: Scrape.do fue bloqueado o se acabaron los créditos.")
            print(response.text[:200])
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
        
        # Para hacer POST con Scrape.do, enviamos los datos a SU api, y él los reenvía.
        # Scrape.do espera que le pasemos la URL destino en 'url' y el body normal.
        
        params_api = {
            'token': TOKEN,
            'url': API_INTERNAL,
            'render': 'true', 
            'session_id': session_id # IMPORTANTE: La misma sesión
        }
        
        # Headers que Polla espera
        headers_polla = {
            "x-requested-with": "XMLHttpRequest",
            "content-type": "application/x-www-form-urlencoded"
        }
        
        # Datos del form
        data_polla = {
            "gameId": GAME_ID,
            "drawId": DRAW_ID,
            "csrfToken": token_polla
        }

        # Hacemos el POST
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
                    print("   ⚠️ JSON válido pero vacío.")
            except:
                print("   ❌ No es JSON válido.")
                print(final_resp.text[:500])
        else:
            print(f"   ❌ Error API Polla: {final_resp.status_code}")
            print(final_resp.text[:200])

    except Exception as e:
        print(f"🔥 Error Crítico: {e}")

if __name__ == "__main__":
    run_scrapedou_test()