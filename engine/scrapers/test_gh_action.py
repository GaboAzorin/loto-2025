import asyncio
import json
import re
import os
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN ---
TOKEN = os.environ.get("SCRAPERAPI_KEY", "").strip() # Tu llave de Scrape.do
GAME_ID = "5271" # Loto
DRAW_ID = "5360" # Sorteo Objetivo
OUTPUT_FILE = "resultado_nube_playwright.json"

BASE_URL = "https://www.polla.cl/es/view/resultados"
API_URL = "https://www.polla.cl/es/get/draw/results"

async def run_proxy_test():
    print(f"🕷️ INICIANDO PLAYWRIGHT CON PROXY SCRAPE.DO")
    
    if len(TOKEN) < 10:
        print("❌ Error: Token vacío.")
        return

    async with async_playwright() as p:
        # --- LA MAGIA: CONFIGURAR EL PROXY ---
        # Scrape.do permite usarlo como un proxy estándar.
        # Formato: http://proxy.scrape.do:8080
        # Auth: username=TOKEN, password=""
        
        print("🌍 Configurando túnel residencial...")
        browser = await p.chromium.launch(
            headless=True,
            proxy={
                "server": "http://proxy.scrape.do:8080",
                "username": TOKEN,
                "password": "" 
            }
        )
        
        # Usamos tu User-Agent probado para parecer Windows 10 real
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True # Importante para proxies
        )
        page = await context.new_page()

        try:
            print("1️⃣ Navegando al Home (Obteniendo Cookies y Token)...")
            
            # Navegamos. Como vamos por proxy, Scrape.do rota la IP por nosotros.
            # Aumentamos timeout a 60s porque los proxies residenciales son algo lentos.
            await page.goto(BASE_URL, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(5) # Espera de seguridad

            # TU LÓGICA DE EXTRACCIÓN (ROBUSTA)
            token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
            
            if not token:
                print("   ⚠️ Token no en DOM. Intentando Regex...")
                content = await page.content()
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
                if m: 
                    token = m.group(1)
            
            if not token:
                print("❌ FATAL: No se encontró Token CSRF.")
                # Guardar HTML para debug
                await page.screenshot(path="debug_error.png")
                with open("debug_error.html", "w", encoding="utf-8") as f:
                    f.write(await page.content())
                return

            print(f"   ✅ Token Validado: {token[:15]}...")

            # 2. PETICIÓN API (Desde el contexto del navegador)
            # Esto es vital: Playwright envía la petición DESDE la misma sesión/IP
            print(f"2️⃣ Solicitando Sorteo {DRAW_ID}...")
            
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
                print(await response.text())

        except Exception as e:
            print(f"🔥 Error Crítico: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_proxy_test())