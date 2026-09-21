#!/usr/bin/env python3
"""Convierte señales ECG (WFDB o HDF5) en imágenes PNG listas para Teachable Machine.

Teachable Machine (Image Project) clasifica imágenes, así que cada registro ECG se renderiza
como un trazado y se guarda en la carpeta de su clase, dentro de --out.

Estrategia de etiquetado:
  Se lee un CSV de etiquetas (--labels) que asocia cada registro con una o varias patologías.
  La columna de identificador y las columnas de etiqueta se indican por parámetro. El mapa
  de patología -> carpeta está en LABEL_TO_CLASS (edítalo según tu dataset).

Ejemplos:
  # WFDB (PTB-XL): carpeta con .dat/.hea + ptbxl_database.csv
  python scripts/wfdb_to_images.py \
      --input data/raw/ptbxl --format wfdb \
      --labels data/raw/ptbxl/ptbxl_database.csv --id-col filename_hr --label-col scp_codes \
      --out data/images

  # HDF5 (CODE-15%): exams.hdf5 + exams.csv
  python scripts/wfdb_to_images.py \
      --input data/raw/code15 --format hdf5 \
      --labels data/raw/code15/exams.csv --id-col exam_id \
      --out data/images

Solo se generan IMÁGENES anonimizadas: no se copia ningún metadato personal.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend sin ventana, para servidores
import matplotlib.pyplot as plt
import numpy as np

from scp_class_map import map_labels  # fuente única del mapeo etiqueta -> clase

# Derivaciones estándar de 12 canales, en orden WFDB habitual.
LEADS = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]


def bandpass(sig: np.ndarray, fs: float, lo: float = 0.5, hi: float = 40.0) -> np.ndarray:
    """Filtro pasa-banda para limpiar deriva de línea base y ruido de alta frecuencia."""
    from scipy.signal import butter, filtfilt

    ny = 0.5 * fs
    b, a = butter(2, [lo / ny, hi / ny], btype="band")
    return filtfilt(b, a, sig, axis=0)


def plot_ecg(signal: np.ndarray, fs: float, out_path: Path, seconds: float = 5.0,
             n_leads: int = 6) -> None:
    """Renderiza las primeras `n_leads` derivaciones en una rejilla estilo papel ECG."""
    n = int(seconds * fs)
    signal = signal[:n]
    t = np.arange(signal.shape[0]) / fs
    n_leads = min(n_leads, signal.shape[1])

    fig, axes = plt.subplots(n_leads, 1, figsize=(6, 6), sharex=True)
    if n_leads == 1:
        axes = [axes]
    for i in range(n_leads):
        ax = axes[i]
        ax.plot(t, signal[:, i], color="black", linewidth=0.6)
        ax.set_ylabel(LEADS[i] if i < len(LEADS) else f"ch{i}", fontsize=7, rotation=0,
                      labelpad=12, va="center")
        # rejilla tipo papel milimetrado
        ax.grid(which="major", color="#f4b0b0", linewidth=0.5)
        ax.set_yticklabels([])
        ax.set_xticklabels([])
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.subplots_adjust(hspace=0.1, left=0.08, right=0.98, top=0.98, bottom=0.03)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=96)
    plt.close(fig)


def iter_wfdb(input_dir: Path):
    """Itera (record_id, signal, fs) sobre registros WFDB de una carpeta."""
    import wfdb

    for hea in sorted(input_dir.rglob("*.hea")):
        rec_id = hea.with_suffix("").name
        try:
            rec = wfdb.rdrecord(str(hea.with_suffix("")))
            yield rec_id, np.asarray(rec.p_signal), float(rec.fs)
        except Exception as e:  # pragma: no cover - registros corruptos
            print(f"[wfdb] omitido {rec_id}: {e}")


def iter_hdf5(input_dir: Path):
    """Itera (record_id, signal, fs) sobre un dataset HDF5 (CODE-15% / SaMi-Trop)."""
    import h5py

    for h5 in sorted(input_dir.rglob("*.hdf5")) + sorted(input_dir.rglob("*.h5")):
        with h5py.File(h5, "r") as f:
            ids = f["exam_id"][:] if "exam_id" in f else range(len(f["tracings"]))
            tracings = f["tracings"]
            fs = float(f.attrs.get("sample_rate", 400))
            for i, rec_id in enumerate(ids):
                yield str(int(rec_id) if hasattr(rec_id, "__int__") else rec_id), \
                    np.asarray(tracings[i]), fs


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", required=True, help="carpeta con los registros descargados")
    p.add_argument("--out", default="data/images", help="carpeta de salida (una subcarpeta por clase)")
    p.add_argument("--format", choices=["wfdb", "hdf5"], default="wfdb")
    p.add_argument("--labels", help="CSV con las etiquetas por registro")
    p.add_argument("--manifest", help="CSV (record_id,class) de plan_balanced_set.py: "
                                      "renderiza SOLO esos registros con esa clase")
    p.add_argument("--id-col", default="exam_id", help="columna de identificador en el CSV")
    p.add_argument("--label-col", default="scp_codes", help="columna de etiquetas en el CSV")
    p.add_argument("--limit", type=int, default=0, help="máximo de registros (0 = todos)")
    p.add_argument("--no-filter", action="store_true", help="no aplicar filtro pasa-banda")
    args = p.parse_args()

    input_dir = Path(args.input)
    out_dir = Path(args.out)

    # manifiesto balanceado (tiene prioridad sobre --labels): record_id -> {clases}
    manifest: dict[str, set[str]] = {}
    if args.manifest:
        import csv

        with open(args.manifest, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                rid, cls = row["record_id"], row["class"]
                for key in (rid, Path(rid).name):  # casa id completo o nombre base
                    manifest.setdefault(key, set()).add(cls)
        print(f"[manifest] {len(manifest)} identificadores cargados de {args.manifest}")

    labels = {}
    if args.labels and not manifest:
        import pandas as pd

        df = pd.read_csv(args.labels)
        labels = dict(zip(df[args.id_col].astype(str), df[args.label_col].astype(str)))
        print(f"[labels] {len(labels)} etiquetas cargadas de {args.labels}")

    iterator = iter_wfdb(input_dir) if args.format == "wfdb" else iter_hdf5(input_dir)

    n = 0
    for rec_id, signal, fs in iterator:
        if manifest:
            classes = sorted(manifest.get(str(rec_id)) or manifest.get(Path(str(rec_id)).name) or [])
            if not classes:
                continue  # registro fuera del set balanceado
        else:
            classes = map_labels(labels.get(str(rec_id), ""))
        if not args.no_filter:
            try:
                signal = bandpass(signal, fs)
            except Exception:
                pass
        for cls in classes:
            plot_ecg(signal, fs, out_dir / cls / f"{rec_id}.png")
        n += 1
        if n % 50 == 0:
            print(f"[render] {n} ECG procesados...")
        if args.limit and n >= args.limit:
            break

    print(f"Listo: {n} ECG convertidos en imágenes bajo {out_dir}/")
    print("Sube cada subcarpeta como una clase en https://teachablemachine.withgoogle.com/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
