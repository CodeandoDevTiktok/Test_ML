# P09 · Reingreso hospitalario <30 días en pacientes con diabetes

**UTEC · Proyecto Integrador I · Grupo 2** — CRISP-DM etapas 1 a 5 · DVC + MinIO · Optuna + MLflow

> **Decisión que se mejora:** al momento del alta, ordenar a los pacientes diabéticos elegibles por riesgo de reingreso antes de 30 días para asignar los cupos limitados de seguimiento reforzado (E1).
> **Métrica primaria:** Recall@K, la proporción de reingresos capturados dentro de la capacidad K.

---

## 1 · La variable global de GitHub (lo primero que se edita)

Abra `proyecto.yaml` y cambie **una sola línea**:

```yaml
github:
  url: "https://github.com/SU-USUARIO/p09-reingreso-diabetes.git"
```

Todo lo demás la lee de ahí: `tareas.py setup` configura `git remote origin`, `tareas.py publicar` hace el push y cada ejecución de MLflow lleva la etiqueta `github_url`. Para una prueba puntual sin editar el archivo: `GITHUB_URL=... python tareas.py estado`.

## 2 · Primer uso (una vez por integrante)

```bash
conda env create -f environment.yml && conda activate p09-reingreso   # o: pip install -r requirements.txt
cp .env.example .env              # complete MINIO_ACCESS_KEY / MINIO_SECRET_KEY (no se versiona)
python tareas.py setup            # git + remoto GitHub + dvc init + remoto MinIO + bucket
python tareas.py estado           # comprueba URL de GitHub, MinIO y MLflow
```

**Quien inicia el repositorio** publica E2 desde el notebook y luego lo importa:

1. Abrir `notebooks/E2_...ipynb` en Colab. Es **autónomo**: no necesita el repo ni archivos `.py`.
2. En la celda **PARÁMETROS**, poner `GITHUB_URL` (y `GITHUB_SUBCARPETA` si el proyecto no está en la raíz del repo).
3. Credenciales, en este orden de preferencia:
   - *Secretos de Colab* (icono de llave): crear `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` y `GITHUB_TOKEN` y **activar «Acceso al notebook» en cada uno**.
   - o escribirlas en la celda **CREDENCIALES** del cuaderno. En ese caso, **vaciar esos valores antes de subir el cuaderno** a GitHub o Drive. El notebook avisa al final si detecta secretos escritos.
   - si falta alguna, el notebook la pide por teclado.
4. Ejecutar todo. La **verificación previa** prueba MinIO, MLflow y GitHub y se detiene con el motivo exacto si algo falla. Si todo está bien, el notebook publica en MLflow (run `tipo=eda`), en MinIO (crudo + contrato) y en GitHub (rama `e2/crudo-v1` con su pull request).
5. Aprobar el PR y, en el repositorio:

```bash
python tareas.py importar-e2 --tag crudo-v1   # baja el crudo de MinIO, verifica md5, dvc add, etiqueta, push
python tareas.py repro                        # E3 completo (verifica el contrato de E2)
python tareas.py version-datos datos-v1 -m "E3 inicial: elegibilidad + CIE-9 v1"
```

Sin Colab, la alternativa es `python tareas.py e2 --tag crudo-v1`, que ejecuta el mismo notebook sin interfaz desde el repo. Cumple el bloque 9: regenerar el EDA con un comando.

**E3, E4 y E5 también se ejecutan en Colab.** Esos cuadernos **no** son autónomos como E2 — y no deben serlo: su lógica vive en `src/p09/` y `dvc.yaml`, versionada y reproducible. Lo que hacen es traer el repositorio al entorno:

1. Abrir el cuaderno en Colab y poner `GITHUB_URL` en **PARÁMETROS** y las claves en **CREDENCIALES** (o en Secretos de Colab).
2. La celda de arranque clona el repositorio, instala dependencias, baja el crudo de MinIO con `importar-e2`, verifica el md5 contra el contrato de E2 y ejecuta `dvc repro`.
3. Al final, la celda de publicación sube los resultados: `dvc push` a MinIO y la etiqueta `datos-vN` a GitHub.

**En una máquina local** el mismo cuaderno detecta que ya está dentro del repositorio y lo usa tal cual. Sin cuadernos:

```bash
git clone <url> && cd p09-reingreso-diabetes
cp .env.example .env && python tareas.py setup
python tareas.py importar-e2 --tag crudo-v1
python tareas.py repro
```

## 2 bis · Cómo se conectan E2 y E3

