# 0013 · Hospicio dentro de la población elegible

**Estado:** aceptada · **Tarea CRISP-DM:** 3.x (nueva versión del conjunto de datos) · **Fecha:** 2026-11-01

## Contexto
E1 dejó el alta a hospicio (códigos 13 y 14) «a revisar» y datos-v1 la excluyó por no ser accionable (bitácora 0001, que prevé reactivarla con excluir_hospicio: false). En datos-v1 fueron 771 episodios (0,76 %) con tasa de reingreso <30 de 5,58 %, la mitad de la prevalencia general. Esta versión los conserva para medir en E4 si incluirlos cambia el desempeño y en E5 si cambia la equidad, antes de fijar la población definitiva con clínica.

## Decisión
| Parámetro | Antes | Después |
|---|---|---|
| `seleccion.excluir_hospicio` | `true` | `false` |

La versión anterior de la tabla se conserva (su etiqueta y sus objetos en `dvc-store/`). E4 compara ambas.

## Implementación
- Parámetros: los de la tabla, en `params.yaml`.
- Etapas afectadas: las que declaran esos parámetros en `dvc.yaml` y las que dependen de ellas.
- Asunto (issue) de GitHub: pendiente de asignar

## Consecuencias

Medido por el pipeline frente a `datos-v1`:

- episodios elegibles: 98,717 → 99,488
- prevalencia <30 (%): 11.37 → 11.32
- pacientes únicos: 69,663 → 70,113
- filas de train: 78,914 → 79,620
- filas de test: 19,803 → 19,868


La nueva tabla se publica como `datos-v2`. Evidencia: `reportes/e3/seleccion.json` y `reportes/e3/particion.json` de cada etiqueta.
