"""3.1 Seleccionar · decisiones/0001-elegibilidad y 0002-columnas.

Qué filas y qué columnas entran. Salida documental: justificación de inclusión
y exclusión (reportes/e3/seleccion.json), una cifra por cada regla aplicada.
"""
from __future__ import annotations

import json

from p09.config import ruta
from p09.datos.comun import escribir, leer, md5_archivo, normalizar_faltantes, p, reporte

SALIDA = "datos/intermedio/seleccionado.parquet"


def main() -> None:
    d, s = p("datos"), p("seleccion")
    df = normalizar_faltantes(leer(d["archivo_crudo"]))
    n0 = len(df)

    # Contrato E2 -> E3: el crudo que se prepara es EXACTAMENTE el que E2 describió
    e2 = json.loads(ruta("reportes/e2/descripcion.json").read_text(encoding="utf-8"))
    md5 = md5_archivo(d["archivo_crudo"])
    if md5 != e2["md5_crudo"] or n0 != e2["filas"]:
        raise SystemExit(f"El crudo (md5 {md5[:10]}, {n0} filas) no es el que describió E2 "
                         f"(md5 {e2['md5_crudo'][:10]}, {e2['filas']} filas): python tareas.py importar-e2 --tag <crudo-vN>")
    log: dict = {"filas_crudo": n0, "columnas_crudo": df.shape[1], "exclusiones": {},
                 "contrato_e2": {"md5_crudo": md5, "filas_e2": e2["filas"], "verificado": True}}

    disp = df["discharge_disposition_id"]
    reglas = {"fallecimiento": disp.isin(s["disposiciones_fallecimiento"])}
    if s["excluir_hospicio"]:
        reglas["hospicio"] = disp.isin(s["disposiciones_hospicio"])
    if s["excluir_alta_voluntaria"]:
        reglas["alta_voluntaria"] = disp.isin(s["disposiciones_alta_voluntaria"])
    if s["excluir_genero_invalido"]:
        reglas["genero_invalido"] = df["gender"].eq("Unknown/Invalid")

    excluir = None
    for nombre, mascara in reglas.items():
        nuevas = mascara if excluir is None else (mascara & ~excluir)
        log["exclusiones"][nombre] = {
            "filas": int(nuevas.sum()),
            "pct_crudo": round(float(nuevas.mean() * 100), 3),
            "tasa_lt30_en_excluidas": round(
                float(df.loc[mascara, d["columna_resultado"]].eq(d["valor_positivo"]).mean() * 100), 3
            ) if mascara.any() else None,
        }
        excluir = mascara if excluir is None else (excluir | mascara)

    df = df.loc[~excluir].copy()
    cols_out = [c for c in s["columnas_descartadas"] if c in df.columns]
    df = df.drop(columns=cols_out)

    log.update({
        "filas_seleccionadas": len(df),
        "pct_conservado": round(len(df) / n0 * 100, 3),
        "columnas_descartadas": cols_out,
        "columnas_resultantes": df.shape[1],
        "pacientes_unicos": int(df[d["id_paciente"]].nunique()),
        "prevalencia_lt30_pct": round(float(df[d["columna_resultado"]].eq(d["valor_positivo"]).mean() * 100), 3),
    })
    escribir(df, SALIDA)
    reporte(log, "reportes/e3/seleccion.json")
    print(f"[3.1] {n0:,} -> {len(df):,} filas; {len(cols_out)} columnas descartadas")


if __name__ == "__main__":
    main()
