# 0008 · Optimización de hiperparámetros con Optuna

**Estado:** aceptada · **Tarea CRISP-DM:** 4.3 Construir el modelo · **Fecha:** 2026-10-17

## Decisión
- Un estudio Optuna (TPE, semilla fija, poda por mediana tras cada pliegue) por algoritmo: `logistica`, `random_forest`, `hist_gb`.
- El espacio incluye el preprocesado (`min_frequency` del OneHot) además del modelo.
- Registro: estudio = run madre (`tipo=estudio`), trial = run hijo (`tipo=trial`, `estado=completo|podado`), con procedencia DVC en cada uno.
- `cv_best_score` es optimista (máximo de N intentos): sirve para elegir, no para prometer.
- Estudios persistidos en `optuna.db` (local, ignorado por git) para poder reanudarlos.

## Alternativas
Rejilla exhaustiva (guía S04): inviable con 6+ hiperparámetros continuos. `mlflow.autolog`: registra demasiado por ejecución con >100 trials.

## Implementación
`modelado.optuna.*`; `src/p09/modelado/optimizar.py`.
