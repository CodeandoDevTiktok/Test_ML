# 0003 · Tratamiento de faltantes y códigos

**Estado:** aceptada · **Tarea CRISP-DM:** 3.2 Limpiar · etapa `limpiar` · **Fecha:** 2026-10-17

## Contexto
Plan de calidad de E2: `max_glu_serum` 94,75 %, `A1Cresult` 83,28 %, `medical_specialty` 49,08 %, `payer_code` 39,56 %, `race` 2,23 %, `diag_3` 1,40 %. Códigos NULL / Not Mapped / Not Available en las tres variables administrativas.

## Decisión
1. **Ausencia informativa** (E1: puede reflejar proceso de atención): `max_glu_serum`, `A1Cresult` → categoría `No medido`; `medical_specialty`, `payer_code` → `Desconocido`. No se imputa con moda.
2. Diagnósticos y raza faltantes → `Desconocido`.
3. Códigos sin significado → `-1` (`Desconocido`).
4. **No** se imputa nada con estadísticas del conjunto completo: cualquier imputación residual la hace el `SimpleImputer` del pipeline de E4, ajustado solo con train (evita fuga, guía S03).
5. Atípicos IQR: se registran, **no** se recortan (E2: valores clínicamente posibles).

## Implementación
`limpieza.*`; `src/p09/datos/limpiar.py`; informe `reportes/e3/limpieza.json`, que responde problema por problema al plan de calidad de E2.
