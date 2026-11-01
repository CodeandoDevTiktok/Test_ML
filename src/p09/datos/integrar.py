"""3.4 Integrar · decisiones/0005-integracion.

Combina la tabla de episodios con el diccionario IDS_mapping.csv (tres bloques
concatenados, ver E2 §2.1) y agrupa los códigos administrativos en categorías
legibles. NO se agregan episodios por paciente: sin fechas, contar "episodios
del paciente" incluiría episodios FUTUROS (fuga de la ventana de resultado).

Salida documental: reportes/e3/integracion.json (cobertura del mapeo).
"""
from __future__ import annotations

import pandas as pd

from p09.datos.comun import escribir, leer, p, reporte
from p09.config import ruta

ENTRADA = "datos/intermedio/construido.parquet"
SALIDA = "datos/intermedio/integrado.parquet"
VARIABLES = ["admission_type_id", "discharge_disposition_id", "admission_source_id"]


def leer_mapping(rel: str) -> pd.DataFrame:
    """Separa el CSV concatenado en (variable, codigo, description) — igual que E2."""
    crudo = pd.read_csv(ruta(rel), header=None, names=["codigo", "description"],
                        dtype="string", keep_default_na=False)
    filas, actual = [], None
    for cod, desc in zip(crudo["codigo"].str.strip(), crudo["description"].str.strip()):
        if cod in VARIABLES and desc == "description":
            actual = cod
        elif actual and cod:
            filas.append({"variable": actual, "codigo": int(cod), "description": desc})
    return pd.DataFrame(filas)


def _grupo(variable: str, desc: str) -> str:
    d = (desc or "").lower()
    if any(t in d for t in ("null", "not mapped", "not available", "unknown", "invalid")) or d == "":
        return "desconocido"
    if variable == "admission_type_id":
        for clave in ("emergency", "urgent", "elective", "trauma", "newborn"):
            if clave in d:
                return clave
        return "otro"
    if variable == "admission_source_id":
        if "referral" in d:
            return "referencia"
        if "emergency" in d:
            return "emergencia"
        if "transfer" in d:
            return "traslado"
        return "otro"
    # discharge_disposition_id
    if "home health" in d or "home under care" in d:
        return "domicilio_con_servicio"
    if "home" in d and "hospice" not in d:
        return "domicilio"
    if "snf" in d or "skilled nursing" in d or "icf" in d or "nursing" in d:
        return "centro_enfermeria"
    if "rehab" in d:
        return "rehabilitacion"
    if "transfer" in d or "short term" in d:
        return "traslado"
    return "otro"


def main() -> None:
    integ = p("integracion")
    df = leer(ENTRADA)
    cobertura = {}
    if integ["usar_descripciones_mapping"]:
        mp = leer_mapping(p("datos")["archivo_mapping"])
        for var in VARIABLES:
            sub = mp[mp.variable == var]
            mapa = {int(r.codigo): _grupo(var, r.description) for r in sub.itertuples()}
            mapa[-1] = "desconocido"           # recodificados en 3.2
            nombre = var.replace("_id", "_grupo")
            df[nombre] = df[var].astype(int).map(mapa).fillna("sin_mapeo").astype("string")
            cobertura[var] = {
                "codigos_en_mapping": int(len(sub)),
                "pct_filas_mapeadas": round(float(df[nombre].ne("sin_mapeo").mean() * 100), 3),
                "categorias": df[nombre].value_counts().to_dict(),
            }
    escribir(df, SALIDA)
    reporte({"filas": len(df), "cobertura_mapping": cobertura,
             "agregados_por_paciente": integ["agregados_por_paciente"]},
            "reportes/e3/integracion.json")
    print(f"[3.4] integrado: {df.shape}")


if __name__ == "__main__":
    main()
