import os
import zipfile
import tkinter as tk
from tkinter import filedialog
from datetime import datetime

# CONFIGURACIÓN
LIMITE_MB = 100
BYTES_LIMITE = LIMITE_MB * 1024 * 1024  # 100 MB en bytes

def obtener_lista_archivos(ruta_origen):
    """Recorre la carpeta y retorna una lista de todos los archivos (sin .pkl)"""
    lista_archivos = []
    for carpeta_actual, _, archivos in os.walk(ruta_origen):
        for archivo in archivos:
            if archivo.lower().endswith('.pkl'):
                continue
            
            ruta_completa = os.path.join(carpeta_actual, archivo)
            ruta_relativa = os.path.relpath(ruta_completa, ruta_origen)
            peso = os.path.getsize(ruta_completa)
            
            lista_archivos.append({
                'ruta_completa': ruta_completa,
                'ruta_relativa': ruta_relativa,
                'peso': peso
            })
    return lista_archivos

def comprimir_por_lotes():
    # 1. Interfaz gráfica oculta
    root = tk.Tk()
    root.withdraw()

    print("Abriendo explorador...")
    ruta_seleccionada = filedialog.askdirectory(title="Selecciona la carpeta a comprimir")
    
    if not ruta_seleccionada:
        print("Cancelado.")
        return

    ruta_seleccionada = os.path.normpath(ruta_seleccionada)
    nombre_carpeta = os.path.basename(ruta_seleccionada)
    directorio_padre = os.path.dirname(ruta_seleccionada)
    
    # Timestamp: Año-Mes-Dia-Hora-Minuto
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    nombre_base = f"{timestamp}-{nombre_carpeta}"

    print(f"Analizando archivos en: {ruta_seleccionada}...")
    
    # 2. Obtener todos los archivos válidos
    archivos_a_procesar = obtener_lista_archivos(ruta_seleccionada)
    
    if not archivos_a_procesar:
        print("No se encontraron archivos válidos (o solo había .pkl).")
        return

    # 3. Lógica de Lotes (Batching)
    numero_parte = 1
    peso_actual_lote = 0
    
    # Función auxiliar para crear el nombre del zip
    def get_zip_path(num):
        nombre = f"{nombre_base}_parte{num}.zip"
        return os.path.join(directorio_padre, nombre)

    # Abrimos el primer ZIP
    ruta_zip_actual = get_zip_path(numero_parte)
    zip_actual = zipfile.ZipFile(ruta_zip_actual, 'w', zipfile.ZIP_DEFLATED)
    
    print(f"Creando Parte {numero_parte}...")

    for item in archivos_a_procesar:
        peso_archivo = item['peso']
        
        # VERIFICACIÓN: ¿Cabe este archivo en el lote actual?
        # Si (peso_actual + nuevo_archivo) supera el límite Y el lote no está vacío
        # entonces cerramos y abrimos uno nuevo.
        if (peso_actual_lote + peso_archivo > BYTES_LIMITE) and (peso_actual_lote > 0):
            # Cerrar el actual
            zip_actual.close()
            print(f" -> Parte {numero_parte} finalizada ({peso_actual_lote / (1024*1024):.2f} MB)")
            
            # Iniciar nuevo lote
            numero_parte += 1
            peso_actual_lote = 0
            ruta_zip_actual = get_zip_path(numero_parte)
            zip_actual = zipfile.ZipFile(ruta_zip_actual, 'w', zipfile.ZIP_DEFLATED)
            print(f"Creando Parte {numero_parte}...")

        # Escribir archivo en el ZIP actual
        zip_actual.write(item['ruta_completa'], item['ruta_relativa'])
        peso_actual_lote += peso_archivo

    # 4. Cerrar el último ZIP que haya quedado abierto
    zip_actual.close()
    print(f" -> Parte {numero_parte} finalizada ({peso_actual_lote / (1024*1024):.2f} MB)")

    print("-" * 40)
    print(f"✅ Proceso terminado.")
    print(f"📦 Total de partes creadas: {numero_parte}")
    print(f"📂 Ubicación: {directorio_padre}")
    print("-" * 40)

if __name__ == "__main__":
    try:
        comprimir_por_lotes()
    except Exception as e:
        print(f"Error: {e}")
    input("\nPresiona Enter para salir...")