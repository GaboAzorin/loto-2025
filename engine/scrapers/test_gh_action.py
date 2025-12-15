import os
import requests
import json
import re

# --- CONFIGURACIÓN ---
# .strip() elimina espacios en blanco al inicio o final que causan el error 401
API_KEY = os.environ.get("SCRAPERAPI_KEY", "").strip() 

GAME_ID = "5271" # Loto
DRAW_ID = "5360" # Sorteo Objetivo
OUTPUT_FILE = "resultado_nube_scraperapi.json"

# URLs
BASE_URL = "https://www.polla.cl/es/view/resultados"
API_INTERNAL = "https://www.polla.cl/es/get/draw/results"

def run_scraperapi_test():
    print(f"☁️ INICIANDO BYPASS CON SCRAPERAPI (Free Tier)")
    
    # --- 1. DIAGNÓSTICO DE LLAVE (CRUCIAL) ---
    longitud = len(API_KEY)
    print(f"🔑 Diagnóstico: GitHub entregó una llave de {longitud} caracteres.")
    
    if longitud < 10:
        print("❌ ERROR CRÍTICO: La llave está vacía o es muy corta.")
        print("   👉 Revisa en GitHub: Settings > Secrets > Actions.")
        print("   👉 Asegúrate que el secreto se llame: SCRAPERAPI_KEY")
        return
    # -----------------------------------------

    # ScraperAPI endpoint
    scraper_url = "http://api.scraperapi.com"

    print("1️⃣ Obteniendo Token CSRF vía ScraperAPI...")
    
    # Parámetros para pedir el Home (render=true activa el navegador real de ellos)
    params_home = {
        'api_key': API_KEY,
        'url': BASE_URL,
        'render': 'true',      
        'country_code': 'us', # Probamos US, suele ser más rápido/estable en free tier
    }

    try:
        # Hacemos GET a ScraperAPI -> Ellos van a Polla
        response = requests.get(scraper_url, params=params_home, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ Falló ScraperAPI en Home. Status: {response.status_code}")
            # Si es 401 aquí, es definitivamente la llave o créditos agotados
            if response.status_code == 401:
                print("   ⛔ Error 401: Llave inválida o sin créditos.")
            return

        # Buscamos el token en el HTML que nos devolvieron
        token = None
        m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', response.text)
        if m: 
            token = m.group(1)
            print(f"   ✅ Token encontrado: {token[:15]}...")
        else:
            print("   ⚠️ Token no encontrado en el HTML devuelto.")
            # Guardamos debug para ver qué nos devolvió ScraperAPI
            with open("debug_scraperapi.html", "w", encoding="utf-8") as f: f.write(response.text)
            return

        # --- 2. CONSULTAR LA API INTERNA ---
        print(f"2️⃣ Consultando Sorteo {DRAW_ID}...")
        
        # Headers necesarios para que Polla crea que somos un navegador
        polla_headers = {
            "x-requested-with": "XMLHttpRequest",
            "content-type": "application/x-www-form-urlencoded"
        }
        
        # Payload con el token que acabamos de ganar
        polla_data = {
            "gameId": GAME_ID,
            "drawId": DRAW_ID,
            "csrfToken": token
        }

        # Petición POST a través de ScraperAPI
        final_response = requests.post(
            scraper_url,
            params={
                'api_key': API_KEY,
                'url': API_INTERNAL,
                'render': 'true' 
            },
            headers=polla_headers,
            data=polla_data
        )

        if final_response.status_code == 200:
            try:
                data = final_response.json()
                print("   ✅ ¡ÉXITO! JSON Recibido.")
                
                # Guardamos el resultado
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                if data.get('results'):
                    print(f"   🎉 Datos reales obtenidos: {data.get('drawDate')}")
                else:
                    print("   ⚠️ JSON válido pero sin resultados (¿Sorteo futuro?)")
            except:
                print("   ❌ La respuesta no es un JSON válido.")
                print(final_response.text[:500])
        else:
            print(f"   ❌ Error en API Polla: {final_response.status_code}")
            print(final_response.text[:200])

    except Exception as e:
        print(f"🔥 Error Crítico en ejecución: {e}")

if __name__ == "__main__":
    run_scraperapi_test()