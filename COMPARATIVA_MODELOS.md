# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-03 06:16:56

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 1% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 18% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 12% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 4% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.627 |                       10    |                           152 |                  1.947 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.415 |                        0.83 |                             2 |                  0.5   |
| ('LOTO3', 'oraculo_neural_v3') |                       26.944 |                       66.67 |                           240 |                  0.925 |
| ('LOTO3', 'oraculo_neural_v4') |                       23.876 |                      100    |                            43 |                  0.977 |
| ('LOTO4', 'oraculo_neural_v3') |                        0.578 |                       50    |                           225 |                  0.462 |
| ('LOTO4', 'oraculo_neural_v4') |                        0     |                        0    |                            28 |                  0.536 |
| ('RACHA', 'oraculo_neural_v3') |                       10.674 |                       60    |                           193 |                  4.824 |
| ('RACHA', 'oraculo_neural_v4') |                       15.714 |                       40    |                             7 |                  5.286 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23948 |           100    |          3 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |