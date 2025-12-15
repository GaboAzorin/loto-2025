import asyncio
import json
import re
import os
from playwright.async_api import async_playwright

# --- CONFIGURACIÓN ---
GAME_ID = "5271"      # Loto
DRAW_ID = "5360"      # Sorteo Objetivo
OUTPUT_FILE = "resultado_gh_5360.json"
BASE_URL = "https://www.polla.cl/es/view/resultados"
API_URL = "https://www.polla.cl/es/get/draw/results"

async def run_remote_test():
    print(f"🚀 INICIANDO TEST REMOTO DESDE GITHUB ACTIONS")
    print(f"🌍 IP Check: Intentando conectar a {BASE_URL}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Usamos un User-Agent muy estándar de Windows/Chrome para "disfrazar" al bot de Github
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 1. Obtener Token
            print("1️⃣  Cargando Home para cookies y token...")
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5) # Espera generosa para scripts

            token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
            
            if not token:
                print("   ⚠️  Token no en DOM. Usando Regex...")
                content = await page.content()
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
                if m: token = m.group(1)
            
            if not token:
                # Si falla aquí, es probable que Polla haya detectado la IP de Github y no haya servido el sitio correctamente
                print("❌ FATAL: No se pudo obtener Token. Posible bloqueo de IP.")
                # Guardamos el HTML para que puedas inspeccionar qué devolvió Polla
                with open("debug_error.html", "w", encoding="utf-8") as f:
                    f.write(await page.content())
                return

            print(f"   🔑 Token obtenido: {token[:10]}...")

            # 2. Petición API
            print(f"2️⃣  Solicitando sorteo {DRAW_ID}...")
            response = await page.request.post(API_URL, data={
                "gameId": GAME_ID, "drawId": DRAW_ID, "csrfToken": token
            }, headers={"x-requested-with": "XMLHttpRequest"})

            if response.status == 200:
                data = await response.json()
                print("   ✅ ¡RESPUESTA 200 OK! (Parece que funcionó)")
                
                # Guardamos el JSON
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                print(f"   💾 Archivo guardado: {OUTPUT_FILE}")
            else:
                print(f"   ❌ Error HTTP {response.status} al consultar API.")

        except Exception as e:
            print(f"🔥 EXCEPCIÓN: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_remote_test())