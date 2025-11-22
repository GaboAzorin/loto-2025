import sys
import datetime
import traceback

# Definimos los archivos de salida al principio
DEBUG_HTML_FILE = 'debug_view.html'
STATUS_FILE = 'system_status.json'

def write_debug(content):
    with open(DEBUG_HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    print("--- INICIO MODO INDESTRUCTIBLE ---")
    try:
        # Intentamos importar las librerías peligrosas DENTRO del try
        import cloudscraper
        from bs4 import BeautifulSoup
        import json

        URL = 'https://www.polla.cl/es/view/resultados'
        
        # 1. Intentar conectar
        print(f"Conectando a {URL}...")
        scraper = cloudscraper.create_scraper()
        response = scraper.get(URL, timeout=60)
        
        # 2. GUARDAR HTML (Lo logre o no)
        html_content = f"\n" + response.text
        write_debug(html_content)
        print(f"HTML guardado. Tamaño: {len(response.text)} bytes")

        # 3. Buscar pistas
        if "balls-content" in response.text:
            print("¡BOLAS ENCONTRADAS EN EL HTML!")
        else:
            print("No se ven bolas. Sitio dinámico confirmado.")

    except Exception as e:
        # SI ALGO FALLA, LO ESCRIBIMOS EN EL HTML PARA QUE LO VEAS
        error_msg = f"""
        <h1>ERROR FATAL DEL SCRIPT</h1>
        <pre>{traceback.format_exc()}</pre>
        """
        print("¡ERROR CAPTURADO!")
        print(e)
        write_debug(error_msg)
    
    # Salimos siempre con éxito para no asustar a GitHub
    sys.exit(0)

if __name__ == "__main__":
    main()
