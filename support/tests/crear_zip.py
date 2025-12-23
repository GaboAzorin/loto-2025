import os
import zipfile
import tkinter as tk
from tkinter import filedialog
from datetime import datetime

# --- CONFIGURACIÓN ESTRICTA GEMINI ---
LIMITE_MB = 95             # Dejamos un margen de seguridad (Max es 100)
LIMITE_ARCHIVOS = 10       # Límite estricto de archivos dentro de un ZIP
BYTES_LIMITE = LIMITE_MB * 1024 * 1024 

def comprimir_para_gemini():
    root = tk.Tk()
    root.withdraw()

    print("--- GENERADOR DE CONTEXTO (OPTIMIZADO PARA GEMINI) ---")
    print(f"Reglas: Máx {LIMITE_ARCHIVOS} archivos por ZIP o {LIMITE_MB} MB.")
    
    ruta_seleccionada = filedialog.askdirectory(title="Selecciona tu carpeta de proyecto")
    
    if not ruta_seleccionada:
        return

    ruta_seleccionada = os.path.normpath(ruta_seleccionada)
    nombre_carpeta = os.path.basename(ruta_seleccionada)
    directorio_padre = os.path.dirname(ruta_seleccionada)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    nombre_base = f"{timestamp}-{nombre_carpeta}"

    print(f"Analizando: {ruta_seleccionada} ...\n")
    
    archivos_para_zip = []

    # 1. ESCANEO Y FILTRADO
    for carpeta_actual, subcarpetas, archivos in os.walk(ruta_seleccionada):
        # Filtros de carpetas basura
        if '.git' in subcarpetas: subcarpetas.remove('.git')
        if '__pycache__' in subcarpetas: subcarpetas.remove('__pycache__')
        
        for archivo in archivos:
            # Filtro PKL
            if archivo.lower().endswith('.pkl'):
                continue
            
            # Filtro archivos basura del sistema
            if archivo == '.DS_Store' or archivo.startswith('~$'):
                continue

            ruta_completa = os.path.join(carpeta_actual, archivo)
            peso = os.path.getsize(ruta_completa)
            ruta_relativa = os.path.relpath(ruta_completa, ruta_seleccionada)
            
            archivos_para_zip.append({
                'ruta_completa': ruta_completa,
                'ruta_relativa': ruta_relativa,
                'peso': peso
            })

    # Ordenamos por importancia (opcional, pero ayuda a que los archivos raíz queden en el zip 1)
    # Ponemos primero los .py y .csv, luego el resto
    archivos_para_zip.sort(key=lambda x: (not x['ruta_relativa'].endswith('.py'), x['ruta_relativa']))

    total_archivos = len(archivos_para_zip)
    print(f"Total archivos válidos encontrados: {total_archivos}")
    
    if total_archivos == 0:
        print("No hay archivos para procesar.")
        return

    # 2. GENERACIÓN DE LOTES (BATCHING)
    numero_parte = 1
    
    # Contadores del lote actual
    peso_actual_lote = 0
    archivos_en_lote_actual = 0
    
    def get_zip_path(num):
        return os.path.join(directorio_padre, f"{nombre_base}_parte{num}.zip")

    ruta_zip_actual = get_zip_path(numero_parte)
    zip_actual = zipfile.ZipFile(ruta_zip_actual, 'w', zipfile.ZIP_DEFLATED)
    
    print("\nCreando paquetes...")

    for item in archivos_para_zip:
        peso_archivo = item['peso']
        
        # --- LÓGICA DE CORTE DOBLE ---
        condicion_peso = (peso_actual_lote + peso_archivo > BYTES_LIMITE)
        condicion_cantidad = (archivos_en_lote_actual >= LIMITE_ARCHIVOS)
        
        # Si se cumple CUALQUIERA de las dos, cerramos y abrimos nuevo
        if (condicion_peso or condicion_cantidad) and archivos_en_lote_actual > 0:
            zip_actual.close()
            print(f"📦 {os.path.basename(ruta_zip_actual)} guardado. (Archivos: {archivos_en_lote_actual} | Peso: {peso_actual_lote/1024:.2f} KB)")
            
            numero_parte += 1
            peso_actual_lote = 0
            archivos_en_lote_actual = 0
            ruta_zip_actual = get_zip_path(numero_parte)
            zip_actual = zipfile.ZipFile(ruta_zip_actual, 'w', zipfile.ZIP_DEFLATED)

        # Escribir en el ZIP actual
        zip_actual.write(item['ruta_completa'], item['ruta_relativa'])
        peso_actual_lote += peso_archivo
        archivos_en_lote_actual += 1

    # Cerrar el último
    zip_actual.close()
    print(f"📦 {os.path.basename(ruta_zip_actual)} guardado. (Archivos: {archivos_en_lote_actual} | Peso: {peso_actual_lote/1024:.2f} KB)")

    print("-" * 50)
    print(f"✅ ¡LISTO! Se generaron {numero_parte} archivos ZIP.")
    print("Cada uno cumple estrictamente con tener máx 10 archivos.")
    print(f"Ubicación: {directorio_padre}")
    print("-" * 50)

if __name__ == "__main__":
    comprimir_para_gemini()
    input("\nPresiona Enter para salir...")