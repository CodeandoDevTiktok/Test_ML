"""Etapa 5 · Evaluación (CRISP-DM 5.1 evaluar resultados, 5.2 revisar proceso).

Secuencia (docs/decisiones/0009-criterios-evaluacion.md):

1. FILTRAR y luego ORDENAR: trials completos de la versión de datos actual.
2. Elegir campeón por CV con la regla de un error estándar (el más simple
   cuyo recall@k está a <= 1 EE del mejor). El test aún no se ha mirado.
3. Reentrenar el campeón con todo train y CALIBRAR (validación agrupada).
4. Usar TEST UNA SOLA VEZ: campeón + B0/B1/B2, IC 95 % por bootstrap de pacientes.
5. Contrastar con los criterios de éxito de E1 y la auditoría de equidad.
6. Registrar el modelo con alias @campeon y un run reporte-final con artefactos.
"""
from __future__ import annotations

import argparse
import json
import math

import mlflow
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.calibration import CalibratedClassifierCV
from sklearn.inspection import permutation_importance

from p09.config import ALIAS_CAMPEON, EXPERIMENTO, MODELO_REGISTRADO, PARAMS, ruta
from p09.evaluacion import figuras
from p09.modelado import registro
from p09.modelado.baselines import BASELINES, puntuar
from p09.modelado.metricas import bootstrap_por_paciente, evaluar
from p09.modelado.optimizar import hp_modelo
from p09.modelado.pipeline import cargar, construir, pliegues, xy
from p09.procedencia import procedencia

SIMPLICIDAD = {"logistica": 0, "hist_gb": 1, "random_forest": 2}
DIR = "reportes/e5"


# ----------------------------------------------------------------- 1 · selección
def trials_version(version: str) -> pd.DataFrame:
    registro.iniciar()
    exp = mlflow.get_experiment_by_name(EXPERIMENTO)
    df = mlflow.search_runs(
        experiment_ids=[exp.experiment_id],
        # filtro por IGUALDAD (una etiqueta ausente no satisface '!=')
        filter_string=(f"attributes.status = 'FINISHED' and tags.tipo = 'trial' "
                       f"and tags.estado = 'completo' and tags.version_datos = '{version}'"),
        order_by=["metrics.cv_recall_at_k_media DESC"],
        max_results=5000,
    )
    if df.empty:
        raise RuntimeError(f"No hay trials completos para version_datos={version}. Ejecute E4.")
    return df


