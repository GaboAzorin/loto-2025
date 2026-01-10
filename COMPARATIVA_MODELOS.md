# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-10 00:52:13

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 3% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 27% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 21% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 9% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.511 |                       10    |                           155 |                  1.929 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.498 |                        0.83 |                             5 |                  0.6   |
| ('LOTO3', 'oraculo_neural_v3') |                       24.968 |                       66.67 |                           269 |                  0.866 |
| ('LOTO3', 'oraculo_neural_v4') |                       19.074 |                      100    |                            72 |                  0.806 |
| ('LOTO4', 'oraculo_neural_v3') |                        0.766 |                       50    |                           248 |                  0.476 |
| ('LOTO4', 'oraculo_neural_v4') |                       11.176 |                       50    |                            51 |                  1.157 |
| ('RACHA', 'oraculo_neural_v3') |                       11.415 |                       60    |                           205 |                  4.839 |
| ('RACHA', 'oraculo_neural_v4') |                       13.947 |                       40    |                            19 |                  5.211 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23948 |           100    |          3 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |