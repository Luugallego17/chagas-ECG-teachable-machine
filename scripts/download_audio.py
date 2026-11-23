#!/usr/bin/env python3
"""Descarga CirCor DigiScope v1.0.3 a data/audio/raw y lo descomprime.

No redistribuye el audio: solo baja el ZIP que publica PhysioNet
(https://physionet.org/content/circor-heart-sound/1.0.3/, ODC-By 1.0).
La carpeta de destino está en .gitignore. No descarga el Challenge 2016.

Uso:
  python scripts/download_audio.py --dest data/audio/raw
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen

URL_ZIP = "https://physionet.org/content/circor-heart-sound/get-zip/1.0.3/"
NOMBRE_ZIP = "circor-heart-sound-1.0.3.zip"


def _ya_esta(dest: Path) -> Path | None:
    for csv in dest.rglob("training_data.csv"):
        wavs = list(csv.parent.glob("training_data/*.wav"))
        if wavs:
            return csv.parent
    return None


def descargar(dest: Path, url: str = URL_ZIP) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    listo = _ya_esta(dest)
    if listo is not None:
        print(f"[audio] ya está descomprimido en {listo}")
        return listo

    zip_path = dest / NOMBRE_ZIP
    if not zip_path.exists() or zip_path.stat().st_size < 1_000_000:
        print(f"[audio] descargando {url}")
        temporal = zip_path.with_suffix(".zip.parcial")
        with urlopen(url, timeout=120) as resp, open(temporal, "wb") as salida:
            bajados = 0
            while True:
                bloque = resp.read(1 << 20)
                if not bloque:
                    break
                salida.write(bloque)
                bajados += len(bloque)
                if bajados % (50 << 20) < (1 << 20):
                    print(f"[audio]   {bajados / 1e6:.0f} MB")
        temporal.replace(zip_path)
        print(f"[audio] ZIP en {zip_path} ({zip_path.stat().st_size / 1e6:.1f} MB)")
    else:
        print(f"[audio] se reutiliza el ZIP {zip_path}")

    print("[audio] descomprimiendo")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    listo = _ya_esta(dest)
    if listo is None:
        print("[audio] el ZIP no dejó training_data.csv", file=sys.stderr)
        sys.exit(1)
    print(f"[audio] listo en {listo}")
    return listo


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga CirCor 1.0.3 (no se versiona).")
    parser.add_argument("--dest", default="data/audio/raw", help="carpeta de crudos, fuera de git")
    args = parser.parse_args()
    descargar(Path(args.dest))


if __name__ == "__main__":
    main()
