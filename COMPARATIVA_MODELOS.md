# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-02 14:40:34

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ⚠️ **LOTO**: v4 está siendo 'silenciado'. Solo el 1% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO3**: v4 está siendo 'silenciado'. Solo el 10% de sus ideas pasan el filtro cognitivo.
- ⚠️ **LOTO4**: v4 está siendo 'silenciado'. Solo el 8% de sus ideas pasan el filtro cognitivo.
- ⚠️ **RACHA**: v4 está siendo 'silenciado'. Solo el 3% de sus ideas pasan el filtro cognitivo.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO', 'oraculo_neural_v3')  |                        9.627 |                       10    |                           152 |                  1.947 |
| ('LOTO', 'oraculo_neural_v4')  |                        0.415 |                        0.83 |                             2 |                  0.5   |
| ('LOTO3', 'oraculo_neural_v3') |                       26.848 |                       66.67 |                           238 |                  0.92  |
| ('LOTO3', 'oraculo_neural_v4') |                       14.202 |                      100    |                            23 |                  0.609 |
| ('LOTO4', 'oraculo_neural_v3') |                        0.235 |                       50    |                           213 |                  0.437 |
| ('LOTO4', 'oraculo_neural_v4') |                        0     |                        0    |                            16 |                  0.25  |
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
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |
| LOTO3   | oraculo_neural_v3 |             23941 |            66.67 |          2 |