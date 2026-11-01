#!/usr/bin/env python
"""tareas.py — ejecutor único del proyecto (Windows, macOS y Linux).

    python tareas.py estado                  # qué URL de GitHub / MinIO / MLflow se usan
    python tareas.py setup                   # git + remoto GitHub + dvc + remoto MinIO + bucket
    python tareas.py importar-e2 --tag crudo-v1
                                             # tras el PR del notebook E2 (Colab): baja el crudo de MinIO,
                                             #   verifica md5 contra el contrato, dvc add, etiqueta, push
    python tareas.py e2 --tag crudo-v1       # alternativa: ejecuta el notebook E2 desde el repo (sin Colab)
    python tareas.py descargar               # baja el crudo (Drive) a datos/crudo/
    python tareas.py repro                   # E3: dvc repro (5 tareas + partición)
    python tareas.py guardar -m "e3: ..."    # git add + commit (mensaje con el porqué)
    python tareas.py version-datos datos-v1 -m "crudo + E3 inicial"
                                             # etiqueta anotada + dvc push + git push + snapshot MinIO
    python tareas.py publicar                # dvc push y luego git push --follow-tags
    python tareas.py e4 [--n-trials 40]      # baselines + Optuna (MLflow)
    python tareas.py e5                      # evaluación + registro @campeon + reporte-final
    python tareas.py verificar               # criterio 1 de S03: repro forzado, dvc.lock idéntico
    python tareas.py minio-listar            # ver la organización del bucket

La URL de GitHub se toma de proyecto.yaml -> github.url (o de la variable de
entorno GITHUB_URL si se define). No hay que escribirla en ningún otro sitio.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

from p09 import config as C  # noqa: E402


def sh(*cmd: str, check: bool = True, quiet: bool = False) -> subprocess.CompletedProcess:
    if not quiet:
        print("$", " ".join(cmd))
    r = subprocess.run(list(cmd), cwd=RAIZ, text=True, capture_output=quiet)
    if check and r.returncode != 0:
        raise SystemExit(f"falló: {' '.join(cmd)}")
    return r


def salida(*cmd: str) -> str:
    return subprocess.run(list(cmd), cwd=RAIZ, text=True, capture_output=True).stdout.strip()


# --------------------------------------------------------------------- setup
def t_estado(_):
    print(f"GitHub (proyecto.yaml) : {C.GITHUB_URL}  rama={C.GITHUB_RAMA}")
    print(f"git remote origin      : {salida('git', 'remote', 'get-url', 'origin') or '(sin configurar)'}")
    print(f"MinIO API              : {C.MINIO_ENDPOINT}  bucket={C.MINIO_BUCKET}")
    print(f"MinIO consola          : {C.CFG['minio']['consola']}")
    print(f"DVC remotos            : {salida('dvc', 'remote', 'list') or '(sin configurar)'}")
    print(f"MLflow                 : {C.MLFLOW_URI}  experimento={C.EXPERIMENTO}")
    print(f".env presente          : {(RAIZ / '.env').exists()}")
    if "CAMBIAR-USUARIO" in C.GITHUB_URL:
        print("\n⚠  Edite proyecto.yaml -> github.url con la URL real del repositorio.")


def _raiz_git() -> Path | None:
    """Raíz del repositorio Git que contiene al proyecto (puede ser una carpeta superior)."""
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=RAIZ, text=True, capture_output=True)
    return Path(r.stdout.strip()).resolve() if r.returncode == 0 else None


def t_setup(_):
    # Nunca se crea un .git aquí si ya hay un repositorio arriba: eso dejaba un repo
    # anidado vacío y toda la procedencia salía como sin-git / sin-version.
    anidado = RAIZ / ".git"
    padre = next((p for p in RAIZ.parents if (p / ".git").exists()), None)
    if anidado.exists() and padre is not None:
        raise SystemExit(f"Hay un repositorio Git anidado en {anidado} dentro de {padre}. "
                         f"Bórrelo (rm -rf {anidado}) y vuelva a ejecutar setup.")
    raiz_git = _raiz_git()
    if raiz_git is None:
        sh("git", "init", "-b", C.GITHUB_RAMA)
        raiz_git = RAIZ
    en_subcarpeta = raiz_git != RAIZ
    # remoto GitHub: idempotente, siempre igual a proyecto.yaml
    if salida("git", "remote"):
        sh("git", "remote", "set-url", "origin", C.GITHUB_URL)
    else:
        sh("git", "remote", "add", "origin", C.GITHUB_URL)
    if not (RAIZ / ".dvc").exists():
        # --subdir: DVC vive en esta carpeta aunque Git esté en la carpeta superior
        sh("dvc", "init", "--subdir") if en_subcarpeta else sh("dvc", "init")
    m = C.CFG["minio"]
    url = f"s3://{m['bucket']}/{m['prefijo_dvc']}"
    nombre = m["nombre_remoto_dvc"]
    sh("dvc", "remote", "add", "-d", "-f", nombre, url)
    sh("dvc", "remote", "modify", nombre, "endpointurl", C.MINIO_ENDPOINT)
    sh("dvc", "remote", "modify", nombre, "region", "us-east-1")
    sh("dvc", "config", "core.autostage", "true")
    try:
        acceso, secreto = C.credenciales_minio()
        # --local => .dvc/config.local (ignorado por git): la credencial NO se versiona
        sh("dvc", "remote", "modify", "--local", nombre, "access_key_id", acceso, quiet=True)
        sh("dvc", "remote", "modify", "--local", nombre, "secret_access_key", secreto, quiet=True)
        print("credenciales MinIO -> .dvc/config.local (no versionado)")
        from p09.infra.minio import asegurar_bucket
        asegurar_bucket()
    except Exception as e:
        print(f"⚠  MinIO no configurado aún: {e}")
    ign = salida("git", "check-ignore", ".dvc/config.local")
    print("✓ .dvc/config.local ignorado por git" if ign else "⚠  .dvc/config.local NO está ignorado")
    t_estado(_)


def t_descargar(_):
    destino = RAIZ / "datos" / "crudo"
    destino.mkdir(parents=True, exist_ok=True)
    for clave, nombre in [("parquet", "diabetic_data.parquet"), ("ids_mapping", "IDS_mapping.csv")]:
        url = C.CFG["fuentes"][clave] + "&confirm=t"
        print(f"↓ {nombre}")
        with urllib.request.urlopen(url, timeout=120) as r, open(destino / nombre, "wb") as f:
            shutil.copyfileobj(r, f)
        cab = (destino / nombre).read_bytes()[:15]
        if b"<!DOCTYPE" in cab or b"<html" in cab:
            raise SystemExit(f"Drive devolvió HTML en {nombre}: revise permisos del enlace")
    print("crudo listo en datos/crudo/")


def t_repro(_):
    if not (RAIZ / "reportes/e2/descripcion.json").exists():
        raise SystemExit("Falta el contrato de E2 (reportes/e2/): ejecute el notebook E2 e importe con "
                         "python tareas.py importar-e2 --tag crudo-v1")
    sh("dvc", "repro")
    sh("dvc", "metrics", "show", check=False)


def t_guardar(a):
    sh("git", "add", "-A")
    sh("git", "commit", "-m", a.mensaje)


def t_publicar(_):
    # contenido primero, historial después: ningún commit apunta a datos ausentes
    sh("dvc", "push")
    sh("git", "push", "-u", "origin", C.GITHUB_RAMA, "--follow-tags")


def _commit_y_tag(tag: str, mensaje: str) -> None:
    if salida("git", "status", "--porcelain"):
        sh("git", "add", "-A")          # .gitignore impide que entren datos o secretos
        sh("git", "commit", "-m", mensaje)
    if tag in salida("git", "tag", "--list", tag).split():
        print(f"⚠  la etiqueta {tag} ya existe: no se mueve (cree {tag[:-1]}{int(tag[-1]) + 1} si es otra versión)"
              if tag[-1].isdigit() else f"⚠  la etiqueta {tag} ya existe")
    else:
        sh("git", "tag", "-a", tag, "-m", mensaje)


def _registrar_crudo(tag: str) -> None:
    """Verifica el crudo local contra el contrato de E2, lo registra en DVC, etiqueta y publica."""
    import json
    from p09.datos.comun import md5_archivo
    contrato = RAIZ / "reportes/e2/descripcion.json"
    if not contrato.exists():
        raise SystemExit("Falta reportes/e2/descripcion.json: integre el PR del notebook E2 (o ejecute tareas.py e2)")
    desc = json.loads(contrato.read_text(encoding="utf-8"))
    for rel, clave in [("datos/crudo/diabetic_data.parquet", "md5_crudo"), ("datos/crudo/IDS_mapping.csv", "md5_mapping")]:
        real = md5_archivo(rel)
        if real != desc[clave]:
            raise SystemExit(f"✗ {rel}: md5 {real[:10]} ≠ contrato E2 {desc[clave][:10]}. No se registra.")
    print(f"✓ crudo verificado contra el contrato E2 (md5 {desc['md5_crudo'][:10]})")
    sh("dvc", "add", "datos/crudo")
    run = json.loads((RAIZ / "reportes/e2/mlflow_run.json").read_text()) if (RAIZ / "reportes/e2/mlflow_run.json").exists() else {}
    _commit_y_tag(tag, f"datos: {tag} publicado por E2 · {desc['filas']} filas · md5 {desc['md5_crudo'][:10]} · "
                       f"MLflow run {run.get('run_id', 'sin-run')[:8]}")


def t_importar_e2(a):
    """Tras integrar el PR del notebook E2: baja el crudo de MinIO, verifica, registra y publica."""
    if salida("git", "remote") and not a.local:
        sh("git", "pull", "--ff-only", "origin", C.GITHUB_RAMA, check=False)
    from p09.infra.minio import descargar_capa
    descargar_capa(a.tag, "crudo", RAIZ / "datos" / "crudo")
    _registrar_crudo(a.tag)
    if not a.local:
        t_publicar(a)
    print(f"✓ {a.tag} en el repositorio. Siguiente: python tareas.py repro")


def t_e2(a):
    """Ejecuta el notebook E2 sin interfaz desde el repo (bloque 9: regenerar el EDA con un comando).
    El notebook publica en MLflow y MinIO; el contrato queda en reportes/e2 y aquí se versiona."""
    import os
    if not (RAIZ / "datos/crudo/diabetic_data.parquet").exists():
        t_descargar(a)
    acceso, secreto = C.credenciales_minio()
    env = {**os.environ, "P09_SALIDA": str(RAIZ / "reportes/e2"), "P09_TAG_CRUDO": a.tag,
           "P09_CRUDO_LOCAL": str(RAIZ / "datos/crudo/diabetic_data.parquet"),
           "P09_MAPPING_LOCAL": str(RAIZ / "datos/crudo/IDS_mapping.csv"),
           "P09_PUBLICAR_GITHUB": "0",                     # aquí el commit lo hace git
           "P09_PUBLICAR_MINIO": "0" if a.local else "1",
           "GITHUB_URL": C.GITHUB_URL, "MINIO_ENDPOINT": C.MINIO_ENDPOINT,
           "MINIO_ACCESS_KEY": acceso, "MINIO_SECRET_KEY": secreto,
           "MLFLOW_TRACKING_URI": C.MLFLOW_URI}
    nb = next((RAIZ / "notebooks").glob("E2_*.ipynb"))
    print(f"$ jupyter nbconvert --execute {nb.name}")
    r = subprocess.run(["jupyter", "nbconvert", "--to", "notebook", "--execute", str(nb),
                        "--ExecutePreprocessor.timeout=1800", "--output-dir", str(RAIZ / "reportes/e2"),
                        "--output", "E2_ejecutado.ipynb"], cwd=RAIZ, env=env, text=True)
    if r.returncode != 0:
        raise SystemExit("falló la ejecución del notebook E2")
    _registrar_crudo(a.tag)
    if not a.local:
        t_publicar(a)


def t_version_datos(a):
    _commit_y_tag(a.tag, f"{a.tag}: {a.mensaje}")
    t_publicar(a)
    from p09.infra.minio import CAPAS_E3, publicar_snapshot
    publicar_snapshot(a.tag, CAPAS_E3)


def t_snapshot(a):
    from p09.infra.minio import publicar_snapshot
    publicar_snapshot(a.tag, a.capas)


def t_minio_listar(_):
    from p09.infra.minio import listar
    listar()


# --------------------------------------------------------------------- E4/E5
def t_e4(a):
    from p09.modelado import baselines, optimizar
    baselines.main([])
    args = ["--n-trials", str(a.n_trials)] if a.n_trials else []
    for alg in a.algoritmo or []:
        args += ["--algoritmo", alg]
    optimizar.main(args)


def t_e5(a):
    from p09.evaluacion import evaluar
    evaluar.main(["--sin-registro"] if a.sin_registro else [])


def t_verificar(_):
    """Criterio 1 (S03): rehacer forzando y comprobar que la anotación no cambia."""
    sh("dvc", "pull", check=False)
    sh("dvc", "repro", "--force")
    r = sh("git", "diff", "--exit-code", "HEAD", "--", "dvc.lock", check=False)
    print("✓ reproducible: dvc.lock idéntico" if r.returncode == 0 else "✗ dvc.lock cambió: NO reproducible")
    raise SystemExit(r.returncode)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for nombre, fn in [("estado", t_estado), ("setup", t_setup), ("descargar", t_descargar),
                       ("repro", t_repro),
                       ("publicar", t_publicar), ("minio-listar", t_minio_listar),
                       ("verificar", t_verificar)]:
        sp.add_parser(nombre).set_defaults(fn=fn)
    g = sp.add_parser("guardar"); g.add_argument("-m", "--mensaje", required=True); g.set_defaults(fn=t_guardar)
    v = sp.add_parser("version-datos"); v.add_argument("tag"); v.add_argument("-m", "--mensaje", required=True)
    v.set_defaults(fn=t_version_datos)
    s = sp.add_parser("snapshot"); s.add_argument("tag"); s.add_argument("--capas", nargs="*")
    s.set_defaults(fn=t_snapshot)
    e2 = sp.add_parser("e2"); e2.add_argument("--tag", default="crudo-v1")
    e2.add_argument("--local", action="store_true", help="sin push a GitHub/MinIO")
    e2.set_defaults(fn=t_e2)
    ie = sp.add_parser("importar-e2"); ie.add_argument("--tag", default="crudo-v1")
    ie.add_argument("--local", action="store_true", help="sin git pull ni push")
    ie.set_defaults(fn=t_importar_e2)
    e4 = sp.add_parser("e4"); e4.add_argument("--n-trials", type=int); e4.add_argument("--algoritmo", action="append")
    e4.set_defaults(fn=t_e4)
    e5 = sp.add_parser("e5"); e5.add_argument("--sin-registro", action="store_true"); e5.set_defaults(fn=t_e5)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