```
 Colab · notebook E2 (autónomo: solo librerías + celda PARÁMETROS)
   │  lee Drive como bytes → md5 del crudo → análisis 2.1–2.4 → contrato reportes/e2/
   ├─► MLflow : run tipo=eda (métricas de calidad, hallazgos, figuras)      = raíz del linaje
   ├─► MinIO  : datasets/crudo/crudo-vN/ (bytes exactos) · datasets/eda/crudo-vN/ · CATALOGO.json
   └─► GitHub : API REST → rama e2/crudo-vN + pull request con reportes/e2/
                                   │ (revisión y merge)
 Repositorio                        ▼
   python tareas.py importar-e2 --tag crudo-vN
     baja datasets/crudo/crudo-vN de MinIO → md5 = contrato? → dvc add → etiqueta crudo-vN → push
   dvc repro
     seleccionar: verifica md5 y filas contra reportes/e2/descripcion.json
     limpiar:     responde variable por variable a reportes/e2/calidad.json
   E4/E5: cada run lleva run_eda + crudo_version + version_datos   (linaje modelo → crudo)
```

- **Una sola fuente de verdad.** El contrato son las tablas del propio notebook: `schema`, `missing_table`, `quality_codes`, `controls`, `quality_plan` y los hallazgos. No hay un `.py` paralelo que pueda divergir.
- **Configuración en GitHub.** El notebook solo necesita `GITHUB_URL`. Si el repo tiene `proyecto.yaml`, toma de ahí MinIO, MLflow y las fuentes. Los secretos nunca van en el notebook.
- **Idempotente.** Si el crudo no cambió, el notebook reutiliza el run de MLflow y la rama del PR.
- **Verificado.** `importar-e2` y `seleccionar` se niegan a continuar si el crudo no coincide con el contrato.
- **Rama protegida.** Si `main` está protegida, `GITHUB_MODO = "pr"` (el valor por defecto) respeta la revisión obligatoria. Con `"directo"` se hace commit en `main`.

## 3 · Flujo de trabajo diario

| Quiero… | Comando |
|---|---|
| Guardar un cambio con su porqué | `python tareas.py guardar -m "e3: excluye hospicio, 0,6 % filas, tasa <30 = 0 (#12)"` |
| Publicar (contenido y luego historial) | `python tareas.py publicar`  → `dvc push` + `git push --follow-tags` |
| Publicar E2 (nuevo crudo) | notebook E2 con `TAG_CRUDO = "crudo-v2"` → PR → `python tareas.py importar-e2 --tag crudo-v2` |
| Fijar una versión de la tabla de modelado | `python tareas.py version-datos datos-v2 -m "CIE-9 v2 revisado por clínica"` |
| Ver versiones organizadas en MinIO | `python tareas.py minio-listar` |
| Correr E4 (baselines + Optuna) | `python tareas.py e4 --n-trials 40` |
| Correr E5 (evaluación + @campeon) | `python tareas.py e5` |
| Comprobar reproducibilidad | `python tareas.py verificar` (repro forzado, `dvc.lock` idéntico) |

En Linux/macOS hay atajos equivalentes en el `Makefile` (`make e4 N=40`, `make version TAG=datos-v2 MSG="..."`).

**Reglas de commit (S03):**
- Una rama por decisión, con el número del asunto: `git switch -c 12-excluir-hospicio`.
- El mensaje dice qué se decidió, por qué y con qué magnitud, y cita el `#issue`.
- Si un cambio toca `params.yaml`, debe tocar también `dvc.lock` **en el mismo commit**. Si no lo hace, es que no se reejecutó.

## 4 · Estructura

```
p09-reingreso-diabetes/
├── proyecto.yaml          <- GITHUB URL (variable global), MinIO, MLflow, fuentes
├── params.yaml            <- todas las decisiones (E3, E4, E5), fuera del código
├── dvc.yaml / dvc.lock    <- receta de E3 y su anotación (ambas versionadas)
├── tareas.py              <- ejecutor multiplataforma de todo el flujo
├── .env.example           <- plantilla de credenciales (.env NUNCA se versiona)
├── datos/
│   ├── crudo/             <- inmutable; solo su puntero crudo.dvc va a git
│   ├── intermedio/        <- salidas de 3.1–3.4 (las gestiona DVC)
│   ├── final/             <- tabla_modelado.parquet (una fila por episodio)
│   └── particion/         <- train / test agrupados por paciente
├── src/p09/
│   ├── config.py · procedencia.py          <- configuración y puente DVC→MLflow
│   ├── datos/      seleccionar · limpiar · construir · cie9 · integrar · formatear · particionar
│   ├── modelado/   pipeline · metricas · baselines · optimizar (Optuna) · registro (MLflow)
│   ├── evaluacion/ evaluar · figuras
│   └── infra/      minio (bucket, snapshots, catálogo)
├── notebooks/             <- E1 · E2 (autónomo, publica el contrato) · E3, E4, E5
├── reportes/e2/           <- contrato E2→E3 (llega por PR desde el notebook E2)
├── docs/decisiones/       <- bitácora: una entrada por decisión (0001–0009)
├── docs/diccionario/      <- diccionario de datos GENERADO por la etapa formatear
├── reportes/e3 · e4 · e5  <- informes JSON/CSV/PNG producidos por el código
├── tests/                 <- pytest + generador sintético (solo pruebas)
└── .github/workflows/     <- CI: clon limpio → dvc pull → repro --force → dvc.lock idéntico
```

