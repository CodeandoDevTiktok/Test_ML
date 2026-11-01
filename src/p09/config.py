"""Configuración central del proyecto P09.

Lee tres fuentes y las expone como objetos simples:

* ``proyecto.yaml``  -> infraestructura (GitHub, MinIO, MLflow). Versionado.
* ``params.yaml``    -> decisiones de datos y modelado. Versionado (DVC lo lee).
* ``.env``           -> secretos (credenciales MinIO). NUNCA versionado.

Uso::

    from p09.config import CFG, PARAMS, RAIZ, preparar_entorno_mlflow
    print(CFG["github"]["url"])
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml


def _buscar_raiz() -> Path:
    """Sube directorios hasta encontrar proyecto.yaml (funciona desde notebooks/)."""
    aqui = Path.cwd().resolve()
    for p in [aqui, *aqui.parents]:
        if (p / "proyecto.yaml").exists():
            return p
    # Respaldo: ubicación del paquete (src/p09/config.py -> raíz)
    return Path(__file__).resolve().parents[2]


RAIZ: Path = _buscar_raiz()


def _leer_yaml(nombre: str) -> dict:
    with open(RAIZ / nombre, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _cargar_env() -> None:
    """Carga .env sin sobrescribir variables ya definidas en el sistema."""
    ruta = RAIZ / ".env"
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


_cargar_env()
CFG: dict = _leer_yaml("proyecto.yaml")
PARAMS: dict = _leer_yaml("params.yaml")

# ------------------------------------------------------------------ atajos
GITHUB_URL: str = os.environ.get("GITHUB_URL", CFG["github"]["url"])
GITHUB_RAMA: str = CFG["github"].get("rama", "main")
MINIO_ENDPOINT: str = os.environ.get("MINIO_ENDPOINT", CFG["minio"]["endpoint"])
MINIO_BUCKET: str = CFG["minio"]["bucket"]
MLFLOW_URI: str = os.environ.get("MLFLOW_TRACKING_URI", CFG["mlflow"]["tracking_uri"])
EXPERIMENTO: str = os.environ.get("MLFLOW_EXPERIMENT_NAME", CFG["mlflow"]["experimento"])
MODELO_REGISTRADO: str = CFG["mlflow"]["modelo_registrado"]
ALIAS_CAMPEON: str = CFG["mlflow"]["alias_campeon"]


def ruta(rel: str | Path) -> Path:
    """Ruta absoluta a partir de la raíz del repositorio."""
    return RAIZ / rel


def credenciales_minio() -> tuple[str, str]:
    acceso = os.environ.get("MINIO_ACCESS_KEY") or os.environ.get("AWS_ACCESS_KEY_ID")
    secreto = os.environ.get("MINIO_SECRET_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not acceso or not secreto:
        raise RuntimeError(
            "Faltan credenciales de MinIO. Copie .env.example a .env y complete "
            "MINIO_ACCESS_KEY y MINIO_SECRET_KEY."
        )
    return acceso, secreto


def preparar_entorno_mlflow() -> str:
    """Configura variables para que MLflow escriba en el servidor del piloto.

    Si el servidor guarda artefactos directamente en MinIO (sin proxy), el
    cliente necesita MLFLOW_S3_ENDPOINT_URL y credenciales S3. Si el servidor
    usa --serve-artifacts, estas variables simplemente no se usan.
    """
    import mlflow

    os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", MINIO_ENDPOINT)
    try:
        acceso, secreto = credenciales_minio()
        os.environ.setdefault("AWS_ACCESS_KEY_ID", acceso)
        os.environ.setdefault("AWS_SECRET_ACCESS_KEY", secreto)
    except RuntimeError:
        pass
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENTO)
    return MLFLOW_URI
