# 0004 · Variables derivadas

**Estado:** aceptada · **Tarea CRISP-DM:** 3.3 Construir · etapa `construir` · **Fecha:** 2026-10-17

## Contexto
Consulta clínica (E1): ≥4 hospitalizaciones previas es señal fuerte; agrupar diagnósticos (insuficiencia cardíaca, piel/celulitis, neurología, infecciosas, subgrupos de diabetes). E2: `<30` es 8,56 % sin ingreso previo vs 16,90 % con al menos uno.

## Decisión
Se construyen 14 atributos, todos disponibles **al momento del alta** (ventana de observación): objetivo `reingreso_30d`, `edad_num`, `grupo_edad`, `visitas_previas_total`, `hosp_previas_4mas`, `n_meds_activos`, `n_meds_cambiados`, `a1c_medido`, `glu_medido`, `diag_k_grupo` (diccionario `cie9-v1`), `diag_principal_diabetes`, `especialidad_grupo`. Se elimina `readmitted` tras derivar el objetivo.

## Implementación
`construccion.*`; `src/p09/datos/construir.py`, `src/p09/datos/cie9.py`.

## Consecuencias
El diccionario CIE-9 está versionado (`VERSION_DICCIONARIO`); cambiarlo exige nueva entrada en la bitácora y revisión clínica.
