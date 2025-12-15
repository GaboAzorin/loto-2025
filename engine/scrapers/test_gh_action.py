import asyncio
import json
import re
import os
import random
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("SCRAPERAPI_KEY", "").strip() 
GAME_ID = "5271" # Loto
DRAW_ID = "5360" # Sorteo Objetivo
OUTPUT_FILE = "resultado_nube_playwright.json"

BASE_URL = "https://www.polla.cl/es/view/resultados"
API_URL = "https://www.polla.cl/es/get/draw/results"

async def run_proxy_test():
    print(f"🕷️ INICIANDO PLAYWRIGHT STEALTH + STICKY PROXY")
    
    if len(TOKEN) < 10:
        print("❌ Error: Token vacío.")
        return

    # Generamos un ID de sesión para que Scrape.do nos de la MISMA IP
    # durante toda la ejecución.
    session_id = str(random.randint(10000, 99999))
    print(f"🔄 Usando Sticky Session ID: {session_id}")

    async with async_playwright() as p:
        
        # --- CONFIGURACIÓN DEL PROXY (MODO EXPERTO) ---
        # Username: Tu Token
        # Password: Los parámetros de Scrape.do. 
        #           'render=false' (porque ya renderizamos nosotros)
        #           'sessionId=...' (para mantener la IP fija)
        proxy_params = f"render=false&sessionId={session_id}"
        
        print("🌍 Configurando navegador blindado...")
        
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled", # Oculta que es un robot
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ],
            proxy={
                "server": "http://proxy.scrape.do:8080",
                "username": TOKEN,
                "password": proxy_params 
            }
        )
        
        # Contexto con User-Agent de usuario real (Windows 10 / Chrome)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            ignore_https_errors=True,
            viewport={"width": 1920, "height": 1080}
        )
        
        # Truco extra: Inyectar script para ocultar webdriver
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = await context.new_page()

        try:
            print("1️⃣ Navegando al Home (Timeout 90s)...")
            
            # Aumentamos timeout a 90s porque los proxies residenciales "sticky" a veces tardan en negociar
            await page.goto(BASE_URL, timeout=90000, wait_until="domcontentloaded")
            
            # Esperamos un poco más para que Incapsula valide el navegador
            print("   ⏳ Esperando validación de seguridad (5s)...")
            await asyncio.sleep(5)

            # Validar título para saber si cargó Polla o el bloqueo
            title = await page.title()
            print(f"   📄 Título detectado: {title}")

            # EXTRACCIÓN DEL TOKEN
            token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
            
            if not token:
                print("   ⚠️ Token no en DOM. Intentando Regex...")
                content = await page.content()
                # Debug: Guardar HTML si falla (para ver si es bloqueo)
                with open("debug_page_source.html", "w", encoding="utf-8") as f: f.write(content)
                
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
                if m: 
                    token = m.group(1)
            
            if not token:
                print("❌ FATAL: No se encontró Token CSRF.")
                # Sacar foto del error
                await page.screenshot(path="debug_screenshot.png")
                print("   📸 Screenshot guardado como debug_screenshot.png")
                return

            print(f"   ✅ Token Validado: {token[:15]}...")

            # 2. PETICIÓN API
            print(f"2️⃣ Solicitando Sorteo {DRAW_ID}...")
            
            # Importante: La petición sale del MISMO contexto, por la MISMA IP (gracias al sessionId)
            response = await page.request.post(API_URL, data={
                "gameId": GAME_ID, 
                "drawId": DRAW_ID, 
                "csrfToken": token
            }, headers={
                "x-requested-with": "XMLHttpRequest"
            })

            if response.status == 200:
                try:
                    data = await response.json()
                    print("   ✅ ¡ÉXITO! JSON Recibido.")
                    
                    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    
                    if data.get('results'):
                        print(f"   🎉 Fecha Sorteo: {data.get('drawDate')}")
                    else:
                        print("   ⚠️ JSON vacío (¿Sorteo futuro?)")
                except:
                    print("   ❌ Error parseando JSON.")
            else:
                print(f"   ❌ Error HTTP {response.status}")

        except Exception as e:
            print(f"🔥 Error Crítico: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_proxy_test())