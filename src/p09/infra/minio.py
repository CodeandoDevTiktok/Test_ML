"""Versionado ORGANIZADO del dataset en MinIO.

DVC guarda el contenido por huella (dvc-store/files/md5/ab/cdef...), ilegible
para una persona. Este módulo publica además, por cada etiqueta git
``datos-vN``, una copia legible y un manifiesto:

    s3://<bucket>/
    ├── dvc-store/                         <- remoto DVC (fuente de verdad)
    └── datasets/
        ├── CATALOGO.json                  <- índice de todas las versiones
        ├── crudo/crudo-v1/diabetic_data.parquet      <- publicado por el notebook E2
        ├── crudo/crudo-v1/IDS_mapping.csv
        ├── eda/crudo-v1/*.json|csv|png               <- informe de E2 + mlflow_run.json
        ├── final/datos-v1/tabla_modelado.parquet     <- publicado por E3
        ├── particion/datos-v1/train.parquet
        ├── particion/datos-v1/test.parquet
        ├── reportes/datos-v1/*.json       <- informes de E3 de esa versión
        └── manifiestos/datos-v1.json      <- md5, filas, commit, github_url
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from p09.config import CFG, MINIO_BUCKET, MINIO_ENDPOINT, credenciales_minio, ruta
from p09.procedencia import procedencia

CAPAS = {
    "crudo": ["datos/crudo/diabetic_data.parquet", "datos/crudo/IDS_mapping.csv"],
    "eda": ["reportes/e2/descripcion.json", "reportes/e2/calidad.json", "reportes/e2/hallazgos.json",
            "reportes/e2/plan_calidad.json", "reportes/e2/esquema_e2.csv",
            "reportes/e2/representatividad.csv", "reportes/e2/mlflow_run.json"],
    "intermedio": ["datos/intermedio/seleccionado.parquet", "datos/intermedio/limpio.parquet",
                   "datos/intermedio/construido.parquet", "datos/intermedio/integrado.parquet"],
    "final": ["datos/final/tabla_modelado.parquet", "docs/diccionario/diccionario_datos.csv"],
    "particion": ["datos/particion/train.parquet", "datos/particion/test.parquet"],
    "reportes": ["reportes/e3/seleccion.json", "reportes/e3/limpieza.json",
                 "reportes/e3/construccion.json", "reportes/e3/integracion.json",
                 "reportes/e3/esquema.json", "reportes/e3/particion.json"],
}


def cliente():
    import boto3
    from botocore.config import Config

    acceso, secreto = credenciales_minio()
    return boto3.client("s3", endpoint_url=MINIO_ENDPOINT, aws_access_key_id=acceso,
                        aws_secret_access_key=secreto, region_name="us-east-1",
                        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                                       connect_timeout=10, read_timeout=120,
                                       retries={"max_attempts": 3, "mode": "standard"}))


def asegurar_bucket(s3=None) -> None:
    s3 = s3 or cliente()
    existentes = {b["Name"] for b in s3.list_buckets().get("Buckets", [])}
    if MINIO_BUCKET in existentes:
        print(f"bucket '{MINIO_BUCKET}' ya existe en {MINIO_ENDPOINT}")
    else:
        s3.create_bucket(Bucket=MINIO_BUCKET)
        print(f"bucket '{MINIO_BUCKET}' creado en {MINIO_ENDPOINT}")


def _md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _filas(p: Path) -> int | None:
    if p.suffix == ".parquet":
        import pyarrow.parquet as pq
        return pq.ParquetFile(p).metadata.num_rows
    return None


CAPAS_E2 = ["crudo", "eda"]
CAPAS_E3 = ["intermedio", "final", "particion", "reportes"]


def publicar_snapshot(tag: str, capas: list[str] | None = None) -> dict:
    """Sube la versión actual del espacio de trabajo bajo datasets/<capa>/<tag>/."""
    capas = capas or list(CAPAS)
    s3 = cliente()
    asegurar_bucket(s3)
    pref = CFG["minio"]["prefijo_datasets"]
    manifiesto = {"tag": tag, "capas": capas, "publicado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "procedencia": procedencia(), "archivos": []}
    extra = {"eda": sorted(str(x.relative_to(ruta("."))) for x in ruta("reportes/e2/figuras").glob("*.png"))}
    for capa in capas:
        for rel in CAPAS[capa] + extra.get(capa, []):
            local = ruta(rel)
            if not local.exists():
                print(f"  (omitido, no existe) {rel}")
                continue
            clave = f"{pref}/{capa}/{tag}/{local.name}"
            md5 = _md5(local)
            s3.upload_file(str(local), MINIO_BUCKET, clave,
                           ExtraArgs={"Metadata": {"md5": md5, "tag": tag, "origen": rel}})
            manifiesto["archivos"].append({"capa": capa, "ruta_repo": rel, "clave_s3": clave,
                                           "md5": md5,
                                           # objeto en dvc-store/ (solo lo que gestiona DVC: datos/...)
                                           "clave_dvc_store": (f"{CFG['minio']['prefijo_dvc']}/files/md5/{md5[:2]}/{md5[2:]}"
                                                               if rel.startswith("datos/") else None),
                                           "bytes": local.stat().st_size,
                                           "filas": _filas(local)})
            print(f"  ↑ s3://{MINIO_BUCKET}/{clave}")
    s3.put_object(Bucket=MINIO_BUCKET, Key=f"{pref}/manifiestos/{tag}.json",
                  Body=json.dumps(manifiesto, indent=2, ensure_ascii=False).encode("utf-8"),
                  ContentType="application/json")
    _actualizar_catalogo(s3, pref, manifiesto)
    return manifiesto


def _actualizar_catalogo(s3, pref: str, manifiesto: dict) -> None:
    clave = f"{pref}/CATALOGO.json"
    try:
        cat = json.loads(s3.get_object(Bucket=MINIO_BUCKET, Key=clave)["Body"].read())
    except Exception:
        cat = {"proyecto": CFG["proyecto"]["codigo"], "github_url": CFG["github"]["url"], "versiones": []}
    cat["versiones"] = [v for v in cat["versiones"] if v["tag"] != manifiesto["tag"]]
    final = next((a for a in manifiesto["archivos"] if a["ruta_repo"].endswith("tabla_modelado.parquet")),
                 next((a for a in manifiesto["archivos"] if a["ruta_repo"].endswith("diabetic_data.parquet")), {}))
    cat["versiones"].append({
        "tag": manifiesto["tag"], "capas": manifiesto["capas"], "publicado_utc": manifiesto["publicado_utc"],
        "git_commit": manifiesto["procedencia"]["git_commit"],
        "md5_tabla_principal": final.get("md5"), "filas_tabla_principal": final.get("filas"),
        "run_eda": manifiesto["procedencia"].get("run_eda"),
        "manifiesto": f"{pref}/manifiestos/{manifiesto['tag']}.json",
    })
    cat["versiones"].sort(key=lambda v: v["tag"])
    s3.put_object(Bucket=MINIO_BUCKET, Key=clave, ContentType="application/json",
                  Body=json.dumps(cat, indent=2, ensure_ascii=False).encode("utf-8"))
    print(f"  catálogo: {len(cat['versiones'])} versiones en s3://{MINIO_BUCKET}/{clave}")


def descargar_capa(tag: str, capa: str, destino: Path) -> list[Path]:
    """Baja datasets/<capa>/<tag>/* (publicado por el notebook E2) a una carpeta local."""
    s3 = cliente()
    prefijo = f"{CFG['minio']['prefijo_datasets']}/{capa}/{tag}/"
    destino.mkdir(parents=True, exist_ok=True)
    bajados = []
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=MINIO_BUCKET, Prefix=prefijo):
        for o in pagina.get("Contents", []):
            local = destino / o["Key"][len(prefijo):]
            local.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(MINIO_BUCKET, o["Key"], str(local))
            bajados.append(local)
            print(f"  ↓ s3://{MINIO_BUCKET}/{o['Key']}")
    if not bajados:
        raise SystemExit(f"No hay nada en s3://{MINIO_BUCKET}/{prefijo}: ¿se ejecutó el notebook E2 con {tag}?")
    return bajados


def listar() -> None:
    s3 = cliente()
    pag = s3.get_paginator("list_objects_v2")
    for pagina in pag.paginate(Bucket=MINIO_BUCKET, Prefix=CFG["minio"]["prefijo_datasets"]):
        for o in pagina.get("Contents", []):
            print(f"{o['Size']:>12,}  {o['Key']}")
