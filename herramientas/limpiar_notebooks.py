"""Deja los notebooks listos para el repo plano y sin secretos.

- GITHUB_SUBCARPETA = ""        (el proyecto ya está en la raíz del repo)
- MINIO_ACCESS_KEY / MINIO_SECRET_KEY / GITHUB_TOKEN = ""   (Secretos de Colab o .env)
- Falla si después de limpiar queda algún token o clave en celdas o salidas.

Uso, desde la raíz del repo:   python herramientas/limpiar_notebooks.py
"""
import json
import re
import sys
from pathlib import Path

PATRONES = [
    (re.compile(r'^(\s*GITHUB_SUBCARPETA\s*=\s*)"[^"]*"', re.M), r'\1""'),
    (re.compile(r"^(\s*(?:MINIO_ACCESS_KEY|MINIO_SECRET_KEY|GITHUB_TOKEN)\s*=\s*)(['\"]).*?\2", re.M), r"\1''"),
]
PROHIBIDO = re.compile(  # patrones genéricos: sin secretos literales
    r"github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}|"
    r"(?:MINIO_ACCESS_KEY|MINIO_SECRET_KEY|GITHUB_TOKEN)\s*=\s*'[^']+'")

problemas = 0
for nb_path in sorted(Path("notebooks").glob("E*.ipynb")):
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    cambios = 0
    for celda in nb["cells"]:
        fuente = "".join(celda["source"])
        nueva = fuente
        if celda["cell_type"] == "code":
            for patron, reemplazo in PATRONES:
                nueva = patron.sub(reemplazo, nueva)
        if nueva != fuente:
            celda["source"] = nueva.splitlines(keepends=True)
            cambios += 1
    texto = json.dumps(nb, ensure_ascii=False, indent=1) + "\n"
    if PROHIBIDO.search(texto):
        print(f"✗ {nb_path.name}: sigue habiendo un secreto (¿en una SALIDA?). Revíselo a mano.")
        problemas += 1
    if cambios:
        nb_path.write_text(texto, encoding="utf-8")
    print(f"✓ {nb_path.name}: {cambios} celdas ajustadas")
sys.exit(1 if problemas else 0)
