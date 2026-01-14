# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-13 23:01:16

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 4% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 31% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 23% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 13% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.4   |                       10    |                           157 |                  1.917 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.833 |                        1.67 |                             7 |                  1     |
| ('LOTO3', 'oraculo_neural_v3') |                       25.093 |                       66.67 |                           284 |                  0.866 |
| ('LOTO3', 'oraculo_neural_v4') |                       19.578 |                      100    |                            87 |                  0.805 |
| ('LOTO4', 'oraculo_neural_v3') |                        0.817 |                       50    |                           257 |                  0.479 |
| ('LOTO4', 'oraculo_neural_v4') |                        9.833 |                       50    |                            60 |                  1.1   |
| ('RACHA', 'oraculo_neural_v3') |                       11.628 |                       60    |                           215 |                  4.828 |
| ('RACHA', 'oraculo_neural_v4') |                       14.31  |                       40    |                            29 |                  5.241 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23948 |           100    |          3 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23961 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23955 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v4 |             23954 |            66.67 |          2 |