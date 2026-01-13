# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-13 00:48:24

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 4% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 29% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 22% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 12% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.455 |                       10    |                           156 |                  1.923 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.693 |                        1.67 |                             6 |                  0.833 |
| ('LOTO3', 'oraculo_neural_v3') |                       25.155 |                       66.67 |                           278 |                  0.871 |
| ('LOTO3', 'oraculo_neural_v4') |                       20.082 |                      100    |                            81 |                  0.827 |
| ('LOTO4', 'oraculo_neural_v3') |                        0.827 |                       50    |                           254 |                  0.48  |
| ('LOTO4', 'oraculo_neural_v4') |                       10.351 |                       50    |                            57 |                  1.105 |
| ('RACHA', 'oraculo_neural_v3') |                       11.374 |                       60    |                           211 |                  4.839 |
| ('RACHA', 'oraculo_neural_v4') |                       14     |                       40    |                            25 |                  5.24  |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23948 |           100    |          3 |
| LOTO3   | oraculo_neural_v3 |             23928 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23955 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23976 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |