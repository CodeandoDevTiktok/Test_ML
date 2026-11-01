"""Métricas del proyecto. Nombres FIJOS: deben llamarse igual en todos los runs
de MLflow para poder ordenarlos juntos (guía S04, error frecuente 2).

Métrica primaria (declarada en E1, salida 10, ANTES de entrenar): recall_at_k.
"""
from __future__ import annotations

import math

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def _top_k(score: np.ndarray, k_frac: float) -> np.ndarray:
    n = len(score)
    k = max(1, math.ceil(k_frac * n))
    # orden estable: empates resueltos por posición => determinista
    orden = np.argsort(-np.asarray(score), kind="stable")
    marca = np.zeros(n, dtype=bool)
    marca[orden[:k]] = True
    return marca


def recall_at_k(y, score, k_frac: float) -> float:
    """Proporción de TODOS los reingresos capturados dentro de los K cupos."""
    y = np.asarray(y)
    if y.sum() == 0:
        return float("nan")
    return float(y[_top_k(score, k_frac)].sum() / y.sum())


def precision_at_k(y, score, k_frac: float) -> float:
    """Proporción de reingresos reales entre los K priorizados."""
    y = np.asarray(y)
    return float(y[_top_k(score, k_frac)].mean())


def calibracion(y, proba) -> tuple[float, float]:
    """Pendiente e intercepto de calibración (regresión logística sobre logit(p))."""
    p = np.clip(np.asarray(proba, dtype=float), 1e-6, 1 - 1e-6)
    logit = np.log(p / (1 - p)).reshape(-1, 1)
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(logit, np.asarray(y))
    return float(lr.coef_[0, 0]), float(lr.intercept_[0])


def evaluar(y, score, k_frac: float, prefijo: str = "", probabilidades: bool = True) -> dict:
    y = np.asarray(y)
    m = {
        "recall_at_k": recall_at_k(y, score, k_frac),
        "precision_at_k": precision_at_k(y, score, k_frac),
        "aucpr": float(average_precision_score(y, score)),
        "roc_auc": float(roc_auc_score(y, score)),
        "prevalencia": float(y.mean()),
    }
    m["lift_at_k"] = m["precision_at_k"] / m["prevalencia"] if m["prevalencia"] else float("nan")
    m["aucpr_sobre_prevalencia"] = m["aucpr"] / m["prevalencia"] if m["prevalencia"] else float("nan")
    if probabilidades:
        m["brier"] = float(brier_score_loss(y, score))
        m["cal_pendiente"], m["cal_intercepto"] = calibracion(y, score)
    return {f"{prefijo}{k}": v for k, v in m.items()}


def bootstrap_por_paciente(y, score, grupos, k_frac: float, n: int = 500, semilla: int = 42) -> dict:
    """IC 95 % remuestreando PACIENTES (no filas): respeta la dependencia intra-paciente."""
    rng = np.random.default_rng(semilla)
    y, score, grupos = np.asarray(y), np.asarray(score), np.asarray(grupos)
    unicos, inv = np.unique(grupos, return_inverse=True)
    filas_por = [np.where(inv == i)[0] for i in range(len(unicos))]
    res = {"recall_at_k": [], "precision_at_k": [], "aucpr": [], "roc_auc": []}
    for _ in range(n):
        idx = np.concatenate([filas_por[i] for i in rng.integers(0, len(unicos), len(unicos))])
        yy, ss = y[idx], score[idx]
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        res["recall_at_k"].append(recall_at_k(yy, ss, k_frac))
        res["precision_at_k"].append(precision_at_k(yy, ss, k_frac))
        res["aucpr"].append(average_precision_score(yy, ss))
        res["roc_auc"].append(roc_auc_score(yy, ss))
    out = {}
    for k, v in res.items():
        out[f"{k}_ic_inf"] = float(np.percentile(v, 2.5))
        out[f"{k}_ic_sup"] = float(np.percentile(v, 97.5))
    return out
