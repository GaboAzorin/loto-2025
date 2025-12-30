import pandas as pd
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', '..', 'data')
CSV_FILE = os.path.join(DATA_DIR, "LOTO_SIMULACIONES.csv")
REPORT_FILE = os.path.join(BASE_DIR, '..', '..', 'COMPARATIVA_MODELOS.md')

def generar_reporte_markdown():
    if not os.path.exists(CSV_FILE): return
    
    df = pd.read_csv(CSV_FILE)
    df_audit = df[df['estado'] == 'AUDITADO'].copy()
    if df_audit.empty: return

    # Filtramos solo los oráculos neurales
    df_models = df_audit[df_audit['algoritmo'].str.contains('oraculo_neural', na=False)]
    
    # 1. Cálculo de métricas estándar
    reporte = df_models.groupby(['juego', 'algoritmo']).agg({
        'score_afinidad': ['mean', 'max', 'count'],
        'aciertos': 'mean'
    }).round(3)

    # 2. Detección de Silenciamiento (Relación de Presencia)
    # Si v4 tiene muchos menos registros que v3, el filtro cognitivo lo está matando.
    counts = df_models.groupby(['juego', 'algoritmo']).size().unstack(fill_value=0)
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# 📊 Auditoría de Modelos: v3 vs v4\n")
        f.write(f"Actualizado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 🌡️ Alerta de Silenciamiento (Salud del Filtro)\n")
        for juego in counts.index:
            v3_c = counts.get('oraculo_neural_v3', {}).get(juego, 0)
            v4_c = counts.get('oraculo_neural_v4', {}).get(juego, 0)
            
            if v4_c < (v3_c * 0.5) and v3_c > 0:
                f.write(f"- ⚠️ **{juego}**: v4 está siendo 'silenciado'. Solo el {round((v4_c/v3_c)*100)}% de sus ideas pasan el filtro cognitivo.\n")
            elif v4_c == 0 and v3_c > 0:
                f.write(f"- 🚨 **{juego}**: v4 está TOTALMENTE bloqueado por la morfología actual.\n")
            else:
                f.write(f"- ✅ **{juego}**: v4 tiene una tasa de aceptación saludable.\n")
        
        f.write("\n## 📈 Resumen de Rendimiento\n")
        f.write(reporte.to_markdown() + "\n\n")
        
        f.write("## 🏆 Top 5 Mejores Aciertos (Histórico)\n")
        top_5 = df_models.sort_values('score_afinidad', ascending=False).head(10)
        f.write(top_5[['juego', 'algoritmo', 'sorteo_objetivo', 'score_afinidad', 'aciertos']].to_markdown(index=False))

if __name__ == "__main__":
    generar_reporte_markdown()