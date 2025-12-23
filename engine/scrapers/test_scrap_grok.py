import asyncio
import json
import os
import random
import re
import subprocess
from datetime import datetime

from playwright.async_api import async_playwright
from playwright_stealth import Stealth  # ← Este es el import correcto para v2.0+

# Constantes
BASE_URL = "https://www.polla.cl/es/view/resultados"
API_URL = "https://www.polla.cl/es/get/draw/results"
GAME_ID = "5271"   # Loto clásico
DRAW_ID = 5200     # Sorteo de prueba

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "test")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"loto_sorteo_{DRAW_ID}.json")

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
]

async def main():
    print(f"\n🕷️  TEST SCRAPER: Consultando sorteo Loto #{DRAW_ID}")

    stealth = Stealth()  # Puedes personalizar si quieres: Stealth(init_scripts_only=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

        context = await browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={"width": 1920, "height": 1080},
            locale="es-CL",
            timezone_id="America/Santiago"
        )

        # Aplicamos stealth al context → afecta todas las páginas que se creen
        await stealth.apply_stealth_async(context)

        page = await context.new_page()

        print("🌐 Cargando página principal para obtener token CSRF...")
        await page.goto(BASE_URL, wait_until="networkidle")
        await asyncio.sleep(random.uniform(2, 5))

        # Intento 1: Selector directo
        token = await page.eval_on_selector('input[name="csrfToken"]', "el => el?.value")

        # Intento 2: Regex fallback
        if not token:
            print("   ⚠️ Token no encontrado en DOM. Intentando regex...")
            content = await page.content()
            m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
            if m:
                token = m.group(1)
                print("   ✅ Token recuperado con regex")

        if not token:
            print("❌ No se pudo obtener token CSRF.")
            await browser.close()
            return

        print("✅ Token obtenido. Consultando API...")

        await asyncio.sleep(random.uniform(0.8, 2.2))

        response = await page.request.post(
            API_URL,
            data={
                "gameId": GAME_ID,
                "drawId": str(DRAW_ID),  # Aseguramos que sea string
                "csrfToken": token
            },
            headers={"x-requested-with": "XMLHttpRequest"}
        )

        if response.status != 200:
            print(f"❌ Error HTTP {response.status}")
            print(await response.text())
            await browser.close()
            return

        try:
            json_data = await response.json()
        except Exception as e:
            print(f"❌ Respuesta no es JSON válido: {e}")
            await browser.close()
            return

        # Guardar bonito
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)

        print(f"💾 Datos guardados en: {os.path.relpath(OUTPUT_FILE, os.getcwd())}")
        print("\n📄 Vista previa (primeros 800 chars):")
        print(json.dumps(json_data, indent=2)[:800] + "..." if len(json.dumps(json_data)) > 800 else "")

        await browser.close()

    # Commit & push automático
    try:
        status = subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()
        if status:
            subprocess.run(["git", "add", "."], check=True)
            commit_msg = f"🤖 Test scrape Loto #{DRAW_ID} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            subprocess.run(["git", "push"], check=True)
            print("🚀 Cambios subidos a GitHub exitosamente!")
        else:
            print("✅ No hay cambios nuevos para subir.")
    except Exception as e:
        print(f"⚠️ Error al subir a GitHub: {e}")

if __name__ == "__main__":
    asyncio.run(main())