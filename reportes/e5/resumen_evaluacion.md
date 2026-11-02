# Resumen de evaluación (E5) · datos v1

**Campeón:** `hist_gb` · recall@K CV = 0.2167
**Veredicto:** NO CUMPLE
**Criterios no cumplidos:** C1_recall_at_k_supera_mejor_baseline_10pct, C4_brecha_sensibilidad_pp

| Modelo (test) | Recall@K | Precision@K | AUCPR | ROC-AUC |
|---|---:|---:|---:|---:|
| campeon_calibrado | 0.2111 | 0.2398 | 0.2013 | 0.6522 |
| campeon_sin_calibrar | 0.2102 | 0.2388 | 0.2011 | 0.6525 |
| b0_prevalencia | 0.1000 | 0.1136 | 0.1136 | 0.5000 |
| b1_logistica | 0.2044 | 0.2322 | 0.1970 | 0.6378 |
| b2_regla | 0.2040 | 0.2317 | 0.1804 | 0.6095 |

IC 95 % Recall@K (bootstrap de pacientes): [0.1927, 0.2311]
Brier = 0.0973 · pendiente calibración = 0.970

## Criterios de éxito (E1)

- **C1_recall_at_k_supera_mejor_baseline_10pct**: ❌ {"valor": 0.2111, "referencia": "b1_logistica=0.2044", "mejora_relativa": 0.0326}
- **C2_aucpr_1_5x_prevalencia**: ✅ {"valor": 1.772, "umbral": 1.5}
- **C3_calibracion_no_peor_que_B1**: ✅ {"brier_campeon": 0.09726, "brier_b1": 0.09783, "pendiente": 0.97}
- **C4_brecha_sensibilidad_pp**: ❌ {"valor": 29.15, "umbral": 10}

## Traducción al negocio (por cada 100 altas elegibles)

Con 10.0 cupos: el modelo captura 2.4 de 11.36 reingresos esperados; el mejor baseline 2.32; el azar 1.14.