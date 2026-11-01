"""El puente DVC -> MLflow: qué bytes de datos y qué código produjeron cada run.

La etiqueta de Git puede mentir; la huella md5 de DVC no. Por eso cada
ejecución de MLflow registra las tres cosas (guía S04, «El puente»).
"""
from __future__ import annotations

import subprocess
from functools import lru_cache

import yaml

from p09.config import GITHUB_URL, RAIZ


def _git(*args: str) -> str:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=RAIZ, timeout=15)
        return r.stdout.strip()
    except Exception:  # git no instalado o no es repo
        return ""


def _md5_desde_lock(ruta_salida: str) -> tuple[str, str]:
    """Busca la huella de una salida declarada en dvc.lock."""
    lock = RAIZ / "dvc.lock"
    if not lock.exists():
        return "sin-dvc-lock", "0"
    data = yaml.safe_load(lock.read_text(encoding="utf-8")) or {}
    for etapa in (data.get("stages") or {}).values():
        for out in etapa.get("outs", []) or []:
            if out.get("path") == ruta_salida:
                return out.get("md5", "?"), str(out.get("size", "?"))
    return "no-encontrado", "0"


def _md5_crudo() -> str:
    puntero = RAIZ / "datos" / "crudo.dvc"
    if not puntero.exists():
        return "sin-puntero"
    d = yaml.safe_load(puntero.read_text(encoding="utf-8"))
    return d["outs"][0].get("md5", "?")


def _vinculo_e2() -> tuple[str, str]:
    """Run de MLflow de E2 que describió ESTE crudo (si el md5 coincide)."""
    import json
    run_f, desc_f = RAIZ / "reportes/e2/mlflow_run.json", RAIZ / "reportes/e2/descripcion.json"
    if not run_f.exists() or not desc_f.exists():
        return "sin-e2", "sin-e2"
    run, desc = json.loads(run_f.read_text()), json.loads(desc_f.read_text())
    if run.get("md5_crudo") != desc.get("md5_crudo"):
        return "e2-desactualizado", desc.get("md5_crudo", "?")
    return run["run_id"], desc["md5_crudo"]


@lru_cache(maxsize=1)
def procedencia() -> dict[str, str]:
    md5_train, bytes_train = _md5_desde_lock("datos/particion/train.parquet")
    md5_test, bytes_test = _md5_desde_lock("datos/particion/test.parquet")
    md5_final, _ = _md5_desde_lock("datos/final/tabla_modelado.parquet")
    etiqueta = _git("describe", "--tags", "--always")
    run_eda, md5_archivo_crudo = _vinculo_e2()
    crudo_v = _git("describe", "--tags", "--abbrev=0", "--match", "crudo-v*")
    return {
        "crudo_version": crudo_v or "sin-version",
        "run_eda": run_eda,
        "md5_archivo_crudo": md5_archivo_crudo,
        "datos_md5_crudo": _md5_crudo(),
        "datos_md5_final": md5_final,
        "datos_md5_train": md5_train,
        "datos_md5_test": md5_test,
        "datos_bytes_train": bytes_train,
        "datos_bytes_test": bytes_test,
        "version_datos": _version_datos(etiqueta),
        "git_commit": _git("rev-parse", "--short", "HEAD") or "sin-git",
        "git_tag": etiqueta or "sin-tag",
        "git_limpio": "si" if _git("status", "--porcelain") == "" else "NO",
        "github_url": GITHUB_URL,
    }


def _version_datos(etiqueta: str) -> str:
    """Extrae 'vN' de la etiqueta más cercana 'datos-vN' (o 'sin-version')."""
    tags = _git("tag", "--points-at", "HEAD", "--list", "datos-v*").split()
    if tags:
        return sorted(tags)[-1].replace("datos-", "")
    previa = _git("describe", "--tags", "--abbrev=0", "--match", "datos-v*")
    return previa.replace("datos-", "") if previa else "sin-version"
