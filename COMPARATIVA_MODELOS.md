# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-14 23:04:38

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO3', 'oraculo_neural_v3') |                        2     |                       10    |                            10 |                  0.2   |
| ('LOTO3', 'oraculo_neural_v4') |                       20.369 |                       66.67 |                            18 |                  0.611 |
| ('LOTO4', 'oraculo_neural_v3') |                        0     |                        0    |                             9 |                  0.889 |
| ('LOTO4', 'oraculo_neural_v4') |                        0     |                        0    |                             9 |                  0     |
| ('RACHA', 'oraculo_neural_v3') |                       17.5   |                       60    |                            12 |                  4.75  |
| ('RACHA', 'oraculo_neural_v4') |                       14.167 |                       15    |                            12 |                  4.25  |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23991 |            66.67 |          2 |
| RACHA   | oraculo_neural_v3 |             10295 |            60    |          2 |
| RACHA   | oraculo_neural_v3 |             10296 |            40    |          7 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23990 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |