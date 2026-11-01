# 0007 · Diseño de la prueba (E4)

**Estado:** aceptada · **Tarea CRISP-DM:** 4.2 Generar el diseño de prueba · **Fecha:** 2026-10-17

## Decisión
- Selección: validación cruzada `StratifiedGroupKFold(5)` por paciente **solo sobre train**.
- Métrica primaria: `recall_at_k` con K = `evaluacion.k_fraccion` (10 % de las altas) — declarada en E1 antes de entrenar.
- Secundarias: `precision_at_k`, `aucpr`, `roc_auc`, `brier`, calibración.
- Baselines B0 (prevalencia), B1 (logística C=1), B2 (regla `number_inpatient`), evaluados con los mismos pliegues.
- El test se usa **una sola vez**, en E5, solo para el campeón y los baselines.

## Implementación
`src/p09/modelado/pipeline.py`, `metricas.py`, `baselines.py`.
