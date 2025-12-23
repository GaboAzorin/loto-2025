import os
import zipfile
import tkinter as tk
from tkinter import filedialog
from datetime import datetime

# CONFIGURACIÓN
LIMITE_MB = 100
BYTES_LIMITE = LIMITE_MB * 1024 * 1024 

def formatear_tamano(bytes_size):
    """Convierte bytes a MB o KB para que sea legible"""
    for unidad in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unidad}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def comprimir_inteligente():
    root = tk.Tk()
    root.withdraw()

    print("--- RESPALDO INTELIGENTE ---")
    ruta_seleccionada = filedialog.askdirectory(title="Selecciona la carpeta")
    
    if not ruta_seleccionada:
        return

    ruta_seleccionada = os.path.normpath(ruta_seleccionada)
    nombre_carpeta = os.path.basename(ruta_seleccionada)
    directorio_padre = os.path.dirname(ruta_seleccionada)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    
    # Nombre base común
    nombre_base = f"{timestamp}-{nombre_carpeta}"

    print(f"Analizando: {ruta_seleccionada} ...\n")
    
    todos_los_archivos = []
    archivos_para_zip = []

    # 1. ESCANEO Y REPORTE
    for carpeta_actual, subcarpetas, archivos in os.walk(ruta_seleccionada):
        if '.git' in subcarpetas: subcarpetas.remove('.git') # Ignorar carpeta git
        
        for archivo in archivos:
            ruta_completa = os.path.join(carpeta_actual, archivo)
            peso = os.path.getsize(ruta_completa)
            ruta_relativa = os.path.relpath(ruta_completa, ruta_seleccionada)
            
            es_pkl = archivo.lower().endswith('.pkl')
            
            todos_los_archivos.append({
                'nombre': archivo,
                'ruta_relativa': ruta_relativa,
                'ruta_completa': ruta_completa,
                'peso': peso,
                'excluido': es_pkl
            })

            if not es_pkl:
                archivos_para_zip.append({
                    'ruta_completa': ruta_completa,
                    'ruta_relativa': ruta_relativa,
                    'peso': peso
                })

    # Ordenar y mostrar reporte
    todos_los_archivos.sort(key=lambda x: x['peso'], reverse=True)

    print("="*60)
    print(f"{'PESO':<12} | {'ESTADO':<10} | {'NOMBRE DEL ARCHIVO'}")
    print("="*60)

    for item in todos_los_archivos:
        peso_fmt = formatear_tamano(item['peso'])
        estado = "[EXCLUIDO]" if item['excluido'] else "   OK   "
        if item['peso'] > BYTES_LIMITE and not item['excluido']:
            estado = "⚠️ GIGANTE"
        
        print(f"{peso_fmt:<12} | {estado:<10} | {item['ruta_relativa']}")

    print("="*60)
    print(f"Archivos válidos a comprimir: {len(archivos_para_zip)}")
    print("-" * 60)
    
    if not archivos_para_zip:
        print("No hay archivos válidos para comprimir.")
        return

    print("\nIniciando compresión...")

    # 2. COMPRESIÓN POR LOTES
    numero_parte = 1
    peso_actual_lote = 0
    
    def get_zip_path(num):
        return os.path.join(directorio_padre, f"{nombre_base}_parte{num}.zip")

    ruta_zip_actual = get_zip_path(numero_parte)
    zip_actual = zipfile.ZipFile(ruta_zip_actual, 'w', zipfile.ZIP_DEFLATED)
    
    for item in archivos_para_zip:
        peso_archivo = item['peso']
        
        # Si se pasa del límite, cerramos y abrimos uno nuevo
        if (peso_actual_lote + peso_archivo > BYTES_LIMITE) and (peso_actual_lote > 0):
            zip_actual.close()
            print(f"📦 {os.path.basename(ruta_zip_actual)} guardado ({formatear_tamano(peso_actual_lote)})")
            
            numero_parte += 1
            peso_actual_lote = 0
            ruta_zip_actual = get_zip_path(numero_parte)
            zip_actual = zipfile.ZipFile(ruta_zip_actual, 'w', zipfile.ZIP_DEFLATED)

        zip_actual.write(item['ruta_completa'], item['ruta_relativa'])
        peso_actual_lote += peso_archivo

    zip_actual.close()
    print(f"📦 {os.path.basename(ruta_zip_actual)} guardado ({formatear_tamano(peso_actual_lote)})")
    
    # 3. RENOMBRADO INTELIGENTE (Si solo hubo 1 parte)
    if numero_parte == 1:
        ruta_original = get_zip_path(1)
        ruta_final_limpia = os.path.join(directorio_padre, f"{nombre_base}.zip")
        
        try:
            # Si existiera uno previo con el mismo nombre exacto, lo borramos para evitar error
            if os.path.exists(ruta_final_limpia):
                os.remove(ruta_final_limpia)
                
            os.rename(ruta_original, ruta_final_limpia)
            print(f"\n✨ Como todo cupo en un solo archivo, se renombró a:")
            print(f"📂 {os.path.basename(ruta_final_limpia)}")
        except Exception as e:
            print(f"No se pudo renombrar el archivo único: {e}")
    else:
        print(f"\n✅ Se generaron {numero_parte} partes debido al peso total.")

    print("\nPROCESO FINALIZADO.")

if __name__ == "__main__":
    comprimir_inteligente()
    input("\nPresiona Enter para salir...")