def elegir_campeon(df: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    n_folds = PARAMS["modelado"]["n_folds"]
    mejores = (df.sort_values("metrics.cv_recall_at_k_media", ascending=False)
                 .groupby("tags.algoritmo", as_index=False).head(1).copy())
    mejores["ee"] = mejores["metrics.cv_recall_at_k_std"] / math.sqrt(n_folds)
    top = mejores.iloc[0]
    umbral = top["metrics.cv_recall_at_k_media"] - top["ee"]
    mejores["dentro_1ee"] = mejores["metrics.cv_recall_at_k_media"] >= umbral
    mejores["simplicidad"] = mejores["tags.algoritmo"].map(SIMPLICIDAD)
    candidatos = mejores[mejores["dentro_1ee"]].sort_values(
        ["simplicidad", "metrics.cv_recall_at_k_media"], ascending=[True, False])
    return candidatos.iloc[0], mejores


def hp_de_run(fila: pd.Series) -> dict:
    hp = {}
    for col, v in fila.items():
        if col.startswith("params.hp_") and v is not None and not (isinstance(v, float) and np.isnan(v)):
            nombre = col.replace("params.hp_", "")
            hp[nombre] = _tipar(v)
    return hp_modelo(hp)


def _tipar(v: str):
    if v in ("None", "none"):
        return "none"
    for t in (int, float):
        try:
            x = t(v)
            if t is float or str(x) == v:
                return x
        except (TypeError, ValueError):
            pass
    return v


# ----------------------------------------------------------------- 4/5 · test
def equidad(test: pd.DataFrame, score: np.ndarray, k: float) -> tuple[pd.DataFrame, float]:
    ev = PARAMS["evaluacion"]
    n = len(score)
    marca = np.zeros(n, bool)
    marca[np.argsort(-score, kind="stable")[: max(1, math.ceil(k * n))]] = True
    filas = []
    for var in ev["grupos_auditoria"]:
        for grupo, idx in test.groupby(var).groups.items():
            pos = test.index.get_indexer(idx)
            y = test["reingreso_30d"].to_numpy()[pos]
            filas.append({
                "variable": var, "grupo": str(grupo), "n": len(pos),
                "prevalencia": float(y.mean()),
                "pct_priorizado": float(marca[pos].mean()),
                "sensibilidad_at_k": float(marca[pos][y == 1].mean()) if y.sum() else np.nan,
                "n_positivos": int(y.sum()),
                "n_suficiente": bool(len(pos) >= ev["n_min_grupo"] and y.sum() >= 30),
            })
    t = pd.DataFrame(filas)
    ok = t[t["n_suficiente"]]
    brecha = float((ok.groupby("variable")["sensibilidad_at_k"].agg(lambda s: s.max() - s.min())).max() * 100)
    return t, brecha


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-registro", action="store_true", help="no registra en Model Registry")
    ap.add_argument("--sin-importancia", action="store_true")
    a = ap.parse_args(argv)

    ev = PARAMS["evaluacion"]
    k = float(ev["k_fraccion"])
    proc = procedencia()
    version = proc["version_datos"]
    carpeta = ruta(DIR)
    carpeta.mkdir(parents=True, exist_ok=True)

    # 1-2 · selección por CV (test sin mirar)
    trials = trials_version(version)
    campeon, mejores = elegir_campeon(trials)
    alg = campeon["tags.algoritmo"]
    hp = hp_de_run(campeon)
    print(f"[E5] campeón por CV: {alg} (run {campeon['run_id'][:8]}) hp={hp}")
    mejores[["tags.algoritmo", "run_id", "metrics.cv_recall_at_k_media", "metrics.cv_recall_at_k_std",
             "ee", "dentro_1ee", "metrics.cv_aucpr_media"]].to_csv(carpeta / "seleccion_cv.csv", index=False)

    # 3 · reentrenar + calibrar con todo train (pliegues agrupados)
    tr_df, te_df = cargar("train"), cargar("test")
    Xtr, ytr, gtr = xy(tr_df)
    Xte, yte, gte = xy(te_df)
    base = construir(alg, hp)
    calibrado = CalibratedClassifierCV(base, method=ev["calibracion"], cv=pliegues(ytr, gtr), ensemble=True)
    calibrado.fit(Xtr, ytr)
    sin_cal = construir(alg, hp).fit(Xtr, ytr)

    # 4 · TEST, una sola vez
    p_cal = calibrado.predict_proba(Xte)[:, 1]
    p_sin = sin_cal.predict_proba(Xte)[:, 1]
    scores = {"campeon_calibrado": p_cal, "campeon_sin_calibrar": p_sin}
    for b in BASELINES:
        scores[b], _ = puntuar(b, Xtr, ytr, Xte)
    metricas = {n: evaluar(yte, s, k, probabilidades=(n != "b2_regla")) for n, s in scores.items()}
    sens_k = {f"recall_at_k_{int(kk*100)}": evaluar(yte, p_cal, kk)["recall_at_k"] for kk in ev["k_sensibilidad"]}
    ic = bootstrap_por_paciente(yte, p_cal, gte, k, n=ev["bootstrap_iteraciones"])
    tabla_eq, brecha = equidad(te_df.reset_index(drop=True), p_cal, k)

    # 5 · criterios de éxito (E1 salida 10)
    mejor_base = max(BASELINES, key=lambda b: metricas[b]["recall_at_k"])
    r_c, r_b = metricas["campeon_calibrado"]["recall_at_k"], metricas[mejor_base]["recall_at_k"]
    criterios = {
        "C1_recall_at_k_supera_mejor_baseline_10pct": {
            "valor": round(r_c, 4), "referencia": f"{mejor_base}={r_b:.4f}",
            "mejora_relativa": round(r_c / r_b - 1, 4),
            "cumple": bool(r_c >= r_b * (1 + ev["mejora_minima_vs_baseline"]))},
        "C2_aucpr_1_5x_prevalencia": {
            "valor": round(metricas["campeon_calibrado"]["aucpr_sobre_prevalencia"], 3),
            "umbral": ev["aucpr_min_vs_prevalencia"],
            "cumple": bool(metricas["campeon_calibrado"]["aucpr_sobre_prevalencia"] >= ev["aucpr_min_vs_prevalencia"])},
        "C3_calibracion_no_peor_que_B1": {
            "brier_campeon": round(metricas["campeon_calibrado"]["brier"], 5),
            "brier_b1": round(metricas["b1_logistica"]["brier"], 5),
            "pendiente": round(metricas["campeon_calibrado"]["cal_pendiente"], 3),
            "cumple": bool(metricas["campeon_calibrado"]["brier"] <= metricas["b1_logistica"]["brier"] * 1.02)},
        "C4_brecha_sensibilidad_pp": {
            "valor": round(brecha, 2), "umbral": ev["brecha_max_sensibilidad_pp"],
            "cumple": bool(brecha <= ev["brecha_max_sensibilidad_pp"])},
    }
    veredicto = ("CUMPLE" if all(c["cumple"] for c in criterios.values()) else
                 "CUMPLE CON MITIGACIONES" if criterios["C2_aucpr_1_5x_prevalencia"]["cumple"] else
                 "NO CUMPLE: renegociar alcance")

    # Traducción al negocio: por cada 100 altas elegibles
    prev = float(yte.mean())
    negocio = {
        "altas": 100, "cupos_K": round(100 * k, 1),
        "reingresos_esperados": round(100 * prev, 2),
        "capturados_campeon": round(100 * prev * r_c, 2),
        "capturados_mejor_baseline": round(100 * prev * r_b, 2),
        "capturados_azar": round(100 * prev * k, 2),
        "reingresos_adicionales_vs_baseline": round(100 * prev * (r_c - r_b), 2),
    }

    # Figuras
    figuras.curva_ganancia(yte, {"campeón": p_cal, "B1 logística": scores["b1_logistica"],
                                 "B2 regla": scores["b2_regla"]}, k, carpeta / "ganancia.png")
    figuras.curvas_pr_roc(yte, {"campeón": p_cal, "B1": scores["b1_logistica"], "B2": scores["b2_regla"]},
                          carpeta / "pr_roc.png")
    figuras.calibracion(yte, {"calibrado": p_cal, "sin calibrar": p_sin, "B1": scores["b1_logistica"]},
                        carpeta / "calibracion.png")
    figuras.equidad(tabla_eq, carpeta / "equidad.png")
    tabla_eq.to_csv(carpeta / "equidad.csv", index=False)

    imp = None
    if not a.sin_importancia:
        rng = np.random.default_rng(PARAMS["modelado"]["semilla"])
        idx = rng.choice(len(Xte), size=min(8000, len(Xte)), replace=False)
        pi = permutation_importance(sin_cal, Xte.iloc[idx], yte[idx], scoring="average_precision",
                                    n_repeats=5, random_state=PARAMS["modelado"]["semilla"], n_jobs=-1)
        imp = (pd.DataFrame({"variable": Xte.columns, "importancia_media": pi.importances_mean,
                             "importancia_std": pi.importances_std})
               .sort_values("importancia_media", ascending=False))
        imp.to_csv(carpeta / "importancia_permutacion.csv", index=False)
        figuras.importancia(imp, carpeta / "importancia.png")

    resultado = {"version_datos": version, "campeon": {"algoritmo": alg, "hp": hp, "run_origen": campeon["run_id"],
                 "cv_recall_at_k": float(campeon["metrics.cv_recall_at_k_media"])},
                 "k_fraccion": k, "test": metricas, "sensibilidad_k": sens_k, "ic95_bootstrap": ic,
                 "criterios": criterios, "veredicto": veredicto, "negocio_por_100_altas": negocio,
                 "brecha_sensibilidad_pp": brecha, "procedencia": proc}
    (carpeta / "evaluacion.json").write_text(json.dumps(resultado, indent=2, default=str), encoding="utf-8")
    _resumen_md(resultado, carpeta / "resumen_evaluacion.md")

    # 6 · MLflow: campeón registrado + reporte-final
    with registro.run(f"campeon-{alg}-{version}", tipo="campeon", etapa="E5", algoritmo=alg,
                      run_origen=campeon["run_id"], veredicto=veredicto):
        mlflow.log_params({"algoritmo": alg, "calibracion": ev["calibracion"], "k_fraccion": k,
                           "n_train": len(ytr), "n_test": len(yte), **{f"hp_{x}": y for x, y in hp.items()}})
        mlflow.log_metrics({f"test_{m}": v for m, v in metricas["campeon_calibrado"].items()})
        mlflow.log_metrics({f"test_{m}": v for m, v in {**sens_k, **ic}.items()})
        mlflow.log_metric("test_brecha_sensibilidad_pp", brecha)
        for b in BASELINES:
            mlflow.log_metric(f"test_{b}_recall_at_k", metricas[b]["recall_at_k"])
        ds = mlflow.data.from_pandas(te_df.head(1000), source="datos/particion/test.parquet",
                                     name=f"p09-test-{version}", targets="reingreso_30d")
        mlflow.log_input(ds, context="test")
        firma = infer_signature(Xte.head(200), p_cal[:200])
        kwargs = dict(signature=firma, input_example=Xte.head(3),
                      pyfunc_predict_fn="predict_proba", serialization_format="cloudpickle")
        # MLflow 3.x usa `name`; MLflow 2.x usa `artifact_path`
        if int(mlflow.__version__.split(".")[0]) >= 3:
            kwargs["name"] = "modelo"
        else:
            kwargs["artifact_path"] = "modelo"
        if not a.sin_registro:
            kwargs["registered_model_name"] = MODELO_REGISTRADO
        info = mlflow.sklearn.log_model(calibrado, **kwargs)

        version_modelo = getattr(info, "registered_model_version", None)
        if not a.sin_registro and version_modelo is None:
            # Respaldo: en algunas versiones 2.x el ModelInfo no trae la versión
            cli_ = mlflow.MlflowClient()
            vs = cli_.search_model_versions(f"name='{MODELO_REGISTRADO}'")
            if vs:
                version_modelo = max(vs, key=lambda v: int(v.version)).version
        if not a.sin_registro and version_modelo:
            cli = mlflow.MlflowClient()
            cli.set_registered_model_alias(MODELO_REGISTRADO, ALIAS_CAMPEON, version_modelo)
            cli.set_model_version_tag(MODELO_REGISTRADO, version_modelo, "veredicto", veredicto)
            cli.set_model_version_tag(MODELO_REGISTRADO, version_modelo, "version_datos", version)
            print(f"[E5] registrado {MODELO_REGISTRADO} v{version_modelo} @{ALIAS_CAMPEON}")

    _reporte_final(version, carpeta)
    print(f"[E5] veredicto: {veredicto}")
    return resultado


def _reporte_final(version: str, carpeta) -> None:
    """El reporte también es una ejecución (guía S04, paso 14)."""
    exp = mlflow.get_experiment_by_name(EXPERIMENTO)
    todos = mlflow.search_runs([exp.experiment_id], max_results=5000,
                               filter_string=f"tags.version_datos = '{version}' and tags.tipo = 'trial'")
    cols = [c for c in ["run_id", "tags.mlflow.runName", "tags.algoritmo", "tags.estado",
                        "metrics.cv_recall_at_k_media", "metrics.cv_aucpr_media", "metrics.cv_roc_auc_media",
                        "metrics.cv_brier_media"] if c in todos.columns]
    ranking = todos[cols].sort_values("metrics.cv_recall_at_k_media", ascending=False)
    ranking.to_csv(carpeta / "ranking_trials.csv", index=False)
    resumen = (ranking[ranking["tags.estado"] == "completo"]
               .groupby("tags.algoritmo")["metrics.cv_recall_at_k_media"]
               .agg(["count", "mean", "max"]).round(4))
    resumen.to_csv(carpeta / "resumen_por_algoritmo.csv")
    with registro.run(f"reporte-final-{version}", tipo="reporte", etapa="E5"):
        mlflow.log_metric("n_trials", len(ranking))
        mlflow.log_metric("n_trials_completos", int((ranking["tags.estado"] == "completo").sum()))
        mlflow.log_artifacts(str(carpeta), artifact_path="reporte")


def _resumen_md(r: dict, destino) -> None:
    t = r["test"]["campeon_calibrado"]
    lin = [f"# Resumen de evaluación (E5) · datos {r['version_datos']}", "",
           f"**Campeón:** `{r['campeon']['algoritmo']}` · recall@K CV = {r['campeon']['cv_recall_at_k']:.4f}",
           f"**Veredicto:** {r['veredicto']}", "",
           "| Modelo (test) | Recall@K | Precision@K | AUCPR | ROC-AUC |", "|---|---:|---:|---:|---:|"]
    for n, m in r["test"].items():
        lin.append(f"| {n} | {m['recall_at_k']:.4f} | {m['precision_at_k']:.4f} | {m['aucpr']:.4f} | {m['roc_auc']:.4f} |")
    ic = r["ic95_bootstrap"]
    lin += ["", f"IC 95 % Recall@K (bootstrap de pacientes): [{ic['recall_at_k_ic_inf']:.4f}, {ic['recall_at_k_ic_sup']:.4f}]",
            f"Brier = {t.get('brier', float('nan')):.4f} · pendiente calibración = {t.get('cal_pendiente', float('nan')):.3f}", "",
            "## Criterios de éxito (E1)", ""]
    for n, c in r["criterios"].items():
        lin.append(f"- **{n}**: {'✅' if c['cumple'] else '❌'} {json.dumps({k: v for k, v in c.items() if k != 'cumple'}, ensure_ascii=False)}")
    ng = r["negocio_por_100_altas"]
    lin += ["", "## Traducción al negocio (por cada 100 altas elegibles)", "",
            f"Con {ng['cupos_K']} cupos: el modelo captura {ng['capturados_campeon']} de {ng['reingresos_esperados']} "
            f"reingresos esperados; el mejor baseline {ng['capturados_mejor_baseline']}; el azar {ng['capturados_azar']}."]
    destino.write_text("\n".join(lin), encoding="utf-8")


if __name__ == "__main__":
    main()
