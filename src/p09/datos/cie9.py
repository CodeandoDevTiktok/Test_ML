"""Agrupación clínica de códigos CIE-9 · decisiones/0004-variables-derivadas.

Grupos según la consulta clínica (E1, salida 5): insuficiencia cardíaca,
piel/celulitis, neurología, infecciosas y subgrupos de diabetes reciben grupo
propio; el resto sigue los capítulos CIE-9. Diccionario VERSIONADO: cualquier
cambio debe pasar por una entrada de la bitácora y revisión clínica.
"""
from __future__ import annotations

import pandas as pd

VERSION_DICCIONARIO = "cie9-v1"

# (inicio, fin, grupo) sobre la parte entera del código; orden = prioridad
RANGOS = [
    (1, 139, "infecciosas"),
    (140, 239, "neoplasias"),
    (240, 279, "endocrino_otro"),      # 250 se resuelve antes
    (280, 289, "sangre"),
    (290, 319, "mental"),
    (320, 389, "neurologico"),
    (390, 459, "circulatorio"),        # 428 se resuelve antes
    (460, 519, "respiratorio"),
    (520, 579, "digestivo"),
    (580, 629, "genitourinario"),
    (630, 679, "embarazo"),
    (680, 709, "piel_celulitis"),
    (710, 739, "musculoesqueletico"),
    (740, 759, "congenito"),
    (760, 779, "perinatal"),
    (780, 799, "sintomas_mal_definidos"),
    (800, 999, "lesiones"),
]


def grupo_cie9(codigo: str | None) -> str:
    if codigo is None or pd.isna(codigo):
        return "desconocido"
    c = str(codigo).strip()
    if c in ("", "Desconocido", "?"):
        return "desconocido"
    if c[0] in "Vv":
        return "codigo_V"
    if c[0] in "Ee":
        return "codigo_E"
    try:
        v = float(c)
    except ValueError:
        return "otros"
    entero = int(v)
    if entero == 250:
        # 250.0x sin complicación; 250.1-250.9 con complicación (cetoacidosis,
        # coma, renal, oftálmica, neurológica, circulatoria, otras)
        decimal = round((v - 250) * 10, 3)
        return "diabetes_sin_complicacion" if decimal < 1 else "diabetes_con_complicacion"
    if entero == 428:
        return "insuficiencia_cardiaca"
    if entero in (785,):
        return "circulatorio"
    for ini, fin, grupo in RANGOS:
        if ini <= entero <= fin:
            return grupo
    return "otros"


def agrupar(serie: pd.Series) -> pd.Series:
    unicos = serie.astype("string").unique()
    mapa = {u: grupo_cie9(u) for u in unicos}
    return serie.astype("string").map(mapa).astype("string")
