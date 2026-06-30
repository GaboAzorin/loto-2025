# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-06-30 08:52:32

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
| ('LOTO3', 'oraculo_neural_v3') |                        7.291 |                       43.33 |                            16 |                  0.438 |
| ('LOTO3', 'oraculo_neural_v4') |                       21.11  |                       66.67 |                            24 |                  0.75  |
| ('LOTO4', 'oraculo_neural_v3') |                        1.429 |                       20    |                            14 |                  1     |
| ('LOTO4', 'oraculo_neural_v4') |                        0     |                        0    |                            14 |                  0.071 |
| ('RACHA', 'oraculo_neural_v3') |                       17.812 |                       60    |                            16 |                  5     |
| ('RACHA', 'oraculo_neural_v4') |                       13.125 |                       15    |                            16 |                  4.562 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23996 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23991 |            66.67 |          2 |
| RACHA   | oraculo_neural_v3 |             10295 |            60    |          2 |
| RACHA   | oraculo_neural_v3 |             10300 |            60    |          8 |
| LOTO3   | oraculo_neural_v3 |             23996 |            43.33 |          2 |
| RACHA   | oraculo_neural_v3 |             10296 |            40    |          7 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23990 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |