import asyncio
import json
import os
import random
import re
import subprocess
from datetime import datetime

from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# Instala si no tienes: pip install playwright playwright-extra playwright-extra-plugin-stealth
# Luego: playwright install chromium
try:
    from playwright_extra import chromium_extra
    from playwright_extra.plugins import StealthPlugin
    chromium_extra.register_plugin(StealthPlugin())
except ImportError:
    print("⚠️ playwright-extra o stealth no instalado. Funcionará pero menos sigiloso.")
    from playwright.async_api import async_playwright as pw_original
    chromium_extra = None

BASE_URL = "https://www.polla.cl/es/view/resultados"
API_URL = "https://www.polla.cl/es/get/draw/results"
GAME_ID = "5271"  # Loto clásico
DRAW_ID = 5200    # El que quieres probar

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "test")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"loto_sorteo_{DRAW_ID}.json")

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]

async def main():
    print(f"\n🕷️  TEST SCRAPER: Consultando sorteo Loto #{DRAW_ID}")

    launch_func = chromium_extra.launch if chromium_extra else async_playwright().chromium.launch

    async with (chromium_extra if chromium_extra else async_playwright()) as p:
        browser = await launch_func(headless=True, args=["--no-sandbox"])
        
        context = await browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={"width": 1920, "height": 1080},
            locale="es-CL",
            timezone_id="America/Santiago"
        )
        page = await context.new_page()
        await stealth_async(page)

        print("🌐 Cargando página principal para obtener token CSRF...")
        await page.goto(BASE_URL, wait_until="networkidle")
        await asyncio.sleep(random.uniform(2, 5))

        # Intento 1: Selector directo
        token = await page.eval_on_selector('input[name="csrfToken"]', "el => el?.value")

        # Intento 2: Regex en HTML completo
        if not token:
            content = await page.content()
            m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
            if m:
                token = m.group(1)
                print("   ✅ Token recuperado con regex")

        if not token:
            print("❌ No se pudo obtener token CSRF. El sitio puede tener protección fuerte.")
            await browser.close()
            return

        print("✅ Token obtenido. Consultando API...")

        await asyncio.sleep(random.uniform(1, 3))

        response = await page.request.post(
            API_URL,
            data={"gameId": GAME_ID, "drawId": DRAW_ID, "csrfToken": token},
            headers={"x-requested-with": "XMLHttpRequest"}
        )

        if response.status != 200:
            print(f"❌ Error HTTP {response.status}")
            print(await response.text())
            await browser.close()
            return

        try:
            json_data = await response.json()
        except:
            print("❌ Respuesta no es JSON válido")
            print(await response.text())
            await browser.close()
            return

        # Guardar JSON bonito
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)

        print(f"💾 Datos guardados en: {OUTPUT_FILE}")
        print("\n📄 Ejemplo de contenido:")
        print(json.dumps(json_data, indent=2)[:1000] + ("..." if len(json.dumps(json_data)) > 1000 else ""))

        await browser.close()

    # Subir a GitHub automáticamente
    try:
        status = subprocess.check_output(["git", "status", "--porcelain"]).decode()
        if status:
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", f"🤖 Test scrape Loto #{DRAW_ID} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 Cambios subidos a GitHub!")
        else:
            print("✅ No hay cambios nuevos.")
    except Exception as e:
        print(f"⚠️ Error al subir a GitHub: {e}")

if __name__ == "__main__":
    asyncio.run(main())