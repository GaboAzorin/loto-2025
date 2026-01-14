# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-14 00:55:44

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 4% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 30% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 23% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 13% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.455 |                       10    |                           156 |                  1.923 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.693 |                        1.67 |                             6 |                  0.833 |
| ('LOTO3', 'oraculo_neural_v3') |                       25.124 |                       66.67 |                           281 |                  0.868 |
| ('LOTO3', 'oraculo_neural_v4') |                       19.762 |                      100    |                            84 |                  0.81  |
| ('LOTO4', 'oraculo_neural_v3') |                        0.82  |                       50    |                           256 |                  0.48  |
| ('LOTO4', 'oraculo_neural_v4') |                       10     |                       50    |                            59 |                  1.102 |
| ('RACHA', 'oraculo_neural_v3') |                       11.643 |                       60    |                           213 |                  4.822 |
| ('RACHA', 'oraculo_neural_v4') |                       14.63  |                       40    |                            27 |                  5.296 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23948 |           100    |          3 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23955 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |