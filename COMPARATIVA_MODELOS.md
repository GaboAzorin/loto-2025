# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-15 18:34:35

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO3', 'oraculo_neural_v3') |                        5.278 |                       33.33 |                            12 |                  0.333 |
| ('LOTO3', 'oraculo_neural_v4') |                       19.332 |                       66.67 |                            20 |                  0.65  |
| ('LOTO4', 'oraculo_neural_v3') |                        0     |                        0    |                            10 |                  0.9   |
| ('LOTO4', 'oraculo_neural_v4') |                        0     |                        0    |                            10 |                  0     |
| ('RACHA', 'oraculo_neural_v3') |                       16.538 |                       60    |                            13 |                  4.769 |
| ('RACHA', 'oraculo_neural_v4') |                       13.462 |                       15    |                            13 |                  4.308 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23991 |            66.67 |          2 |
| RACHA   | oraculo_neural_v3 |             10295 |            60    |          2 |
| RACHA   | oraculo_neural_v3 |             10296 |            40    |          7 |
| LOTO3   | oraculo_neural_v3 |             23992 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |