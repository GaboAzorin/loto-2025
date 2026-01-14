# 📊 Auditoría de Modelos: v3 vs v4
Actualizado el: 2026-01-14 15:07:31

## 🌡️ Alerta de Silenciamiento (Salud del Filtro)
- ✅ **LOTO3**: v4 tiene una tasa de aceptación saludable.
- ✅ **RACHA**: v4 tiene una tasa de aceptación saludable.

## 📈 Resumen de Rendimiento
|                                |   ('score_afinidad', 'mean') |   ('score_afinidad', 'max') |   ('score_afinidad', 'count') |   ('aciertos', 'mean') |
|:-------------------------------|-----------------------------:|----------------------------:|------------------------------:|-----------------------:|
| ('LOTO3', 'oraculo_neural_v3') |                            0 |                           0 |                             1 |                      0 |
| ('LOTO3', 'oraculo_neural_v4') |                            0 |                           0 |                             1 |                      0 |
| ('RACHA', 'oraculo_neural_v3') |                           15 |                          15 |                             1 |                      6 |
| ('RACHA', 'oraculo_neural_v4') |                            5 |                           5 |                             1 |                      5 |

## 🏆 Top 5 Mejores Aciertos (Histórico)
| juego   | algoritmo         |   sorteo_objetivo |   score_afinidad |   aciertos |
|:--------|:------------------|------------------:|-----------------:|-----------:|
| RACHA   | oraculo_neural_v3 |             10295 |               15 |          6 |
| RACHA   | oraculo_neural_v4 |             10295 |                5 |          5 |
| LOTO3   | oraculo_neural_v3 |             23989 |                0 |          0 |
| LOTO3   | oraculo_neural_v4 |             23989 |                0 |          0 |