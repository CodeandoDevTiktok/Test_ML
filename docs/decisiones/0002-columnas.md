# 0002 · Columnas que entran

**Estado:** aceptada · **Tarea CRISP-DM:** 3.1 Seleccionar · etapa `seleccionar` · **Fecha:** 2026-10-17

## Contexto
E2: `weight` 96,86 % faltante; `examide` y `citoglipton` con cardinalidad 1. E1: raza no se usa para priorizar.

## Decisión
- Descartar `weight` (supera el umbral Kelleher de 50 %; sin señal recuperable).
- Descartar `examide`, `citoglipton` (constantes).
- Conservar `race` con rol **auditoría**: no entra al modelo, sí a la auditoría de equidad de E5.
- `discharge_disposition_grupo` se construye pero **no** es predictor salvo `modelado.usar_disposicion_alta: true` (E1: requiere evaluación temporal).

## Implementación
`seleccion.columnas_descartadas`, `seleccion.columnas_auditoria`, `modelado.usar_disposicion_alta`; roles en `src/p09/datos/formatear.py` y `reportes/e3/esquema.json`.
