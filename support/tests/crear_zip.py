import os
import zipfile
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import pyperclip

# --- CONFIGURACIÓN ESTRICTA GEMINI ---
LIMITE_MB = 95             # Dejamos un margen de seguridad (Max es 100)
LIMITE_ARCHIVOS = 10       # Límite estricto de archivos dentro de un ZIP
BYTES_LIMITE = LIMITE_MB * 1024 * 1024 

def comprimir_para_gemini():
    root = tk.Tk()
    root.withdraw()

    print("--- GENERADOR DE CONTEXTO (OPTIMIZADO PARA GEMINI) ---")
    print(f"Reglas: Máx {LIMITE_ARCHIVOS} archivos por ZIP o {LIMITE_MB} MB.")
    print("Filtro activo: Solo los últimos 10 archivos 'prediccion_*.json'")
    
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
    archivos_prediccion = [] # Lista temporal para las predicciones

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
            ruta_relativa = os.path.relpath(ruta_completa, ruta_seleccionada)
            peso = os.path.getsize(ruta_completa)
            mtime = os.path.getmtime(ruta_completa) # Necesario para ordenar por fecha

            item_archivo = {
                'ruta_completa': ruta_completa,
                'ruta_relativa': ruta_relativa,
                'peso': peso,
                'mtime': mtime
            }

            # --- LÓGICA DE FILTRADO DE PREDICCIONES ---
            # Si es una predicción json, la mandamos a la lista de espera
            if archivo.startswith("prediccion_") and archivo.endswith(".json"):
                archivos_prediccion.append(item_archivo)
            else:
                # Si es cualquier otro archivo, pasa directo
                archivos_para_zip.append(item_archivo)

    # 2. PROCESAMIENTO DE PREDICCIONES (SOLO LAS ÚLTIMAS 10)
    if archivos_prediccion:
        print(f"  -> Se encontraron {len(archivos_prediccion)} archivos de predicción.")
        # Ordenamos por fecha de modificación descendente (el más nuevo primero)
        archivos_prediccion.sort(key=lambda x: x['mtime'], reverse=True)
        # Tomamos solo los primeros 10
        top_10_predicciones = archivos_prediccion[:10]
        print(f"  -> Se conservarán solo los {len(top_10_predicciones)} más recientes.")
        # Los agregamos a la lista principal
        archivos_para_zip.extend(top_10_predicciones)

    # 3. ORDENAMIENTO FINAL
    # Ordenamos por importancia: .py y .csv primero, luego el resto
    archivos_para_zip.sort(key=lambda x: (not x['ruta_relativa'].endswith('.py'), x['ruta_relativa']))

    total_archivos = len(archivos_para_zip)
    print(f"Total archivos válidos finales a procesar: {total_archivos}")
    
    if total_archivos == 0:
        print("No hay archivos para procesar.")
        return

    # 4. GENERACIÓN DE LOTES (BATCHING)
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

    print("Además, ya está en tu portapapeles el texto de resumen del proyecto :)")
    
    texto_para_portapapeles = 'Arquitectura MLOps Serverless orientada a eventos ejecutada sobre GitHub Actions. El sistema implementa un pipeline ETL autónomo (Playwright) con reconstrucción temporal y manejo de concurrencia mediante colas asíncronas (UUID tickets) con consolidación batch para garantizar la integridad atómica de los datos (*_MAESTRO.csv).\nEl núcleo de inferencia opera mediante un ensamble dinámico (RandomForest, Cadenas de Markov, Heurísticas) orquestado por un algoritmo de votación ponderada (Consenso Meritocrático). Integra un ciclo de retroalimentación cerrado (RL-lite): el agente Juez calcula la función de pérdida sobre predicciones pasadas y el Entrenador ajusta los pesos sinápticos en loto_genome.json en tiempo de ejecución.'
    pyperclip.copy(texto_para_portapapeles)
    print(texto_para_portapapeles)

if __name__ == "__main__":
    comprimir_para_gemini()
    input("\nPresiona Enter para salir...")