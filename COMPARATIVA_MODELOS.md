# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-16 06:18:40

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
| ('LOTO3', 'oraculo_neural_v3') |                        4.872 |                       33.33 |                            13 |                  0.308 |
| ('LOTO3', 'oraculo_neural_v4') |                       19.999 |                       66.67 |                            21 |                  0.667 |
| ('LOTO4', 'oraculo_neural_v3') |                        1.667 |                       20    |                            12 |                  1     |
| ('LOTO4', 'oraculo_neural_v4') |                        0     |                        0    |                            12 |                  0     |
| ('RACHA', 'oraculo_neural_v3') |                       15.714 |                       60    |                            14 |                  4.786 |
| ('RACHA', 'oraculo_neural_v4') |                       12.857 |                       15    |                            14 |                  4.357 |

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
| LOTO3   | oraculo_neural_v4 |             23990 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |