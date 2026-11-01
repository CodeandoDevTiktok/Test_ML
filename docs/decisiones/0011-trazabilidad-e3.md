# 0011 · Cierre trazable de E3

**Estado:** aceptada · **Tarea CRISP-DM:** 3.1–3.5 (salidas documentales) · **Fecha:** 2026-11-01

## Contexto
La auditoría de E3 encontró que el pipeline se había ejecutado pero nunca se había versionado:
`dvc.lock`, `reportes/e3/` y `docs/diccionario/` no estaban en el repositorio, y en MinIO solo
existía el crudo (`dvc status -c` marcaba como `new` todas las salidas). `proyecto.yaml` apuntaba
a otro repositorio, por lo que el notebook trabajó en un clon sin commits. Los runs de E4/E5
quedaron con `version_datos = sin-version` y `datos_md5_crudo = sin-puntero`.

## Decisión
1. E3 se cierra **publicando**: `dvc.lock`, métricas y diccionario van a Git; las salidas van a MinIO
   (`dvc push`) y se etiqueta `datos-vN`. Primero el contenido, después el historial.
2. Las constantes de negocio que quedaban en el código pasan a `params.yaml`
   (`seleccion.valores_genero_invalido`, `limpieza.token_no_medido`, `limpieza.columnas_no_medido`,
   `construccion.cortes_grupo_edad`). Los valores no cambian: la tabla final es la misma.
3. La agrupación CIE-9 se mantiene en `src/p09/datos/cie9.py` como **diccionario versionado**
   (`VERSION_DICCIONARIO`): es una tabla de referencia clínica, no un umbral; cambiarla exige
   nueva entrada en la bitácora (ver 0004).
4. La comprobación de reproducibilidad compara `dvc.lock` contra `HEAD`, no contra el índice.

## Implementación
- Parámetros: los cuatro nombrados arriba.
- Código: `seleccionar.py`, `limpiar.py`, `construir.py`, `procedencia.py`, `tareas.py`.
- Cuaderno: `notebooks/E3_...` (secciones «Correcciones» y «Publicación»).
- Asunto (issue) de GitHub: pendiente de asignar

## Consecuencias
E4 y E5 deben volver a ejecutarse sobre la etiqueta `datos-vN` para que sus runs lleven
`version_datos` y las huellas de `dvc.lock`. Las credenciales que circularon en los cuadernos
se consideran comprometidas: se rotan fuera del repositorio.
