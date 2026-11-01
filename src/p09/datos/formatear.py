"""3.5 Formatear · decisiones/0006-particion.

Cambios sintácticos que exige la herramienta: tipos, orden de columnas y ROL de
cada columna (id, predictora, auditoría, referencia, objetivo). Genera desde el
código —no a mano— el diccionario de datos (criterio de aceptación 5: 100 %
de columnas) y el esquema que leerá E4.
"""
from __future__ import annotations

import pandas as pd

from p09.datos.comun import MEDICAMENTOS, NUMERICAS_CRUDAS, escribir, leer, p, reporte
from p09.config import ruta

ENTRADA = "datos/intermedio/integrado.parquet"
SALIDA = "datos/final/tabla_modelado.parquet"
DICCIONARIO = "docs/diccionario/diccionario_datos.csv"

DESCRIPCIONES = {
    "encounter_id": "Identificador del episodio (sujeto de predicción)",
    "patient_nbr": "Identificador del paciente; solo para agrupar particiones",
    "race": "Raza registrada; SOLO auditoría de equidad (E1)",
    "gender": "Sexo registrado",
    "age": "Tramo de edad original (10 años)",
    "edad_num": "Punto medio del tramo de edad",
    "grupo_edad": "Tramo amplio de edad para auditoría",
    "admission_type_id": "Código original de tipo de admisión",
    "admission_type_grupo": "Tipo de admisión agrupado (IDS_mapping)",
    "admission_source_id": "Código original de fuente de admisión",
    "admission_source_grupo": "Fuente de admisión agrupada (IDS_mapping)",
    "discharge_disposition_id": "Código original de destino de alta",
    "discharge_disposition_grupo": "Destino de alta agrupado; predictor solo si params lo habilita",
    "time_in_hospital": "Días de estancia del episodio",
    "num_lab_procedures": "Número de pruebas de laboratorio",
    "num_procedures": "Número de procedimientos (no laboratorio)",
    "num_medications": "Número de medicamentos distintos administrados",
    "number_outpatient": "Visitas ambulatorias en el año previo",
    "number_emergency": "Visitas a emergencia en el año previo",
    "number_inpatient": "Hospitalizaciones en el año previo",
    "number_diagnoses": "Número de diagnósticos registrados",
    "visitas_previas_total": "Suma de visitas previas (ambulatorio+emergencia+hospital)",
    "hosp_previas_4mas": "1 si number_inpatient >= umbral clínico (params)",
    "payer_code": "Pagador; 'Desconocido' si faltaba",
    "medical_specialty": "Especialidad original; 'Desconocido' si faltaba",
    "especialidad_grupo": "Top-N especialidades; resto 'Otra'",
    "diag_1": "CIE-9 principal (referencia)", "diag_2": "CIE-9 secundario (referencia)",
    "diag_3": "CIE-9 terciario (referencia)",
    "diag_1_grupo": "Grupo clínico del diagnóstico principal",
    "diag_2_grupo": "Grupo clínico del diagnóstico secundario",
    "diag_3_grupo": "Grupo clínico del diagnóstico terciario",
    "diag_principal_diabetes": "1 si el diagnóstico principal es 250.xx",
    "max_glu_serum": "Glucosa sérica máxima; 'No medido' si no se midió",
    "A1Cresult": "Resultado HbA1c; 'No medido' si no se midió",
    "a1c_medido": "1 si se midió HbA1c", "glu_medido": "1 si se midió glucosa sérica",
    "n_meds_activos": "Medicamentos para diabetes con valor distinto de 'No'",
    "n_meds_cambiados": "Medicamentos con dosis 'Up' o 'Down'",
    "change": "Hubo cambio de medicación para diabetes",
    "diabetesMed": "Se prescribió medicación para diabetes",
    "reingreso_30d": "OBJETIVO: 1 si hubo reingreso antes de 30 días",
}
REFERENCIA = ["age", "medical_specialty", "diag_1", "diag_2", "diag_3",
              "admission_type_id", "admission_source_id", "discharge_disposition_id"]
