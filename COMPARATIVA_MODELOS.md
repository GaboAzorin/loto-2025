# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-16 16:59:51

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        1.67  |                        1.67 |                             1 |                  2     |
| ('LOTO', 'oraculo_neural_v4')  |                        0     |                        0    |                             1 |                  0     |
| ('LOTO3', 'oraculo_neural_v3') |                        5.238 |                       33.33 |                            14 |                  0.357 |
| ('LOTO3', 'oraculo_neural_v4') |                       19.999 |                       66.67 |                            22 |                  0.727 |
| ('LOTO4', 'oraculo_neural_v3') |                        1.667 |                       20    |                            12 |                  1     |
| ('LOTO4', 'oraculo_neural_v4') |                        0     |                        0    |                            12 |                  0     |
| ('RACHA', 'oraculo_neural_v3') |                       15     |                       60    |                            15 |                  4.8   |
| ('RACHA', 'oraculo_neural_v4') |                       13     |                       15    |                            15 |                  4.467 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23991 |            66.67 |          2 |
| RACHA   | oraculo_neural_v3 |             10295 |            60    |          2 |
| RACHA   | oraculo_neural_v3 |             10296 |            40    |          7 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23990 |            33.33 |          1 |