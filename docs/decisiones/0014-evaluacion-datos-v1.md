# 0014 · Evaluación de datos-v1

**Estado:** aceptada · **Tarea CRISP-DM:** 5.1–5.3 · **Fecha:** 2026-11-02

## Versión evaluada y por qué (decidido antes de usar el test)
En E4, la mejor configuración de datos-v1 (random forest, recall@K CV 0,2188) y la de datos-v2 (hist_gb, 0,2172) difieren en 0,0016, dentro de 1 error estándar: en desempeño son equivalentes. Sin diferencia de desempeño se mantiene la población accionable de la bitácora 0001: el alta a hospicio no es intervenible por el programa de seguimiento, así que se evalúa la población sin hospicio (datos-v1).

Comparación en CV entre versiones (E4, trials completos filtrados por md5 de train):

| versión | algoritmo | trials | mejor cv recall@K | 1 EE |
|---|---|---|---|---|
| datos-v1 | hist_gb | 8 | 0.2167 | 0.0061 |
| datos-v1 | logistica | 15 | 0.2105 | 0.0037 |
| datos-v1 | random_forest | 7 | 0.2188 | 0.0056 |
| datos-v2 | hist_gb | 10 | 0.2172 | 0.0023 |
| datos-v2 | logistica | 28 | 0.2129 | 0.0025 |
| datos-v2 | random_forest | 6 | 0.2154 | 0.0024 |

## Resultado
- Campeón por CV (regla de 1 EE): `hist_gb` · recall@K CV = 0.2167
- Test (uso único): recall@K = 0.2111 (IC 95 % bootstrap de pacientes 0.1927–0.2311) · AUCPR = 0.2013 · Brier = 0.0973

| Criterio (E1, salida 10) | Cumple | Detalle |
|---|---|---|
| C1_recall_at_k_supera_mejor_baseline_10pct | ❌ | {"valor": 0.2111, "referencia": "b1_logistica=0.2044", "mejora_relativa": 0.0326} |
| C2_aucpr_1_5x_prevalencia | ✅ | {"valor": 1.772, "umbral": 1.5} |
| C3_calibracion_no_peor_que_B1 | ✅ | {"brier_campeon": 0.09726, "brier_b1": 0.09783, "pendiente": 0.97} |
| C4_brecha_sensibilidad_pp | ❌ | {"valor": 29.15, "umbral": 10} |

**Veredicto: NO CUMPLE** · no cumple: C1_recall_at_k_supera_mejor_baseline_10pct, C4_brecha_sensibilidad_pp

## Próximos pasos
1. El campeón mejora +3.3% sobre b1_logistica=0.2044 en test; E1 exige +10 %. Llevarlo al dueño del proceso (vuelta a E1, tareas 1.1 y 1.4): decidir si esa mejora justifica el cambio de proceso o si se mantiene el umbral.
2. Volver a E3 con información nueva (adherencia, ajuste de insulina, laboratorio al alta) antes de reabrir E4: con las variables actuales, E4 mostró que la búsqueda de hiperparámetros ya no mueve el resultado.
3. Mientras tanto, la regla del mejor baseline es una herramienta utilizable y documentada. Ocultar este resultado sería el error, no obtenerlo.
4. Brecha de sensibilidad de 29.2 pp entre grupos (máximo 10 pp): identificar el grupo subatendido en `equidad.csv` y evaluar umbrales por grupo o cupos protegidos antes de cualquier uso.
5. E6 no despliega este modelo: el alias @campeon identifica la mejor opción evaluada, con su veredicto (NO CUMPLE) como etiqueta. Como máximo, piloto silencioso sin efecto en pacientes.

## Trazabilidad
- Datos: `datos-v1` · md5 train `5fac2bc0425cc9ac5a8d95faf0ff8b25` · crudo `crudo-v1`
- Modelo: `models:/p09-reingreso-30d@campeon` (etiquetas `veredicto`, `version_datos`, `datos_md5_train`, `git_commit`)
- MLflow: ejecuciones `campeon-*-v1` y `reporte-final-v1`
- Repositorio: `reportes/e5/` en esta misma rama · asunto: pendiente de asignar
