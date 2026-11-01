"""3.3 Construir · decisiones/0004-variables-derivadas.

Atributos derivados (todos conocidos AL MOMENTO DEL ALTA — ventana de observación):

* reingreso_30d             objetivo binario (readmitted == '<30'); se elimina readmitted
* edad_num / grupo_edad     punto medio del tramo / tramo amplio para auditoría
* visitas_previas_total     outpatient + emergency + inpatient (año previo)
* hosp_previas_4mas         señal clínica de la consulta (E1): >= 4 hospitalizaciones
* n_meds_activos            medicamentos con valor distinto de 'No'
* n_meds_cambiados          medicamentos con 'Up' o 'Down' durante el episodio
* a1c_medido / glu_medido   la medición se hizo (ausencia = señal de proceso)
* diag_k_grupo              agrupación clínica CIE-9 (cie9.py)
* diag_principal_diabetes   diag_1 es 250.xx
* especialidad_grupo        top-N especialidades; el resto 'Otra'

Salida documental: reportes/e3/construccion.json.
"""
from __future__ import annotations

import numpy as np

from p09.datos.cie9 import VERSION_DICCIONARIO, agrupar
from p09.datos.comun import MEDICAMENTOS, escribir, leer, p, reporte

ENTRADA = "datos/intermedio/limpio.parquet"
SALIDA = "datos/intermedio/construido.parquet"


def _edad_media(tramo: str) -> float:
    # "[70-80)" -> 75.0
    a, b = tramo.strip("[)").split("-")
    return (float(a) + float(b)) / 2


def _grupo_edad(e: float) -> str:
    if e < 40:
        return "<40"
    if e < 60:
        return "40-59"
    if e < 80:
        return "60-79"
    return "80+"


def main() -> None:
    d, c = p("datos"), p("construccion")
    df = leer(ENTRADA)
    nuevas: list[str] = []

    # Objetivo
    df["reingreso_30d"] = df[d["columna_resultado"]].eq(d["valor_positivo"]).astype("int64")
    df = df.drop(columns=[d["columna_resultado"]])  # el resultado crudo NO entra
    nuevas.append("reingreso_30d")

    # Edad
    df["edad_num"] = df["age"].astype(str).map(_edad_media)
    df["grupo_edad"] = df["edad_num"].map(_grupo_edad).astype("string")
    nuevas += ["edad_num", "grupo_edad"]

    # Utilización previa
    df["visitas_previas_total"] = df[["number_outpatient", "number_emergency", "number_inpatient"]].sum(axis=1)
    df["hosp_previas_4mas"] = (df["number_inpatient"] >= c["umbral_hospitalizaciones_previas"]).astype("int64")
    nuevas += ["visitas_previas_total", "hosp_previas_4mas"]

    # Medicación
    meds = [m for m in MEDICAMENTOS if m in df.columns]
    m = df[meds].astype("string")
    df["n_meds_activos"] = m.ne("No").sum(axis=1).astype("int64")
    df["n_meds_cambiados"] = m.isin(["Up", "Down"]).sum(axis=1).astype("int64")
    nuevas += ["n_meds_activos", "n_meds_cambiados"]

    # Mediciones de laboratorio
    df["a1c_medido"] = df["A1Cresult"].ne("No medido").astype("int64")
    df["glu_medido"] = df["max_glu_serum"].ne("No medido").astype("int64")
    nuevas += ["a1c_medido", "glu_medido"]

    # Diagnósticos
    if c["agrupar_diagnosticos"]:
        for k in (1, 2, 3):
            df[f"diag_{k}_grupo"] = agrupar(df[f"diag_{k}"])
            nuevas.append(f"diag_{k}_grupo")
    df["diag_principal_diabetes"] = df["diag_1"].astype(str).str.startswith("250").astype("int64")
    nuevas.append("diag_principal_diabetes")

    # Especialidad
    top = (df.loc[df["medical_specialty"] != "Desconocido", "medical_specialty"]
           .value_counts().head(c["top_especialidades"]).index)
    df["especialidad_grupo"] = np.where(
        df["medical_specialty"].eq("Desconocido"), "Desconocido",
        np.where(df["medical_specialty"].isin(top), df["medical_specialty"], "Otra"))
    df["especialidad_grupo"] = df["especialidad_grupo"].astype("string")
    nuevas.append("especialidad_grupo")

    escribir(df, SALIDA)
    reporte({
        "filas": len(df),
        "atributos_derivados": nuevas,
        "n_atributos_derivados": len(nuevas),
        "diccionario_cie9": VERSION_DICCIONARIO,
        "prevalencia_objetivo_pct": round(float(df["reingreso_30d"].mean() * 100), 3),
        "pct_hosp_previas_4mas": round(float(df["hosp_previas_4mas"].mean() * 100), 3),
        "tasa_lt30_si_4mas": round(float(df.loc[df.hosp_previas_4mas == 1, "reingreso_30d"].mean() * 100), 3),
        "tasa_lt30_si_menos4": round(float(df.loc[df.hosp_previas_4mas == 0, "reingreso_30d"].mean() * 100), 3),
        "distribucion_diag1_grupo_pct": (df["diag_1_grupo"].value_counts(normalize=True) * 100).round(2).to_dict()
        if c["agrupar_diagnosticos"] else {},
        "especialidades_top": list(map(str, top)),
    }, "reportes/e3/construccion.json")
    print(f"[3.3] {len(nuevas)} atributos derivados")


if __name__ == "__main__":
    main()
