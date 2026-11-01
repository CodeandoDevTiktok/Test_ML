# 0012 · Vista legible de los datos versionados

**Estado:** aceptada · **Tarea CRISP-DM:** 3.1–3.5 (salidas documentales) · **Fecha:** 2026-11-01

## Contexto
En MinIO, `dvc-store/` guarda cada versión por su huella md5 (`files/md5/2d/1fdd…`). Es lo que exige la
guía S03 («versionar datos es dejar de identificarlos por su nombre»), pero el equipo no podía saber qué
objeto era cada tabla, y la copia legible `datasets/` no incluía las tablas intermedias.

## Decisión
1. `dvc-store/` **no se renombra ni se reorganiza**: es la fuente de verdad y DVC la localiza por huella.
2. `datasets/<capa>/<tag>/` es la vista para personas e incluye las capas `intermedio`, `final`,
   `particion` y `reportes` de E3.
3. Cada manifiesto (`datasets/manifiestos/<tag>.json`) enlaza cada archivo con su objeto en
   `dvc-store/` (`clave_dvc_store`). El mismo mapa se obtiene con
   `dvc list <repo> datos --rev <tag> -R --dvc-only --show-hash`.

## Alternativas descartadas
- Renombrar los objetos de `dvc-store/`: DVC dejaría de encontrarlos y se perderían la deduplicación y la
  verificación de integridad.
- Registrar los intermedios con `dvc add` para darles un puntero propio: serían salidas huérfanas
  (antipatrón 3 de la guía).

## Implementación
- Código: `src/p09/infra/minio.py` (`CAPAS`, `CAPAS_E3`, manifiesto).
- Cuaderno E3: secciones «Copia legible completa» y «Mapa nombre → huella».
- Asunto (issue) de GitHub: pendiente de asignar

## Consecuencias
La copia legible duplica unos 11 MB por versión de datos. Puede reconstruirse siempre desde `dvc-store/`.
