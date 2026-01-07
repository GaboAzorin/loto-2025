# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-06 22:07:35

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 3% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 25% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 19% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 7% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.508 |                       10    |                           154 |                  1.929 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.415 |                        0.83 |                             4 |                  0.5   |
| ('LOTO3', 'oraculo_neural_v3') |                       25.17  |                       66.67 |                           263 |                  0.867 |
| ('LOTO3', 'oraculo_neural_v4') |                       19.343 |                      100    |                            66 |                  0.803 |
| ('LOTO4', 'oraculo_neural_v3') |                        0.7   |                       50    |                           243 |                  0.469 |
| ('LOTO4', 'oraculo_neural_v4') |                       12.391 |                       50    |                            46 |                  1.217 |
| ('RACHA', 'oraculo_neural_v3') |                       11.125 |                       60    |                           200 |                  4.835 |
| ('RACHA', 'oraculo_neural_v4') |                       15.714 |                       40    |                            14 |                  5.286 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23948 |           100    |          3 |
| LOTO3   | oraculo_neural_v4 |             23961 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |