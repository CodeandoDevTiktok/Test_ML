"""Vocabulario MLflow del proyecto: se acuerda al principio y no se toca.

Etiquetas obligatorias en TODAS las ejecuciones (filtrables por igualdad):
    tipo           baseline | estudio | trial | campeon | evaluacion | reporte
    etapa          E4 | E5
    algoritmo      b0_prevalencia | b1_logistica | b2_regla | logistica | random_forest | hist_gb
    version_datos  vN (de la etiqueta git datos-vN)
    datos_md5_*    huellas DVC (procedencia)
    git_commit / git_limpio / github_url
"""
from __future__ import annotations

import time
from contextlib import contextmanager

import mlflow
import numpy as np

from p09.config import PARAMS, preparar_entorno_mlflow
from p09.procedencia import procedencia

_listo = False


def iniciar() -> None:
    global _listo
    if not _listo:
        uri = preparar_entorno_mlflow()
        print(f"MLflow -> {uri}")
        _listo = True


def etiquetas(**extra) -> dict:
    t = {**procedencia(), "proyecto": "P09"}
    t.update({k: str(v) for k, v in extra.items()})
    return t


@contextmanager
def run(nombre: str, nested: bool = False, **tags):
    iniciar()
    with mlflow.start_run(run_name=nombre, nested=nested) as r:
        mlflow.set_tags(etiquetas(**tags))
        t0 = time.time()
        yield r
        mlflow.log_metric("duracion_seg", round(time.time() - t0, 2))


def log_cv(resultados: list[dict], prefijo: str = "cv_") -> dict:
    """Registra media y desviación de las métricas por pliegue."""
    resumen = {}
    for k in resultados[0]:
        vals = np.array([r[k] for r in resultados], dtype=float)
        resumen[f"{prefijo}{k}_media"] = float(np.nanmean(vals))
        resumen[f"{prefijo}{k}_std"] = float(np.nanstd(vals))
    mlflow.log_metrics(resumen)
    return resumen


def k_frac() -> float:
    return float(PARAMS["evaluacion"]["k_fraccion"])
