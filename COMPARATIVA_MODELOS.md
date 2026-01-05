# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-05 03:23:21

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 2% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 20% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 14% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 6% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.564 |                       10    |                           153 |                  1.935 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.553 |                        0.83 |                             3 |                  0.667 |
| ('LOTO3', 'oraculo_neural_v3') |                       26.639 |                       66.67 |                           246 |                  0.919 |
| ('LOTO3', 'oraculo_neural_v4') |                       23.606 |                      100    |                            49 |                  0.98  |
| ('LOTO4', 'oraculo_neural_v3') |                        0.568 |                       50    |                           229 |                  0.459 |
| ('LOTO4', 'oraculo_neural_v4') |                        0     |                        0    |                            32 |                  0.594 |
| ('RACHA', 'oraculo_neural_v3') |                       11.117 |                       60    |                           197 |                  4.822 |
| ('RACHA', 'oraculo_neural_v4') |                       14.545 |                       40    |                            11 |                  5.273 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23948 |           100    |          3 |
| LOTO3   | oraculo_neural_v4 |             23961 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |