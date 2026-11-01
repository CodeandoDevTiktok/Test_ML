"""Construcción de datos, pliegues y pipelines de scikit-learn (E4).

Patrón de la guía S04: TODO el preprocesado vive dentro del Pipeline
(ColumnTransformer + modelo) para que (1) se ajuste solo con el pliegue de
entrenamiento —sin fuga— y (2) viaje con el modelo registrado en MLflow.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from p09.config import PARAMS, ruta

OBJETIVO = "reingreso_30d"
GRUPO = "patient_nbr"


def esquema() -> dict:
    return json.loads(ruta("reportes/e3/esquema.json").read_text(encoding="utf-8"))


def columnas() -> tuple[list[str], list[str]]:
    """Columnas predictoras numéricas y categóricas, según roles de E3 y params."""
    e = esquema()
    num, cat = list(e["numericas"]), list(e["categoricas"])
    if not PARAMS["modelado"]["usar_disposicion_alta"]:
        cat = [c for c in cat if c != "discharge_disposition_grupo"]
    return num, cat


def cargar(particion: str) -> pd.DataFrame:
    return pd.read_parquet(ruta(f"datos/particion/{particion}.parquet"))


def xy(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    num, cat = columnas()
    X = df[num + cat].copy()
    for c in cat:  # string -> object: OneHotEncoder y la firma MLflow lo esperan así
        X[c] = X[c].astype(object)
    return X, df[OBJETIVO].to_numpy(), df[GRUPO].to_numpy()


def pliegues(y: np.ndarray, grupos: np.ndarray, n_folds: int | None = None,
             semilla: int | None = None) -> list[tuple[np.ndarray, np.ndarray]]:
    """Validación cruzada agrupada por paciente y estratificada por resultado."""
    m = PARAMS["modelado"]
    sgkf = StratifiedGroupKFold(n_splits=n_folds or m["n_folds"], shuffle=True,
                                random_state=m["semilla"] if semilla is None else semilla)
    return list(sgkf.split(np.zeros(len(y)), y, groups=grupos))


def preprocesador(algoritmo: str, min_frequency: int = 20) -> ColumnTransformer:
    num, cat = columnas()
    pasos_num = [("imp", SimpleImputer(strategy="median"))]
    if algoritmo == "logistica":
        pasos_num.append(("esc", StandardScaler()))
    rama_num = Pipeline(pasos_num)
    rama_cat = Pipeline([
        ("imp", SimpleImputer(strategy="constant", fill_value="Desconocido")),
        ("oh", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=min_frequency,
                             sparse_output=False)),
    ])
    return ColumnTransformer([("num", rama_num, num), ("cat", rama_cat, cat)],
                             remainder="drop", verbose_feature_names_out=True)


def modelo(algoritmo: str, hp: dict, semilla: int):
    hp = {k: v for k, v in hp.items() if k != "min_frequency"}
    if algoritmo == "logistica":
        return LogisticRegression(max_iter=2000, solver="lbfgs", random_state=semilla, **hp)
    if algoritmo == "random_forest":
        return RandomForestClassifier(n_jobs=-1, random_state=semilla, **hp)
    if algoritmo == "hist_gb":
        return HistGradientBoostingClassifier(random_state=semilla, early_stopping=False, **hp)
    raise ValueError(f"algoritmo desconocido: {algoritmo}")


def construir(algoritmo: str, hp: dict, semilla: int | None = None) -> Pipeline:
    semilla = PARAMS["modelado"]["semilla"] if semilla is None else semilla
    pipe = Pipeline([
        ("pre", preprocesador(algoritmo, int(hp.get("min_frequency", 20)))),
        ("clf", modelo(algoritmo, hp, semilla)),
    ])
    pipe.set_output(transform="pandas")
    return pipe
