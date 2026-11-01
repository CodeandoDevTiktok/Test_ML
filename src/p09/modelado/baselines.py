"""Baselines técnicos declarados en E1 (salida 10) ANTES de entrenar:

* B0 · probabilidad constante = prevalencia de entrenamiento (equivale a azar)
* B1 · regresión logística regularizada (C=1) con las variables disponibles al alta
* B2 · regla clínica: priorizar por hospitalizaciones previas en el año
        (number_inpatient; desempate por visitas previas totales)

Se evalúan con la MISMA validación cruzada agrupada que los candidatos de Optuna.
"""
from __future__ import annotations

import argparse
import json

import mlflow
import numpy as np

from p09.config import ruta
from p09.modelado import registro
from p09.modelado.metricas import evaluar
from p09.modelado.pipeline import cargar, construir, pliegues, xy

BASELINES = ["b0_prevalencia", "b1_logistica", "b2_regla"]


def puntuar(nombre: str, Xtr, ytr, Xev) -> tuple[np.ndarray, bool]:
    """Devuelve (score, es_probabilidad) para el conjunto de evaluación."""
    if nombre == "b0_prevalencia":
        return np.full(len(Xev), ytr.mean()), True
    if nombre == "b1_logistica":
        pipe = construir("logistica", {"C": 1.0}).fit(Xtr, ytr)
        return pipe.predict_proba(Xev)[:, 1], True
    if nombre == "b2_regla":
        return (Xev["number_inpatient"].to_numpy(float)
                + 1e-3 * Xev["visitas_previas_total"].to_numpy(float)), False
    raise ValueError(nombre)


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser()
    ap.parse_args(argv)
    X, y, g = xy(cargar("train"))
    k = registro.k_frac()
    folds = pliegues(y, g)
    resumen = {}
    with registro.run("baselines", tipo="baselines_madre", etapa="E4"):
        for nombre in BASELINES:
            with registro.run(nombre, nested=True, tipo="baseline", etapa="E4", algoritmo=nombre):
                mlflow.log_params({"algoritmo": nombre, "k_fraccion": k, "n_train": len(y),
                                   "n_folds": len(folds), "validacion": "StratifiedGroupKFold(patient_nbr)"})
                res = []
                for tr, va in folds:
                    s, es_p = puntuar(nombre, X.iloc[tr], y[tr], X.iloc[va])
                    res.append(evaluar(y[va], s, k, probabilidades=es_p))
                resumen[nombre] = registro.log_cv(res)
                print(f"  {nombre:16s} recall@k={resumen[nombre]['cv_recall_at_k_media']:.4f}")
    destino = ruta("reportes/e4/baselines_cv.json")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    return resumen


if __name__ == "__main__":
    main()
