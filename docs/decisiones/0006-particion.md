# 0006 · Formato, roles y partición

**Estado:** aceptada · **Tarea CRISP-DM:** 3.5 Formatear + partición · etapas `formatear`, `particionar` · **Fecha:** 2026-10-17

## Contexto
E2: 16 773 pacientes con más de un episodio (47 021 filas). E1: validar separando pacientes.

## Decisión
- Cada columna recibe un rol (id, predictora, auditoría, referencia, objetivo); el diccionario de datos se **genera** desde el código (100 % de columnas).
- Partición 80/20 con `StratifiedGroupKFold` por `patient_nbr`: ningún paciente en ambos lados y prevalencia equivalente. Se adelanta a E3 para que nada de E4 vea el test.

## Implementación
`particion.*`; `src/p09/datos/formatear.py`, `particionar.py`; `reportes/e3/particion.json` (`pacientes_solapados` debe ser 0).
