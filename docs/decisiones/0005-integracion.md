# 0005 · Integración con IDS_mapping

**Estado:** aceptada · **Tarea CRISP-DM:** 3.4 Integrar · etapa `integrar` · **Fecha:** 2026-10-17

## Contexto
`IDS_mapping.csv` contiene tres bloques concatenados (E2 §2.1).

## Decisión
Se parsea por bloques y se agrupan los códigos en categorías legibles (`*_grupo`).
**No** se construyen agregados por paciente: sin fecha por episodio, contar "episodios del paciente" incluiría episodios posteriores al alta (fuga de la ventana de resultado).

## Implementación
`integracion.*`; `src/p09/datos/integrar.py`; cobertura del mapeo en `reportes/e3/integracion.json`.
