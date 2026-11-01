"""Optimización de hiperparámetros con Optuna, registrada en MLflow (E4).

Diseño (docs/decisiones/0008-optuna.md):

* Un ESTUDIO Optuna por algoritmo  ->  una ejecución MADRE en MLflow (tipo=estudio)
* Cada TRIAL                         ->  una ejecución HIJA (tipo=trial, nested=True)
* Objetivo: media de recall_at_k en StratifiedGroupKFold por paciente sobre TRAIN.
  El conjunto de prueba NO se toca aquí (se usa una sola vez en E5).
* El espacio incluye el PREPROCESADO (min_frequency del OneHot) junto al modelo.
* Poda (MedianPruner) tras cada pliegue: los trials podados se registran igual
  con estado=podado — un resultado negativo también es un hallazgo.
* cv_best_score de la madre está sesgado al alza (máximo de N intentos); la
  estimación honesta es la de test en E5.

Uso:
    python -m p09.modelado.optimizar                      # todos los de params.yaml
    python -m p09.modelado.optimizar --algoritmo hist_gb --n-trials 20
"""
from __future__ import annotations

import argparse
import json
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mlflow  # noqa: E402
import numpy as np  # noqa: E402
import optuna  # noqa: E402

from p09.config import PARAMS, ruta  # noqa: E402
from p09.modelado import registro  # noqa: E402
from p09.modelado.metricas import evaluar  # noqa: E402
from p09.modelado.pipeline import cargar, construir, pliegues, xy  # noqa: E402


def espacio(trial: optuna.Trial, algoritmo: str) -> dict:
    """Espacio de búsqueda: preprocesado + modelo."""
    hp = {"min_frequency": trial.suggest_categorical("min_frequency", [10, 50, 200])}
    if algoritmo == "logistica":
        hp["C"] = trial.suggest_float("C", 1e-3, 10.0, log=True)
        hp["class_weight"] = trial.suggest_categorical("class_weight", ["none", "balanced"])
    elif algoritmo == "random_forest":
        hp["n_estimators"] = trial.suggest_int("n_estimators", 100, 400, step=50)
        hp["max_depth"] = trial.suggest_int("max_depth", 4, 18)
        hp["min_samples_leaf"] = trial.suggest_int("min_samples_leaf", 5, 100, log=True)
        hp["max_features"] = trial.suggest_categorical("max_features", ["sqrt", 0.3, 0.5])
        hp["max_samples"] = trial.suggest_float("max_samples", 0.3, 0.9)
        hp["class_weight"] = trial.suggest_categorical("class_weight", ["none", "balanced_subsample"])
    elif algoritmo == "hist_gb":
        hp["learning_rate"] = trial.suggest_float("learning_rate", 0.02, 0.2, log=True)
        hp["max_iter"] = trial.suggest_int("max_iter", 100, 500, step=50)
        hp["max_leaf_nodes"] = trial.suggest_int("max_leaf_nodes", 15, 63)
        hp["min_samples_leaf"] = trial.suggest_int("min_samples_leaf", 20, 300, log=True)
        hp["l2_regularization"] = trial.suggest_float("l2_regularization", 1e-3, 10.0, log=True)
        hp["class_weight"] = trial.suggest_categorical("class_weight", ["none", "balanced"])
    else:
        raise ValueError(algoritmo)
    return hp


def hp_modelo(hp: dict) -> dict:
    """Optuna no admite None en categóricas: 'none' -> None."""
    return {k: (None if v == "none" else v) for k, v in hp.items()}


