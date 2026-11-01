"""3.2 Limpiar · decisiones/0003-faltantes.

Responde, problema por problema, al plan de calidad de E2:

* ausencia alta (max_glu_serum, A1Cresult)  -> categoría "No medido" (ausencia informativa)
* medical_specialty / payer_code / race      -> categoría "Desconocido" (no se imputa)
* diag_1..3 faltantes                        -> "Desconocido"
* códigos NULL / Not Mapped / Not Available  -> código -1 ("Desconocido")
* atípicos IQR                               -> se registran; NO se recortan (datos válidos)

Salida documental: reportes/e3/limpieza.json (métrica DVC, comparable entre versiones).
"""
from __future__ import annotations

import numpy as np

import json

from p09.config import ruta
from p09.datos.comun import NUMERICAS_CRUDAS, escribir, leer, p, reporte

ENTRADA = "datos/intermedio/seleccionado.parquet"
SALIDA = "datos/intermedio/limpio.parquet"


def main() -> None:
    lim, sel = p("limpieza"), p("seleccion")
    df = leer(ENTRADA)
    falt_antes = (df.isna().mean() * 100).round(3)
    acciones: dict = {}

    # 1 · Ausencia informativa: no se imputa con moda/mediana
    for c in lim["columnas_ausencia_informativa"]:
        if c in df.columns:
            token = lim["token_no_medido"] if c in lim["columnas_no_medido"] else lim["token_faltante"]
            n = int(df[c].isna().sum())
            df[c] = df[c].fillna(token).astype("string")
            acciones[c] = {"faltantes": n, "accion": f"categoria '{token}'",
                           "pct": round(n / len(df) * 100, 3)}

    # 2 · Diagnósticos y auditoría: categoría explícita
    for c in ["diag_1", "diag_2", "diag_3", *sel["columnas_auditoria"]]:
        if c in df.columns:
            n = int(df[c].isna().sum())
            df[c] = df[c].fillna(lim["token_faltante"]).astype("string")
            acciones[c] = {"faltantes": n, "accion": "categoria 'Desconocido'",
                           "pct": round(n / len(df) * 100, 3)}

    # 3 · Códigos administrativos sin significado -> -1
    for col, clave in [("admission_type_id", "admission_type_desconocido"),
                       ("admission_source_id", "admission_source_desconocido"),
                       ("discharge_disposition_id", "discharge_desconocido")]:
        m = df[col].isin(lim[clave])
        df.loc[m, col] = -1
        acciones[col] = {"recodificados_a_-1": int(m.sum()), "pct": round(float(m.mean() * 100), 3)}

    # 4 · Faltantes residuales: NO se imputan aquí (sería ajustar con todo el
    #     conjunto antes de partir = fuga). Se dejan para el SimpleImputer del
    #     pipeline de E4, que aprende solo con train. Solo se registran.
    residuales = {c: int(n) for c, n in df.isna().sum().items() if n > 0}
    for c, n in residuales.items():
        if n / len(df) > lim["umbral_no_imputar"]:
            raise ValueError(f"{c}: {n/len(df):.1%} faltante supera el umbral y no tiene regla")

    # 5 · Atípicos: solo registro
    atipicos = {}
    for c in NUMERICAS_CRUDAS:
        q1, q3 = df[c].quantile([0.25, 0.75])
        iqr = q3 - q1
        k = lim["regla_atipicos_iqr"]
        fuera = (df[c] < q1 - k * iqr) | (df[c] > q3 + k * iqr)
        atipicos[c] = {"n": int(fuera.sum()), "pct": round(float(fuera.mean() * 100), 3),
                       "min": float(df[c].min()), "max": float(df[c].max())}
        if lim["recortar_atipicos"]:
            df[c] = df[c].clip(q1 - k * iqr, q3 + k * iqr)

    # 6 · Tipos coherentes
    for c in NUMERICAS_CRUDAS:
        df[c] = df[c].astype("float64")

    # Respuesta al informe de calidad de E2, variable por variable
    cal = json.loads(ruta("reportes/e2/calidad.json").read_text(encoding="utf-8"))
    respuesta = []
    for var, pct in cal["faltantes_pct"].items():
        if var in sel["columnas_descartadas"]:
            dec = "descartada en 3.1"
        elif var in acciones:
            dec = acciones[var].get("accion", "recodificada")
        else:
            dec = "imputación en el pipeline de E4 (ajustada solo con train)"
        respuesta.append({"variable": var, "pct_faltante_e2": pct, "decision_e3": dec,
                          "pct_faltante_tras_e3": round(float(df[var].isna().mean() * 100), 3) if var in df else None})
    for c in cal["codigos_especiales"]:
        if c["variable"] in df.columns and c["n"] > 0:
            dec = ("excluido en 3.1" if c["codigo"] in sel["disposiciones_fallecimiento"]
                   else "recodificado a -1 (desconocido)")
            respuesta.append({"variable": f"{c['variable']}={c['codigo']}", "pct_faltante_e2": c["pct"],
                              "decision_e3": dec, "pct_faltante_tras_e3": None})
    for c in cal["constantes"]:
        respuesta.append({"variable": c, "pct_faltante_e2": 0, "decision_e3":
                          "descartada en 3.1 (constante)" if c in sel["columnas_descartadas"] else "PENDIENTE",
                          "pct_faltante_tras_e3": None})

    escribir(df, SALIDA)
    reporte({
        "respuesta_plan_calidad_e2": respuesta,
        "filas": len(df),
        "celdas_faltantes_despues": int(df.isna().sum().sum()),
        "faltantes_residuales_para_pipeline": residuales,
        "faltantes_antes_pct": {k: v for k, v in falt_antes.items() if v > 0},
        "acciones": acciones,
        "atipicos_iqr": atipicos,
        "atipicos_recortados": bool(lim["recortar_atipicos"]),
    }, "reportes/e3/limpieza.json")
    print(f"[3.2] {len(df):,} filas limpias; {len(acciones)} acciones registradas")


if __name__ == "__main__":
    main()
