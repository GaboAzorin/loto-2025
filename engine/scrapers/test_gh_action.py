import os
import requests
import json
import re

# --- CONFIGURACIÓN ---
API_KEY = os.environ.get("SCRAPERAPI_KEY") 
GAME_ID = "5271" # Loto
DRAW_ID = "5360" # Sorteo Objetivo
OUTPUT_FILE = "resultado_nube_scraperapi.json"

# URLs
BASE_URL = "https://www.polla.cl/es/view/resultados"
API_INTERNAL = "https://www.polla.cl/es/get/draw/results"

def run_scraperapi_test():
    print(f"☁️ INICIANDO BYPASS CON SCRAPERAPI (Free Tier)")
    
    if not API_KEY:
        print("❌ Error: Falta la SCRAPERAPI_KEY")
        return

    # ScraperAPI funciona enviando tu petición a SU servidor.
    # Usamos render=true para que ellos carguen el JS de Incapsula.
    scraper_url = "http://api.scraperapi.com"

    print("1️⃣ Obteniendo Token CSRF vía ScraperAPI...")
    
    # Payload para pedirle a ScraperAPI que vaya al HOME de Polla
    params_home = {
        'api_key': API_KEY,
        'url': BASE_URL,
        'render': 'true',      # Importante para que ejecute el JS de bloqueo
        'country_code': 'us',  # A veces CL funciona mejor, a veces US. Probamos US estándar.
    }

    try:
        # Hacemos GET a ScraperAPI -> Ellos van a Polla -> Nos devuelven el HTML ya procesado
        response = requests.get(scraper_url, params=params_home, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ Falló ScraperAPI en Home: {response.status_code}")
            print(response.text[:200]) # Ver error
            return

        # Buscamos el token en el HTML que nos devolvieron
        token = None
        m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', response.text)
        if m: 
            token = m.group(1)
            print(f"   ✅ Token encontrado: {token[:15]}...")
        else:
            print("   ⚠️ Token no encontrado en el HTML devuelto.")
            # Guardar debug
            with open("debug_scraperapi.html", "w", encoding="utf-8") as f: f.write(response.text)
            return

        # 2️⃣ Petición POST a la API de Polla
        # Para peticiones POST con ScraperAPI, se envían headers y data de forma especial
        print(f"2️⃣ Consultando Sorteo {DRAW_ID}...")
        
        # Headers que Polla espera
        polla_headers = {
            "x-requested-with": "XMLHttpRequest",
            "content-type": "application/x-www-form-urlencoded"
        }
        
        # Datos que Polla espera
        polla_data = {
            "gameId": GAME_ID,
            "drawId": DRAW_ID,
            "csrfToken": token
        }

        # Configuración final para ScraperAPI (POST)
        # Nota: ScraperAPI maneja las cookies de sesión automáticamente si usas 'keep_headers' a veces,
        # pero para APIs complejas, a veces es mejor pasar todo en el payload.
        
        final_response = requests.post(
            scraper_url,
            params={
                'api_key': API_KEY,
                'url': API_INTERNAL,
                'render': 'true' # Mantenemos render para consistencia
            },
            headers=polla_headers,
            data=polla_data
        )

        if final_response.status_code == 200:
            try:
                data = final_response.json()
                print("   ✅ ¡ÉXITO! JSON Recibido.")
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                
                if data.get('results'):
                    print(f"   🎉 Datos reales obtenidos: {data.get('drawDate')}")
                else:
                    print("   ⚠️ JSON vacío (¿Sorteo no disponible?)")
            except:
                print("   ❌ La respuesta no es JSON válido.")
                print(final_response.text[:500])
        else:
            print(f"   ❌ Error en API Polla: {final_response.status_code}")

    except Exception as e:
        print(f"🔥 Error Crítico: {e}")

if __name__ == "__main__":
    run_scraperapi_test()