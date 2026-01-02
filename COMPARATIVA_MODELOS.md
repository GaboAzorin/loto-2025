# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-02 18:03:00

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 1% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 14% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 12% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 3% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.627 |                       10    |                           152 |                  1.947 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.415 |                        0.83 |                             2 |                  0.5   |
| ('LOTO3', 'oraculo_neural_v3') |                       26.848 |                       66.67 |                           238 |                  0.92  |
| ('LOTO3', 'oraculo_neural_v4') |                       12.929 |                      100    |                            33 |                  0.727 |
| ('LOTO4', 'oraculo_neural_v3') |                        0.58  |                       50    |                           224 |                  0.464 |
| ('LOTO4', 'oraculo_neural_v4') |                        0     |                        0    |                            27 |                  0.519 |
| ('RACHA', 'oraculo_neural_v3') |                       10.681 |                       60    |                           191 |                  4.827 |
| ('RACHA', 'oraculo_neural_v4') |                       11     |                       15    |                             5 |                  4.8   |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23948 |           100    |          3 |
| LOTO3   | oraculo_neural_v3 |             23928 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |