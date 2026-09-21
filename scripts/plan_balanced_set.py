#!/usr/bin/env python3
"""Explora las etiquetas de un dataset y genera un MANIFIESTO balanceado por clase.

Un modelo de Teachable Machine sesga hacia las clases mayoritarias. En PTB-XL/CODE-15% la
clase `normal` domina y `lafb`/`pvc` son raras. Este script:

  1. Lee el CSV de etiquetas del dataset.
  2. Asigna cada registro a sus clases de proyecto (usa scripts/scp_class_map.py).
  3. Imprime la distribución de clases (cuántos ECG hay de cada una).
  4. Escribe un manifiesto (record_id, class) BALANCEADO, submuestreando las clases grandes,
     que luego consume `wfdb_to_images.py` para renderizar solo esos registros.

Usa SOLO la librería estándar: se ejecuta sin instalar nada.

Ejemplos:
  # PTB-XL: una columna de etiquetas (scp_codes, dict serializado)
  python scripts/plan_balanced_set.py \
      --labels data/raw/ptbxl/ptbxl_database.csv \
      --id-col filename_hr --label-col scp_codes \
      --out data/manifest.csv --per-class 300

  # CODE-15%: varias columnas booleanas de anomalía
  python scripts/plan_balanced_set.py \
      --labels data/raw/code15/exams.csv \
      --id-col exam_id --bool-cols RBBB 1dAVb \
      --out data/manifest.csv --per-class 500
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scp_class_map import map_labels  # noqa: E402


def truthy(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "t", "y", "1.0"}


def read_rows(path: Path, id_col: str, label_col: str | None, bool_cols: list[str]):
    """Itera (record_id, clases) por fila del CSV."""
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in ([id_col] + ([label_col] if label_col else []) + bool_cols)
                   if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"columnas no encontradas en el CSV: {missing}\n"
                             f"disponibles: {reader.fieldnames}")
        for row in reader:
            rec_id = row[id_col]
            if bool_cols:
                # construye una etiqueta sintética con los nombres de columnas activas
                active = " ".join(c for c in bool_cols if truthy(row.get(c, "")))
                classes = map_labels(active)
            else:
                classes = map_labels(row.get(label_col, ""))
            yield rec_id, classes


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--labels", required=True, help="CSV de etiquetas del dataset")
    p.add_argument("--id-col", default="exam_id", help="columna del identificador de registro")
    p.add_argument("--label-col", help="columna de etiquetas (p. ej. scp_codes en PTB-XL)")
    p.add_argument("--bool-cols", nargs="*", default=[],
                   help="columnas booleanas de anomalía (p. ej. RBBB 1dAVb en CODE-15%)")
    p.add_argument("--out", default="data/manifest.csv", help="manifiesto de salida")
    p.add_argument("--per-class", type=int, default=0,
                   help="objetivo de ejemplos por clase (0 = usar la clase minoritaria)")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    if not args.label_col and not args.bool_cols:
        p.error("indica --label-col o --bool-cols")

    random.seed(args.seed)
    by_class: dict[str, list[str]] = defaultdict(list)
    total = 0
    for rec_id, classes in read_rows(Path(args.labels), args.id_col, args.label_col, args.bool_cols):
        total += 1
        for cls in classes:
            by_class[cls].append(rec_id)

    if not by_class:
        raise SystemExit("no se asignó ninguna clase; revisa --label-col/--bool-cols")

    # --- Distribución ---
    print(f"\nRegistros leídos: {total}")
    print("Distribución de clases (un ECG puede contar en varias):")
    width = max(len(c) for c in by_class)
    counts = {c: len(ids) for c, ids in by_class.items()}
    biggest = max(counts.values())
    for cls in sorted(counts, key=counts.get, reverse=True):
        n = counts[cls]
        bar = "#" * int(40 * n / biggest)
        print(f"  {cls:<{width}}  {n:6d}  {bar}")

    # --- Plan balanceado ---
    target = args.per_class or min(counts.values())
    print(f"\nObjetivo por clase: {target} "
          f"({'fijado' if args.per_class else 'clase minoritaria'})")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    seen: set[tuple[str, str]] = set()
    written = 0
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["record_id", "class"])
        for cls, ids in by_class.items():
            pick = ids if len(ids) <= target else random.sample(ids, target)
            for rec_id in pick:
                key = (rec_id, cls)
                if key in seen:
                    continue
                seen.add(key)
                w.writerow([rec_id, cls])
                written += 1

    print(f"\nManifiesto escrito: {out}  ({written} filas)")
    print("Renderiza solo esos registros pasando el manifiesto a wfdb_to_images.py "
          "(o filtra por él en tu notebook).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
