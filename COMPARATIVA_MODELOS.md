# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-10 18:15:23

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 3% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 28% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 21% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 10% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.511 |                       10    |                           155 |                  1.929 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.498 |                        0.83 |                             5 |                  0.6   |
| ('LOTO3', 'oraculo_neural_v3') |                       24.938 |                       66.67 |                           272 |                  0.864 |
| ('LOTO3', 'oraculo_neural_v4') |                       19.644 |                      100    |                            75 |                  0.813 |
| ('LOTO4', 'oraculo_neural_v3') |                        0.84  |                       50    |                           250 |                  0.48  |
| ('LOTO4', 'oraculo_neural_v4') |                       11.132 |                       50    |                            53 |                  1.151 |
| ('RACHA', 'oraculo_neural_v3') |                       11.449 |                       60    |                           207 |                  4.841 |
| ('RACHA', 'oraculo_neural_v4') |                       14.762 |                       40    |                            21 |                  5.286 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| LOTO3   | oraculo_neural_v4 |             23948 |           100    |          3 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23934 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |