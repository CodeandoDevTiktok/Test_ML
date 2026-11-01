"""Partición train/test agrupada por paciente · decisiones/0006-particion.

Se adelanta aquí (guía S03, «Fuga de información») para que nada de E4 se
ajuste con el conjunto de prueba. StratifiedGroupKFold garantiza a la vez:
mismo paciente nunca en ambos lados, y prevalencia similar en train y test.
"""
from __future__ import annotations

from sklearn.model_selection import StratifiedGroupKFold

from p09.datos.comun import escribir, leer, p, reporte

ENTRADA = "datos/final/tabla_modelado.parquet"


def main() -> None:
    cfg = p("particion")
    df = leer(ENTRADA)
    n_splits = max(2, round(1 / cfg["proporcion_prueba"]))
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=cfg["semilla"])
    idx_tr, idx_te = next(sgkf.split(df, df["reingreso_30d"], groups=df[cfg["agrupar_por"]]))
    tr, te = df.iloc[idx_tr].reset_index(drop=True), df.iloc[idx_te].reset_index(drop=True)

    solapados = set(tr[cfg["agrupar_por"]]) & set(te[cfg["agrupar_por"]])
    assert not solapados, f"{len(solapados)} pacientes en train y test"

    escribir(tr, "datos/particion/train.parquet")
    escribir(te, "datos/particion/test.parquet")
    reporte({
        "n_train": len(tr), "n_test": len(te),
        "pct_test": round(len(te) / len(df) * 100, 2),
        "pacientes_train": int(tr[cfg["agrupar_por"]].nunique()),
        "pacientes_test": int(te[cfg["agrupar_por"]].nunique()),
        "pacientes_solapados": len(solapados),
        "prevalencia_train_pct": round(float(tr["reingreso_30d"].mean() * 100), 3),
        "prevalencia_test_pct": round(float(te["reingreso_30d"].mean() * 100), 3),
    }, "reportes/e3/particion.json")
    print(f"[part] train={len(tr):,} test={len(te):,} solapados=0")


if __name__ == "__main__":
    main()
