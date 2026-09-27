#!/usr/bin/env python3
"""Des-identifica fotos de ECG antes de usarlas: quita metadatos y tapa/recorta identificadores.

Las fotos de ECG en papel suelen contener datos personales de pacientes: nombre, número de
historia clínica, fecha, nombre del hospital, y ADEMÁS metadatos EXIF del teléfono (fecha y a
veces ubicación GPS). Este script deja las imágenes seguras para uso académico:

  1. Elimina TODOS los metadatos (EXIF/GPS/ICC) reconstruyendo el píxel puro.
  2. Tapa con cajas negras sólidas las regiones que indiques (nombre, ID, fecha, sellos).
     Se usa relleno opaco, no desenfoque, porque el desenfoque a veces se puede revertir.
  3. Opcionalmente rota y/o recorta para dejar solo el trazado.

Requiere Pillow (en tu máquina):  pip install pillow

FLUJO RECOMENDADO
  # 1) Genera una vista con rejilla de coordenadas para saber qué tapar:
  python scripts/deidentify_images.py --in fotos/ --out previews/ --grid

  # 2) Mira las previews, anota las cajas (x,y,ancho,alto) que cubren los datos y aplícalas:
  python scripts/deidentify_images.py --in fotos/foto1.jpg --out anon/foto1.jpg \
      --redact 0,0,702,190 --redact 480,0,222,520

  # 3) (opcional) recorta a la tira del ECG y/o rota:
  python scripts/deidentify_images.py --in fotos/foto1.jpg --out anon/foto1.jpg \
      --rotate 90 --crop 60,300,600,1000

  # Lote con las mismas cajas para todas, solo quitando metadatos:
  python scripts/deidentify_images.py --in fotos/ --out anon/

IMPORTANTE: revisa SIEMPRE a ojo cada imagen de salida antes de usarla. Ninguna
automatización sustituye una verificación humana de que no queda ningún dato identificable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    raise SystemExit("Falta Pillow. Instálalo con:  pip install pillow")

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_box(s: str) -> tuple[int, int, int, int]:
    parts = [int(v) for v in s.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("una caja debe ser x,y,ancho,alto (4 enteros)")
    return tuple(parts)  # type: ignore[return-value]


def strip_metadata(img: "Image.Image") -> "Image.Image":
    """Devuelve una copia SIN metadatos: reconstruye el bitmap desde cero."""
    img = img.convert("RGB")
    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))
    return clean


def draw_grid(img: "Image.Image", step: int = 100) -> "Image.Image":
    """Superpone una rejilla con coordenadas para poder leer posiciones en píxeles."""
    img = img.convert("RGB").copy()
    d = ImageDraw.Draw(img)
    w, h = img.size
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=(255, 0, 0), width=1)
        d.text((x + 2, 2), str(x), fill=(255, 0, 0))
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=(255, 0, 0), width=1)
        d.text((2, y + 2), str(y), fill=(255, 0, 0))
    return img


def process(img: "Image.Image", redactions, crop, rotate) -> "Image.Image":
    out = strip_metadata(img)
    if rotate:
        out = out.rotate(-rotate, expand=True)  # horario, como en el visor
    if redactions:
        d = ImageDraw.Draw(out)
        for (x, y, w, h) in redactions:
            d.rectangle([x, y, x + w, y + h], fill=(0, 0, 0))
    if crop:
        x, y, w, h = crop
        out = out.crop((x, y, x + w, y + h))
    return out


def iter_inputs(inp: Path):
    if inp.is_dir():
        for p in sorted(inp.iterdir()):
            if p.suffix.lower() in EXTS:
                yield p
    elif inp.suffix.lower() in EXTS:
        yield inp


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--in", dest="inp", required=True, help="imagen o carpeta de entrada")
    p.add_argument("--out", required=True, help="imagen o carpeta de salida")
    p.add_argument("--redact", type=parse_box, action="append", default=[],
                   help="caja a tapar x,y,ancho,alto (repetible)")
    p.add_argument("--crop", type=parse_box, help="recorte final x,y,ancho,alto")
    p.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=0,
                   help="rotación horaria en grados")
    p.add_argument("--grid", action="store_true",
                   help="en vez de des-identificar, escribe previews con rejilla de coordenadas")
    p.add_argument("--boxes-json", help="JSON {archivo: [[x,y,w,h],...]} de cajas por imagen (lote)")
    p.add_argument("--quality", type=int, default=95, help="calidad JPEG de salida")
    args = p.parse_args()

    inp = Path(args.inp)
    out = Path(args.out)
    per_file = json.loads(Path(args.boxes_json).read_text()) if args.boxes_json else {}

    inputs = list(iter_inputs(inp))
    if not inputs:
        raise SystemExit(f"no se encontraron imágenes en {inp}")
    batch = inp.is_dir()
    if batch:
        out.mkdir(parents=True, exist_ok=True)

    for src in inputs:
        img = Image.open(src)
        dst = (out / src.name) if batch else out
        dst.parent.mkdir(parents=True, exist_ok=True)
        if args.grid:
            draw_grid(img).save(dst.with_suffix(".png"))
            print(f"[grid] {dst.with_suffix('.png')}")
            continue
        boxes = args.redact + [tuple(b) for b in per_file.get(src.name, [])]
        result = process(img, boxes, args.crop, args.rotate)
        if dst.suffix.lower() in (".jpg", ".jpeg"):
            result.save(dst, "JPEG", quality=args.quality)  # sin exif: no se pasa
        else:
            result.save(dst)
        print(f"[anon] {src.name} -> {dst}  (metadatos eliminados, {len(boxes)} cajas)")

    print("\nListo. REVISA a ojo cada imagen de salida antes de usarla.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
