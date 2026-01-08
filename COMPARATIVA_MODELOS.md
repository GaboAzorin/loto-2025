# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-08 18:15:26

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 3% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 26% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 20% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 8% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.508 |                       10    |                           154 |                  1.929 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.415 |                        0.83 |                             4 |                  0.5   |
| ('LOTO3', 'oraculo_neural_v3') |                       25.087 |                       66.67 |                           266 |                  0.868 |
| ('LOTO3', 'oraculo_neural_v4') |                       18.937 |                      100    |                            69 |                  0.812 |
| ('LOTO4', 'oraculo_neural_v3') |                        0.772 |                       50    |                           246 |                  0.476 |
| ('LOTO4', 'oraculo_neural_v4') |                       11.633 |                       50    |                            49 |                  1.184 |
| ('RACHA', 'oraculo_neural_v3') |                       11.256 |                       60    |                           203 |                  4.833 |
| ('RACHA', 'oraculo_neural_v4') |                       14.412 |                       40    |                            17 |                  5.294 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23948 |           100    |          3 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23955 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |