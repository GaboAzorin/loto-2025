# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-04 18:15:12

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 1% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 18% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 13% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 4% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.627 |                       10    |                           152 |                  1.947 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.415 |                        0.83 |                             2 |                  0.5   |
| ('LOTO3', 'oraculo_neural_v3') |                       26.97  |                       66.67 |                           241 |                  0.925 |
| ('LOTO3', 'oraculo_neural_v4') |                       23.561 |                      100    |                            44 |                  0.977 |
| ('LOTO4', 'oraculo_neural_v3') |                        0.575 |                       50    |                           226 |                  0.465 |
| ('LOTO4', 'oraculo_neural_v4') |                        0     |                        0    |                            29 |                  0.552 |
| ('RACHA', 'oraculo_neural_v3') |                       10.696 |                       60    |                           194 |                  4.82  |
| ('RACHA', 'oraculo_neural_v4') |                       15.625 |                       40    |                             8 |                  5.375 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23948 |           100    |          3 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |