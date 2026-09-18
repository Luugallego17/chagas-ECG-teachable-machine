#!/usr/bin/env python3
"""Descarga los datasets de ECG usados para identificar patologías chagásicas.

Fuentes soportadas (ver docs/datasets.md para detalles y licencias):

  samitrop   Cohorte de Chagas (Zenodo 4905618)      -> requiere registro en algunas versiones
  code15     CODE-15%, 345.779 ECG (Zenodo 4916206)  -> abierto
  ptbxl      PTB-XL, 21.837 ECG (PhysioNet)           -> requiere cuenta PhysioNet
  challenge2025  PhysioNet Challenge 2025 (Chagas)     -> requiere cuenta PhysioNet

Uso:
  python scripts/download_data.py --dataset code15 --dest data/raw
  python scripts/download_data.py --dataset ptbxl  --dest data/raw   # pedirá login PhysioNet

Nota: los datasets son grandes (varios GB). Descarga solo lo que necesites y respeta los
términos de uso de cada fuente. Este script NO redistribuye datos: solo automatiza la
descarga desde la fuente oficial.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# URLs oficiales. Verifica en docs/datasets.md antes de usar.
DATASETS = {
    "samitrop": {
        "kind": "zenodo",
        "record": "4905618",
        "desc": "SaMi-Trop — cohorte de enfermedad de Chagas",
    },
    "code15": {
        "kind": "zenodo",
        "record": "4916206",
        "desc": "CODE-15% — 345.779 ECG con etiquetas de conducción",
    },
    "ptbxl": {
        "kind": "physionet",
        "path": "ptb-xl",
        "desc": "PTB-XL — 21.837 ECG clínicos con diagnósticos SCP",
    },
    "challenge2025": {
        "kind": "physionet",
        "path": "challenge-2025",
        "desc": "PhysioNet Challenge 2025 — detección de Chagas por ECG",
    },
}


def download_zenodo(record: str, dest: Path) -> None:
    """Descarga todos los ficheros de un registro Zenodo vía su API pública."""
    import requests
    from tqdm import tqdm

    api = f"https://zenodo.org/api/records/{record}"
    print(f"[zenodo] consultando {api}")
    meta = requests.get(api, timeout=60)
    meta.raise_for_status()
    files = meta.json().get("files", [])
    if not files:
        print("[zenodo] el registro no lista ficheros descargables.", file=sys.stderr)
        return
    dest.mkdir(parents=True, exist_ok=True)
    for f in files:
        url = f["links"]["self"]
        name = f["key"]
        out = dest / name
        if out.exists():
            print(f"[zenodo] ya existe, se omite: {name}")
            continue
        print(f"[zenodo] descargando {name} ({f.get('size', 0) / 1e6:.1f} MB)")
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            with open(out, "wb") as fh, tqdm(
                total=total, unit="B", unit_scale=True, desc=name
            ) as bar:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
                    bar.update(len(chunk))
    print(f"[zenodo] completado en {dest}")


def download_physionet(path: str, dest: Path) -> None:
    """PhysioNet requiere autenticación; se delega en la herramienta oficial `wget`.

    Se imprime el comando recomendado en lugar de incrustar credenciales.
    """
    out = dest / path
    cmd = (
        f"wget -r -N -c -np --user <TU_USUARIO_PHYSIONET> --ask-password "
        f"https://physionet.org/files/{path}/ -P {dest}"
    )
    print("PhysioNet requiere cuenta y aceptar los términos de uso del dataset.")
    print("1) Regístrate en https://physionet.org/ y acepta el DUA del dataset.")
    print(f"2) Descarga con:\n\n    {cmd}\n")
    print(f"   Los ficheros quedarán en: {out}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", choices=sorted(DATASETS), help="dataset a descargar")
    p.add_argument("--dest", default="data/raw", help="carpeta destino (por defecto data/raw)")
    p.add_argument("--list", action="store_true", help="lista los datasets disponibles y termina")
    args = p.parse_args()

    if args.list:
        for k, v in DATASETS.items():
            print(f"  {k:14s} {v['desc']}")
        return 0

    if not args.dataset:
        p.error("indica --dataset (o usa --list para ver las opciones)")

    ds = DATASETS[args.dataset]
    dest = Path(args.dest) / args.dataset
    print(f"== {args.dataset}: {ds['desc']} ==")
    if ds["kind"] == "zenodo":
        download_zenodo(ds["record"], dest)
    elif ds["kind"] == "physionet":
        download_physionet(ds["path"], dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
