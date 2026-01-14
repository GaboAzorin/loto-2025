# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-14 17:00:43

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **LOTO4**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO3', 'oraculo_neural_v3') |                        0     |                        0    |                             1 |                  0     |
| ('LOTO3', 'oraculo_neural_v4') |                       29.627 |                       33.33 |                             9 |                  0.889 |
| ('LOTO4', 'oraculo_neural_v3') |                        0     |                        0    |                             9 |                  0.889 |
| ('LOTO4', 'oraculo_neural_v4') |                        0     |                        0    |                             9 |                  0     |
| ('RACHA', 'oraculo_neural_v3') |                       15.455 |                       60    |                            11 |                  4.545 |
| ('RACHA', 'oraculo_neural_v4') |                       14.091 |                       15    |                            11 |                  4.091 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10295 |            60    |          2 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| LOTO3   | oraculo_neural_v4 |             23989 |            33.33 |          1 |
| RACHA   | oraculo_neural_v4 |             10295 |            15    |          4 |