def optimizar(algoritmo: str, n_trials: int, timeout: int | None, version: str) -> dict:
    cfg = PARAMS["modelado"]
    X, y, g = xy(cargar("train"))
    folds = pliegues(y, g)
    k = registro.k_frac()

    sampler = optuna.samplers.TPESampler(seed=cfg["semilla"])
    pruner = (optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=1)
              if cfg["optuna"]["pruner"] == "median" else optuna.pruners.NopPruner())
    nombre_estudio = f"p09-{algoritmo}-{version}"
    db = ruta("optuna.db")
    estudio = optuna.create_study(study_name=nombre_estudio, direction="maximize",
                                  sampler=sampler, pruner=pruner,
                                  storage=f"sqlite:///{db.as_posix()}", load_if_exists=True)

    with registro.run(f"optuna-{algoritmo}-{version}", tipo="estudio", etapa="E4",
                      algoritmo=algoritmo, estudio=nombre_estudio) as madre:
        mlflow.log_params({"algoritmo": algoritmo, "n_trials": n_trials, "k_fraccion": k,
                           "n_train": len(y), "n_folds": len(folds), "sampler": "TPE",
                           "pruner": cfg["optuna"]["pruner"], "objetivo": "cv_recall_at_k_media",
                           "validacion": "StratifiedGroupKFold(patient_nbr)"})

        def objetivo(trial: optuna.Trial) -> float:
            hp = espacio(trial, algoritmo)
            with registro.run(f"{algoritmo}-t{trial.number:03d}", nested=True, tipo="trial",
                              etapa="E4", algoritmo=algoritmo, estudio=nombre_estudio,
                              trial=trial.number, run_madre=madre.info.run_id) as hija:
                mlflow.log_params({"algoritmo": algoritmo, "n_train": len(y), "k_fraccion": k,
                                   **{f"hp_{a}": b for a, b in hp.items()}})
                res, t0, podado = [], time.time(), False
                for i, (tr, va) in enumerate(folds):
                    pipe = construir(algoritmo, hp_modelo(hp)).fit(X.iloc[tr], y[tr])
                    s = pipe.predict_proba(X.iloc[va])[:, 1]
                    m = evaluar(y[va], s, k)
                    res.append(m)
                    mlflow.log_metric("fold_recall_at_k", m["recall_at_k"], step=i)
                    parcial = float(np.mean([r["recall_at_k"] for r in res]))
                    trial.report(parcial, i)
                    if trial.should_prune():
                        # se cierra la ejecución como FINISHED y se marca; luego se poda
                        mlflow.set_tag("estado", "podado")
                        mlflow.log_metric("cv_recall_at_k_parcial", parcial)
                        podado = True
                        break
                if not podado:
                    resumen = registro.log_cv(res)
                    mlflow.log_metric("seg_por_fold", (time.time() - t0) / len(folds))
                    mlflow.set_tag("estado", "completo")
                    trial.set_user_attr("mlflow_run_id", hija.info.run_id)
            if podado:
                raise optuna.TrialPruned()
            return resumen["cv_recall_at_k_media"]

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        estudio.optimize(objetivo, n_trials=n_trials, timeout=timeout, gc_after_trial=True,
                         catch=(ValueError,))

        mejor = estudio.best_trial
        mlflow.log_metric("cv_best_score", mejor.value)       # OPTIMISTA: solo para elegir
        mlflow.log_params({f"mejor_{a}": b for a, b in mejor.params.items()})
        mlflow.set_tags({"mejor_trial": mejor.number,
                         "mejor_run": mejor.user_attrs.get("mlflow_run_id", "")})
        estados = [t.state.name for t in estudio.trials]
        mlflow.log_metrics({"n_completos": estados.count("COMPLETE"),
                            "n_podados": estados.count("PRUNED")})
        _artefactos(estudio, algoritmo, version)

    salida = {"algoritmo": algoritmo, "estudio": nombre_estudio, "mejor_valor": mejor.value,
              "mejor_params": mejor.params, "mejor_run": mejor.user_attrs.get("mlflow_run_id")}
    print(f"  {algoritmo}: mejor cv recall@k = {mejor.value:.4f} (trial {mejor.number})")
    return salida


def _artefactos(estudio: optuna.Study, algoritmo: str, version: str) -> None:
    carpeta = ruta(f"reportes/e4/optuna_{algoritmo}")
    carpeta.mkdir(parents=True, exist_ok=True)
    estudio.trials_dataframe().to_csv(carpeta / "trials.csv", index=False)
    from optuna.visualization import matplotlib as ovm
    for nombre, fn in [("historia", ovm.plot_optimization_history),
                       ("importancia_hp", ovm.plot_param_importances)]:
        try:
            ax = fn(estudio)
            fig = ax.figure if hasattr(ax, "figure") else plt.gcf()
            fig.set_size_inches(8, 4.5)
            fig.tight_layout()
            fig.savefig(carpeta / f"{nombre}.png", dpi=120)
            plt.close("all")
        except Exception as e:  # p. ej. muy pocos trials para importancia
            print(f"    (sin gráfico {nombre}: {e})")
    mlflow.log_artifacts(str(carpeta), artifact_path=f"optuna_{algoritmo}")


def main(argv=None) -> list[dict]:
    cfg = PARAMS["modelado"]
    ap = argparse.ArgumentParser()
    ap.add_argument("--algoritmo", choices=cfg["algoritmos"], action="append")
    ap.add_argument("--n-trials", type=int, default=cfg["optuna"]["n_trials"])
    ap.add_argument("--timeout", type=int, default=cfg["optuna"]["timeout_segundos"])
    a = ap.parse_args(argv)
    from p09.procedencia import procedencia
    version = procedencia()["version_datos"]
    res = [optimizar(alg, a.n_trials, a.timeout, version) for alg in (a.algoritmo or cfg["algoritmos"])]
    destino = ruta("reportes/e4/optuna_resumen.json")
    destino.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    return res


if __name__ == "__main__":
    main()
