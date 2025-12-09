import asyncio
import json
import os
from playwright.async_api import async_playwright

# --- OBJETIVOS DE LA MISIÓN ---
TARGETS = [
    {"name": "RACHA",  "gameId": "5272", "drawId": 10222},
    {"name": "LOTO3",  "gameId": "2181", "drawId": 23880},
    {"name": "LOTO4",  "gameId": "5270", "drawId": 11489}
]

BASE_URL = "https://www.polla.cl/es/view/resultados"
API_URL = "https://www.polla.cl/es/get/draw/results"

async def run():
    print("🛰️ INICIANDO MISIÓN DE RECONOCIMIENTO (SCOUTING)...")
    
    async with async_playwright() as p:
        # Usamos navegador headless pero con firma real
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 1. INFILTRACIÓN: Obtener Cookies y Token CSRF
            print(f"🔌 Conectando a {BASE_URL} para obtener credenciales...")
            await page.goto(BASE_URL, wait_until="domcontentloaded")
            await asyncio.sleep(2) # Pausa humana

            # Extracción del Token (Misma técnica blindada que tu scraper actual)
            token = await page.evaluate("document.querySelector('input[name=\"csrfToken\"]')?.value")
            if not token: 
                content = await page.content()
                import re
                m = re.search(r'csrfToken["\']\s*[:=]\s*["\']([a-zA-Z0-9]+)["\']', content)
                if m: token = m.group(1)
            
            if not token:
                raise Exception("❌ No se pudo capturar el Token CSRF. Polla ha mejorado sus defensas.")
            
            print(f"✅ Token capturado: {token[:10]}... (OK)")

            # 2. EXTRACCIÓN QUIRÚRGICA
            for target in TARGETS:
                print(f"\n🔎 Buscando datos de {target['name']} (Sorteo #{target['drawId']})...")
                
                # Simulamos la petición AJAX exacta que hace el sitio
                response = await page.request.post(
                    API_URL, 
                    data={
                        "gameId": target['gameId'], 
                        "drawId": target['drawId'], 
                        "csrfToken": token
                    }, 
                    headers={"x-requested-with": "XMLHttpRequest"}
                )
                
                if response.status == 200:
                    try:
                        json_data = await response.json()
                        
                        # Validar si trajo datos
                        if not json_data or not json_data.get('drawNumber'):
                            print(f"⚠️ Alerta: El JSON de {target['name']} llegó vacío o inválido.")
                            continue

                        # 3. GUARDADO DE LA MUESTRA
                        filename = f"MUESTRA_{target['name']}.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(json_data, f, indent=4, ensure_ascii=False)
                        
                        print(f"📦 ¡ÉXITO! Datos guardados en '{filename}'")
                        
                    except Exception as e:
                        print(f"❌ Error procesando JSON de {target['name']}: {e}")
                else:
                    print(f"❌ Error HTTP {response.status} al consultar {target['name']}")
                
                # Pausa táctica entre peticiones para no levantar sospechas
                await asyncio.sleep(1.5)

        except Exception as e:
            print(f"🔥 Falla crítica en la misión: {e}")
        
        await browser.close()
        print("\n🏁 Misión finalizada.")

if __name__ == "__main__":
    asyncio.run(run())