## 5 · Grafo de E3 (`dvc dag`)

```
reportes/e2 (contrato E2) ─┐
datos/crudo ──────────────┴► seleccionar (3.1) ─► limpiar (3.2) ─► construir (3.3) ─► integrar (3.4) ─► formatear (3.5) ─► particionar
                     └────────────► limpiar (lee calidad.json)
```

Cada etapa declara `deps`, `params`, `outs` y `metrics`, y su `desc` cita la entrada de `docs/decisiones/` que la justifica.

## 6 · MinIO: versionado organizado

```
s3://p09-reingreso/
├── dvc-store/                              <- remoto DVC (por huella md5) = fuente de verdad
└── datasets/
    ├── CATALOGO.json                       <- índice: tag, capas, commit, md5, filas, run_eda
    ├── manifiestos/<tag>.json              <- md5, bytes, filas y procedencia de cada archivo
    ├── crudo/crudo-vN/                     <- diabetic_data.parquet, IDS_mapping.csv   (E2)
    ├── eda/crudo-vN/                       <- informe E2: json, csv, figuras, mlflow_run.json (E2)
    ├── intermedio/datos-vN/                <- seleccionado, limpio, construido, integrado (E3)
    ├── final/datos-vN/                     <- tabla_modelado.parquet, diccionario_datos.csv
    ├── particion/datos-vN/                 <- train.parquet, test.parquet
    └── reportes/datos-vN/                  <- informes de E3 de esa versión
```

Para volver a cualquier versión: `git checkout datos-v1 && dvc checkout`.

`dvc-store/` nombra cada objeto por su huella md5 (no está cifrado: así lo exige el versionado por contenido). Para ver qué nombre corresponde a cada huella, sin descargar nada:

```bash
dvc list https://github.com/CodeandoDevTiktok/Test_ML datos --rev datos-v1 -R --dvc-only --show-hash --size
```

El objeto está en `dvc-store/files/md5/<2 primeros caracteres>/<resto>`. Cada manifiesto de `datasets/manifiestos/` trae ese enlace en `clave_dvc_store`.
La API S3 está en `:9000`; el `:9001` es la consola web. Si su servidor usa otro puerto, ajuste `minio.endpoint` en `proyecto.yaml`.

## 7 · MLflow: vocabulario acordado (no cambiar)

| Etiqueta `tipo` | Qué es |
|---|---|
| `eda` | E2: calidad, hallazgos, dataset con huella, figuras (raíz del linaje) |
| `baseline` | B0 prevalencia, B1 logística, B2 regla `number_inpatient` (CV) |
| `estudio` | ejecución madre de un estudio Optuna (un algoritmo) |
| `trial` | ejecución hija; `estado = completo` o `podado` |
| `campeon` | modelo reentrenado y calibrado, con métricas de test |
| `reporte` | `reporte-final-<versión>` con todos los artefactos de E5 |

Todas las ejecuciones llevan `run_eda`, `crudo_version`, `version_datos`, `datos_md5_train`, `datos_md5_test`, `git_commit`, `git_limpio` y `github_url`.
Las métricas tienen nombres fijos: `cv_recall_at_k_media`, `cv_aucpr_media`, `test_recall_at_k`, …
El modelo se consume por alias: `mlflow.pyfunc.load_model("models:/p09-reingreso-30d@campeon")`, que devuelve probabilidades calibradas.

**Para buscar ejecuciones, primero se filtra y después se ordena:**

```python
mlflow.search_runs(filter_string="tags.tipo = 'trial' and tags.estado = 'completo' and tags.version_datos = 'v1'",
                   order_by=["metrics.cv_recall_at_k_media DESC"], max_results=5000)
```

## 8 · Seguridad

- `.env` y `.dvc/config.local` están en `.gitignore`. Compruébelo con `git check-ignore .env .dvc/config.local`.
- El cuaderno E2 admite credenciales escritas en su celda **CREDENCIALES**; esa copia **no se sube** al repositorio con valores reales. Antes de subirlo o compartirlo, vaciarlos. El propio cuaderno avisa.
- `minioadmin` es la cuenta **raíz** de MinIO y su contraseña ya circuló por chat. Recomendación: rotarla y crear un usuario con permiso solo sobre `p09-reingreso`.
- Si una credencial llega al historial de Git, borrarla no basta: hay que **revocarla**.
- Para el CI, configure `MINIO_ACCESS_KEY` y `MINIO_SECRET_KEY` en *Settings → Secrets*.
