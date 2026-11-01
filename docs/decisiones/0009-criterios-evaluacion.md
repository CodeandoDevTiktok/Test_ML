# 0009 · Criterios de evaluación y elección del campeón (E5)

**Estado:** aceptada · **Tarea CRISP-DM:** 5.1 Evaluar resultados · **Fecha:** 2026-10-17

## Decisión
1. Filtrar (`tipo=trial`, `estado=completo`, `version_datos` actual) y **después** ordenar.
2. Regla de un error estándar: entre los mejores de cada algoritmo, el más simple cuyo `cv_recall_at_k` esté a ≤1 EE del mejor.
3. Reentrenar con todo train y calibrar (`isotonic`, pliegues agrupados).
4. Criterios (E1, salida 10): C1 Recall@K ≥ 1,10 × mejor baseline; C2 AUCPR ≥ 1,5 × prevalencia; C3 Brier no peor que B1 (+2 %); C4 brecha de sensibilidad ≤ 10 pp entre grupos con n ≥ 500 y ≥ 30 positivos.
5. IC 95 % por bootstrap **de pacientes**.
6. Veredicto: `CUMPLE` / `CUMPLE CON MITIGACIONES` / `NO CUMPLE: renegociar alcance`. Los tres son legítimos; ocultarlo no.
7. Registrar `p09-reingreso-30d@campeon` y un run `reporte-final`.

## Implementación
`evaluacion.*`; `src/p09/evaluacion/evaluar.py`.
