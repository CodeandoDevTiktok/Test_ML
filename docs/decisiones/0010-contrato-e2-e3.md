# 0010 · Contrato E2 → E3 (notebook E2 autónomo)

**Estado:** aceptada · **Tarea CRISP-DM:** 2.1–2.4 → 3.1/3.2 · **Fecha:** 2026-11-01

## Contexto
El notebook E2 leía Drive en memoria y no dejaba nada versionado; E3 partía de una descarga aparte. En una primera corrección, el notebook pasó a depender del repositorio (`proyecto.yaml`, paquete `p09`) y falló en Colab (`StopIteration`). El equipo trabaja E2 en Colab y no debe copiar archivos `.py` al entorno.

## Decisión
1. **El notebook E2 es autónomo.** Solo necesita librerías y una celda de parámetros con `GITHUB_URL`. Si el repo tiene `proyecto.yaml`, lee de ahí el resto de la configuración. Los secretos van en variables de entorno o en los Secretos de Colab.
2. **El contrato son las tablas del notebook** (`reportes/e2/*.json|csv|png`). Se elimina el `eda.py` del repositorio para no tener la misma lógica en dos sitios.
3. **El notebook publica en tres destinos:**
   - MLflow: run `tipo=eda`, raíz del linaje.
   - MinIO: `datasets/crudo/<tag>/` con los bytes exactos, `datasets/eda/<tag>/`, el manifiesto y el catálogo.
   - GitHub: vía API REST, como rama `e2/<tag>` con pull request, para respetar la revisión obligatoria.
4. **El repositorio importa.** `python tareas.py importar-e2 --tag <tag>` baja el crudo de MinIO, verifica su md5 contra el contrato, lo registra en DVC y etiqueta `crudo-vN`.
5. **E3 depende del contrato en el grafo.** `seleccionar` verifica el md5 y las filas; `limpiar` responde a `calidad.json`.
6. **Bloque 9.** `python tareas.py e2` ejecuta el mismo notebook sin interfaz desde el repo.

## Alternativas descartadas
- **Que el notebook clone el repo e instale el paquete:** añade dependencia y credenciales de git en Colab.
- **Escribir el `.py` como archivo temporal:** el equipo lo rechazó explícitamente.
- **Un `.py` paralelo en el repo:** dos implementaciones de las mismas cifras acaban divergiendo.

## Consecuencias
- Desde el modelo `@campeon` se llega al run de E2 y al md5 del crudo exacto.
- Un crudo distinto al descrito no se puede registrar ni preparar.
