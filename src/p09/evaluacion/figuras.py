"""Figuras de E5. Cada cifra del informe tiene su figura y viceversa (Anscombe)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.metrics import precision_recall_curve, roc_curve  # noqa: E402


def _guardar(fig, destino):
    fig.tight_layout()
    fig.savefig(destino, dpi=130)
    plt.close(fig)


def curva_ganancia(y, scores: dict, k_frac: float, destino) -> None:
    """Recall acumulado vs fracción de altas contactadas: la vista operativa."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    y = np.asarray(y)
    x = np.arange(1, len(y) + 1) / len(y)
    for nombre, s in scores.items():
        orden = np.argsort(-np.asarray(s), kind="stable")
        ax.plot(x, np.cumsum(y[orden]) / y.sum(), label=nombre)
    ax.plot([0, 1], [0, 1], ls=":", c="grey", label="azar")
    ax.axvline(k_frac, c="crimson", ls="--", lw=1)
    ax.text(k_frac + 0.01, 0.05, f"K = {k_frac:.0%} de las altas", color="crimson")
    ax.set_xlabel("fracción de altas priorizadas (cupos)")
    ax.set_ylabel("fracción de reingresos <30 d capturados")
    ax.set_title("Curva de ganancia en test (por paciente)")
    ax.set_xlim(0, 0.5)
    ax.set_ylim(0, 1)
    ax.legend()
    _guardar(fig, destino)


def curvas_pr_roc(y, scores: dict, destino) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for nombre, s in scores.items():
        p, r, _ = precision_recall_curve(y, s)
        axes[0].plot(r, p, label=nombre)
        f, t, _ = roc_curve(y, s)
        axes[1].plot(f, t, label=nombre)
    axes[0].axhline(np.mean(y), ls=":", c="grey", label="prevalencia")
    axes[0].set(xlabel="recall", ylabel="precisión", title="Precisión–recall")
    axes[1].plot([0, 1], [0, 1], ls=":", c="grey")
    axes[1].set(xlabel="1 - especificidad", ylabel="sensibilidad", title="ROC")
    for ax in axes:
        ax.legend(fontsize=8)
    _guardar(fig, destino)


def calibracion(y, probas: dict, destino) -> None:
    fig, ax = plt.subplots(figsize=(5.5, 5))
    for nombre, p in probas.items():
        fp, mp = calibration_curve(y, p, n_bins=10, strategy="quantile")
        ax.plot(mp, fp, marker="o", label=nombre)
    lim = max(0.4, float(np.max([np.max(p) for p in probas.values()])))
    ax.plot([0, lim], [0, lim], ls=":", c="grey", label="perfecta")
    ax.set(xlabel="probabilidad predicha", ylabel="frecuencia observada",
           title="Calibración (deciles)")
    ax.legend(fontsize=8)
    _guardar(fig, destino)


def equidad(tabla, destino) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    etiquetas = [f"{r.variable}={r.grupo}" for r in tabla.itertuples()]
    colores = ["#4472C4" if ok else "#BBBBBB" for ok in tabla["n_suficiente"]]
    ax.barh(etiquetas, tabla["sensibilidad_at_k"] * 100, color=colores)
    ax.set_xlabel("sensibilidad dentro del grupo en el top-K global (%)")
    ax.set_title("Auditoría de equidad (gris = n insuficiente)")
    ax.invert_yaxis()
    _guardar(fig, destino)


def importancia(tabla, destino, top: int = 15) -> None:
    t = tabla.head(top).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(t["variable"], t["importancia_media"], xerr=t["importancia_std"], color="#2F5597")
    ax.set_xlabel("caída de AUCPR al permutar (test)")
    ax.set_title(f"Importancia por permutación (top {top})")
    _guardar(fig, destino)
