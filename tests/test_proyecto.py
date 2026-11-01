"""Pruebas rápidas: métricas, agrupación CIE-9 y ausencia de fuga en la partición."""
import numpy as np
import pytest

from p09.datos.cie9 import grupo_cie9
from p09.modelado.metricas import evaluar, precision_at_k, recall_at_k


def test_recall_at_k_perfecto_y_azar():
    y = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    s = np.array([.9, .8, .1, .1, .1, .1, .1, .1, .1, .1])
    assert recall_at_k(y, s, 0.2) == 1.0
    assert precision_at_k(y, s, 0.2) == 1.0
    assert recall_at_k(y, -s, 0.2) == 0.0


def test_evaluar_nombres_estables():
    r = np.random.default_rng(0)
    y = r.integers(0, 2, 500); s = r.random(500)
    m = evaluar(y, s, 0.1)
    for k in ["recall_at_k", "precision_at_k", "aucpr", "roc_auc", "brier", "cal_pendiente"]:
        assert k in m


@pytest.mark.parametrize("cod,grupo", [
    ("428", "insuficiencia_cardiaca"), ("428.1", "insuficiencia_cardiaca"),
    ("250.01", "diabetes_sin_complicacion"), ("250.83", "diabetes_con_complicacion"),
    ("682", "piel_celulitis"), ("038", "infecciosas"), ("345", "neurologico"),
    ("V27", "codigo_V"), ("E888", "codigo_E"), ("Desconocido", "desconocido"), (None, "desconocido"),
])
def test_cie9(cod, grupo):
    assert grupo_cie9(cod) == grupo


def test_particion_sin_pacientes_compartidos():
    from p09.config import ruta
    import pandas as pd
    tr, te = ruta("datos/particion/train.parquet"), ruta("datos/particion/test.parquet")
    if not tr.exists():
        pytest.skip("ejecute dvc repro primero")
    a, b = pd.read_parquet(tr), pd.read_parquet(te)
    assert not set(a.patient_nbr) & set(b.patient_nbr)
