"""Utilidades compartidas por las etapas de preparación (E3)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from p09.config import PARAMS, ruta

MEDICAMENTOS = [
    "metformin", "repaglinide", "nateglinide", "chlorpropamide", "glimepiride",
    "acetohexamide", "glipizide", "glyburide", "tolbutamide", "pioglitazone",
    "rosiglitazone", "acarbose", "miglitol", "troglitazone", "tolazamide",
    "examide", "citoglipton", "insulin", "glyburide-metformin", "glipizide-metformin",
    "glimepiride-pioglitazone", "metformin-rosiglitazone", "metformin-pioglitazone",
]
NUMERICAS_CRUDAS = [
    "time_in_hospital", "num_lab_procedures", "num_procedures", "num_medications",
    "number_outpatient", "number_emergency", "number_inpatient", "number_diagnoses",
]
TOKENS_FALTANTE = {"?", "None", "none", "NULL", "nan", "NaN", ""}


def leer(rel: str) -> pd.DataFrame:
    return pd.read_parquet(ruta(rel))


def escribir(df: pd.DataFrame, rel: str) -> None:
    destino = ruta(rel)
    destino.parent.mkdir(parents=True, exist_ok=True)
    # index=False y sin metadatos de tiempo => misma huella md5 en cada ejecución
    df.to_parquet(destino, index=False, engine="pyarrow", compression="snappy")


def _a_json(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return round(float(o), 6)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))


def reporte(datos: dict, rel: str) -> None:
    """Escribe un JSON determinista (sin fechas) para que DVC lo compare."""
    destino = ruta(rel)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(datos, indent=2, ensure_ascii=False, sort_keys=True, default=_a_json),
        encoding="utf-8",
    )


def p(seccion: str) -> dict:
    return PARAMS[seccion]


def normalizar_faltantes(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte '?', 'None', '' ... en NaN real en columnas de texto."""
    df = df.copy()
    for c in df.select_dtypes(include=["object", "string"]).columns:
        s = df[c].astype("string").str.strip()
        df[c] = s.mask(s.isin(TOKENS_FALTANTE))
    return df


def md5_archivo(rel: str | Path) -> str:
    """Huella md5 de un archivo: la identidad del crudo en el contrato E2 -> E3."""
    import hashlib
    h = hashlib.md5()
    with open(ruta(rel), "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def raiz_ok() -> Path:
    return ruta(".")
