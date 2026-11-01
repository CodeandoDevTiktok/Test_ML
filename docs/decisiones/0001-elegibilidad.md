# 0001 · Elegibilidad de episodios

**Estado:** aceptada · **Tarea CRISP-DM:** 3.1 Seleccionar · etapa `seleccionar` · **Fecha:** 2026-10-17

## Contexto
E1 (salida 9) define la población elegible; E2 encontró 1 652 episodios (1,62 %) con destino de alta = fallecimiento (códigos 11, 19, 20, 21) y 3 filas con `gender = Unknown/Invalid`.

## Decisión
Se excluyen: fallecimientos (no pueden reingresar), hospicio 13–14 (no accionable para seguimiento reforzado), alta voluntaria 7 (población con mecanismo distinto, E1) y género inválido (dato imposible).

## Alternativas consideradas
- Conservar hospicio y alta voluntaria como categorías: descartado hasta tener criterio clínico; se reactivan con `excluir_hospicio: false` / `excluir_alta_voluntaria: false`.
- Etiquetar fallecimientos como negativos: genera negativos artificiales (riesgo de E1, salida 6).

## Implementación
- Parámetros: `seleccion.disposiciones_*`, `seleccion.excluir_*`
- Código: `src/p09/datos/seleccionar.py`
- Evidencia: `reportes/e3/seleccion.json` (filas por regla y tasa `<30` en excluidas)

## Consecuencias
La tasa de `<30` de cada grupo excluido queda registrada para auditar que la exclusión no sesga la prevalencia. **Pendiente**: validar con la Dra. Lares el tratamiento de transferencias y psiquiatría.