DERIVADAS = {"edad_num", "grupo_edad", "visitas_previas_total", "hosp_previas_4mas",
             "n_meds_activos", "n_meds_cambiados", "a1c_medido", "glu_medido",
             "diag_1_grupo", "diag_2_grupo", "diag_3_grupo", "diag_principal_diabetes",
             "especialidad_grupo", "admission_type_grupo", "admission_source_grupo",
             "discharge_disposition_grupo", "reingreso_30d"}
ENTERAS_BINARIAS = {"hosp_previas_4mas", "a1c_medido", "glu_medido", "diag_principal_diabetes"}


def rol(col: str, auditoria: list[str]) -> str:
    if col in ("encounter_id", "patient_nbr"):
        return "id"
    if col == "reingreso_30d":
        return "objetivo"
    if col in auditoria or col == "grupo_edad":
        return "auditoria"
    if col in REFERENCIA:
        return "referencia"
    return "predictora"


def main() -> None:
    auditoria = p("seleccion")["columnas_auditoria"]
    df = leer(ENTRADA)
    roles = {c: rol(c, auditoria) for c in df.columns}

    numericas = [c for c in df.columns if roles[c] == "predictora" and
                 (c in NUMERICAS_CRUDAS or c in {"edad_num", "visitas_previas_total",
                                                 "n_meds_activos", "n_meds_cambiados"} | ENTERAS_BINARIAS)]
    categoricas = [c for c in df.columns if roles[c] == "predictora" and c not in numericas]
    for c in numericas:
        df[c] = df[c].astype("float64")
    for c in categoricas + [c for c, r in roles.items() if r in ("auditoria", "referencia")]:
        if c not in ("admission_type_id", "admission_source_id", "discharge_disposition_id"):
            df[c] = df[c].astype("string")
    df["reingreso_30d"] = df["reingreso_30d"].astype("int64")

    orden = (["encounter_id", "patient_nbr"] + numericas + categoricas
             + [c for c, r in roles.items() if r == "auditoria"]
             + [c for c, r in roles.items() if r == "referencia"] + ["reingreso_30d"])
    df = df[orden].sort_values("encounter_id").reset_index(drop=True)
    escribir(df, SALIDA)

    # Diccionario de datos generado (100 % de columnas)
    filas = []
    for c in df.columns:
        filas.append({
            "columna": c, "rol": roles[c],
            "tipo": "numerica" if c in numericas else str(df[c].dtype),
            "origen": "derivada" if c in DERIVADAS else ("cruda" if c not in MEDICAMENTOS else "cruda (medicamento)"),
            "descripcion": DESCRIPCIONES.get(c, f"Estado del medicamento {c} (No/Steady/Up/Down)"
                                             if c in MEDICAMENTOS else ""),
            "pct_faltante": round(float(df[c].isna().mean() * 100), 3),
            "cardinalidad": int(df[c].nunique()),
            "ejemplo": str(df[c].iloc[0]),
        })
    dic = pd.DataFrame(filas)
    ruta(DICCIONARIO).parent.mkdir(parents=True, exist_ok=True)
    dic.to_csv(ruta(DICCIONARIO), index=False)

    reporte({
        "filas": len(df), "columnas": df.shape[1],
        "numericas": numericas, "categoricas": categoricas,
        "auditoria": [c for c, r in roles.items() if r == "auditoria"],
        "referencia": [c for c, r in roles.items() if r == "referencia"],
        "objetivo": "reingreso_30d", "ids": ["encounter_id", "patient_nbr"],
        "cobertura_diccionario_pct": round(len(dic) / df.shape[1] * 100, 1),
    }, "reportes/e3/esquema.json")
    print(f"[3.5] tabla final {df.shape}; {len(numericas)} num + {len(categoricas)} cat")


if __name__ == "__main__":
    main()
