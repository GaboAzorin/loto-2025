# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-06 18:16:57

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 2% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 24% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 19% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 7% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.564 |                       10    |                           153 |                  1.935 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.553 |                        0.83 |                             3 |                  0.667 |
| ('LOTO3', 'oraculo_neural_v3') |                       25.204 |                       66.67 |                           260 |                  0.869 |
| ('LOTO3', 'oraculo_neural_v4') |                       19.577 |                      100    |                            63 |                  0.81  |
| ('LOTO4', 'oraculo_neural_v3') |                        0.702 |                       50    |                           242 |                  0.471 |
| ('LOTO4', 'oraculo_neural_v4') |                       12.667 |                       50    |                            45 |                  1.222 |
| ('RACHA', 'oraculo_neural_v3') |                       11.106 |                       60    |                           199 |                  4.829 |
| ('RACHA', 'oraculo_neural_v4') |                       15.769 |                       40    |                            13 |                  5.385 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23948 |           100    |          3 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23961 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |