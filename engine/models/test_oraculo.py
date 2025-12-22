import os
import sys
import joblib
import pandas as pd
import numpy as np
from datetime import datetime

# Ajustar path para importar módulos locales si es necesario
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.append(current_dir)

print("🔍 --- DIAGNÓSTICO DE ORÁCULO NEURAL ---")

# 1. PRUEBA DE IMPORTACIÓN
print("\n1️⃣ Intentando importar OraculoNeural...")
try:
    from oraculo_neural import OraculoNeural
    print("   ✅ Importación exitosa.")
except Exception as e:
    print(f"   ❌ ERROR CRÍTICO DE IMPORTACIÓN: {e}")
    sys.exit(1)

# 2. PRUEBA DE ARCHIVOS
print("\n2️⃣ Verificando archivos de modelos (.pkl)...")
DATA_DIR = os.path.join(current_dir, '..', '..', 'data')
juegos = ["LOTO", "LOTO3", "LOTO4", "RACHA"]
for g in juegos:
    path = os.path.join(DATA_DIR, f'{g.lower()}_rf_model.pkl')
    exists = os.path.exists(path)
    status = "✅ Existe" if exists else "❌ FALTA"
    size = f"({os.path.getsize(path)/1024:.1f} KB)" if exists else ""
    print(f"   - {g}: {path} -> {status} {size}")

# 3. PRUEBA DE PREDICCIÓN (EL NÚCLEO)
print("\n3️⃣ Intentando cargar modelos y predecir...")
for g in juegos:
    print(f"\n   👉 Probando {g}...")
    try:
        # Instanciar
        oracle = OraculoNeural(g)
        
        # Verificar carga del modelo
        if oracle.model is None:
            print(f"      ⚠️ El modelo es NONE. Intentando cargar explícitamente...")
            # Forzamos carga manual para ver el error real
            try:
                oracle.model = joblib.load(oracle.model_file)
                print("      ✅ Carga manual exitosa.")
            except Exception as e_load:
                print(f"      ❌ ERROR CARGANDO .PKL: {e_load}")
                continue

        # Predecir
        fecha = datetime.now()
        pred = oracle.predecir(fecha_objetivo=fecha)
        
        if pred:
            print(f"      ✨ ÉXITO: Predicción generada: {pred}")
        else:
            print(f"      ⚠️ ALERTA: Predicción devolvió lista vacía []")
            
    except Exception as e:
        print(f"      🔥 EXCEPCIÓN NO CONTROLADA: {e}")

print("\n🏁 Diagnóstico finalizado.")