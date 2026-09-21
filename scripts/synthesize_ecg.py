#!/usr/bin/env python3
"""Genera ECG SINTÉTICOS representativos de cada patología chagásica.

Objetivo: validar el pipeline y la taxonomía de clases SIN necesidad de descargar los
datasets reales (que son grandes y con registro). Usa SOLO la librería estándar de Python,
así que se ejecuta en cualquier sitio, sin instalar nada.

Cada clase se dibuja como un trazado (rhythm strip) en formato SVG, con la rejilla tipo
papel milimetrado. Sirve para:
  - ver de un vistazo qué morfología define cada clase,
  - comprobar visualmente la lógica de etiquetado,
  - tener un "smoke test" del render antes de procesar datos reales.

⚠️ NO uses estas señales sintéticas para ENTRENAR el modelo: son ilustrativas, no clínicas.
El entrenamiento debe hacerse con ECG reales (ver docs/datasets.md).

Uso:
  python scripts/synthesize_ecg.py --out samples          # un SVG por clase + uno combinado
"""
from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

FS = 250          # Hz
DURATION = 5.0    # s
MM_PER_S = 25     # velocidad de papel estándar
PX_PER_MM = 4     # resolución del dibujo

# Clases del proyecto (coinciden con data/images/<clase>)
CLASSES = ["normal", "rbbb", "lafb", "rbbb_lafb", "av_block", "pvc"]

DESCRIPTIONS = {
    "normal":    "ECG normal: PR ~160 ms, QRS estrecho (~90 ms), eje normal",
    "rbbb":      "BRD: QRS ancho (~130 ms) con patrón RSR' terminal",
    "lafb":      "HBAI: qR inicial, activacion tardia (eje izquierdo)",
    "rbbb_lafb": "BRD + HBAI: patron chagasico clasico (QRS ancho + RSR' + q inicial)",
    "av_block":  "BAV 1er grado: PR prolongado (~280 ms)",
    "pvc":       "Extrasistole ventricular: latido ancho prematuro + pausa compensatoria",
}


def gaussian(t: float, center: float, width: float, amp: float) -> float:
    """Onda gaussiana simple (para P y T)."""
    return amp * math.exp(-((t - center) ** 2) / (2 * width ** 2))


def beat_template(fs: int, kind: str = "normal") -> list[float]:
    """Devuelve las muestras (mV) de un latido, según la morfología pedida."""
    dur = 0.8  # s por plantilla de latido
    n = int(dur * fs)
    out = []
    for i in range(n):
        t = i / fs
        v = 0.0
        # Onda P (ausente/disociada se maneja fuera)
        v += gaussian(t, 0.15, 0.020, 0.12)
        if kind in ("normal", "lafb", "av_block"):
            # QRS estrecho normal
            v += gaussian(t, 0.34, 0.012, -0.10)   # Q
            v += gaussian(t, 0.37, 0.012, 1.00)    # R
            v += gaussian(t, 0.40, 0.012, -0.22)   # S
            if kind == "lafb":
                v += gaussian(t, 0.325, 0.008, -0.18)  # q inicial más marcada
        elif kind in ("rbbb", "rbbb_lafb"):
            # QRS ancho con RSR' (segunda R terminal): sello del BRD
            v += gaussian(t, 0.35, 0.012, 0.85)    # R
            v += gaussian(t, 0.385, 0.010, -0.30)  # S
            v += gaussian(t, 0.435, 0.016, 0.55)   # R' terminal ancho
            if kind == "rbbb_lafb":
                v += gaussian(t, 0.325, 0.008, -0.20)  # q inicial (componente HBAI)
        # Onda T
        v += gaussian(t, 0.58, 0.045, 0.28)
        out.append(v)
    return out


def pvc_beat(fs: int) -> list[float]:
    """Latido ventricular prematuro: QRS ancho, bizarro, sin P, T opuesta."""
    dur = 0.8
    n = int(dur * fs)
    out = []
    for i in range(n):
        t = i / fs
        v = gaussian(t, 0.33, 0.050, -1.10)   # QRS ancho y profundo
        v += gaussian(t, 0.46, 0.070, 0.55)   # onda T opuesta y ancha
        out.append(v)
    return out


def build_strip(kind: str) -> list[float]:
    """Compone una tira de 5 s a partir de latidos, según la clase."""
    random.seed(hash(kind) & 0xFFFF)
    n_total = int(DURATION * FS)
    sig = [0.0] * n_total
    rr = 0.85  # intervalo RR base (s) ~ 70 lpm

    if kind == "av_block":
        # PR prolongado: se simula alargando el latido base (P más adelantada del QRS)
        beat = beat_template(FS, "normal")
        # desplazar el QRS: reconstruimos con P antes y QRS más tarde
        beat = _prolong_pr(FS, extra=0.12)
        _lay_beats(sig, beat, rr)
    elif kind == "pvc":
        normal = beat_template(FS, "normal")
        pvc = pvc_beat(FS)
        # secuencia: N N N V(pausa) N
        pos = 0.15
        seq = ["N", "N", "N", "V", "N", "N"]
        for j, b in enumerate(seq):
            beat = pvc if b == "V" else normal
            _place(sig, beat, int(pos * FS))
            step = rr * (0.55 if b == "V" else 1.0)
            if b == "V":
                step = rr * 1.45  # pausa compensatoria tras la extrasístole
            pos += step
    else:
        beat = beat_template(FS, kind)
        _lay_beats(sig, beat, rr)
    return sig


def _prolong_pr(fs: int, extra: float) -> list[float]:
    """Latido normal pero con intervalo PR alargado (BAV de 1er grado)."""
    dur = 0.8 + extra
    n = int(dur * fs)
    out = []
    for i in range(n):
        t = i / fs
        v = gaussian(t, 0.15, 0.020, 0.12)           # P temprana
        qrs_c = 0.34 + extra                          # QRS retrasado -> PR largo
        v += gaussian(t, qrs_c - 0.03, 0.012, -0.10)
        v += gaussian(t, qrs_c, 0.012, 1.00)
        v += gaussian(t, qrs_c + 0.03, 0.012, -0.22)
        v += gaussian(t, qrs_c + 0.21, 0.045, 0.28)  # T
        out.append(v)
    return out


def _lay_beats(sig: list[float], beat: list[float], rr: float) -> None:
    pos = 0.15
    while int(pos * FS) + len(beat) < len(sig):
        _place(sig, beat, int(pos * FS))
        pos += rr


def _place(sig: list[float], beat: list[float], start: int) -> None:
    for k, v in enumerate(beat):
        idx = start + k
        if 0 <= idx < len(sig):
            sig[idx] += v


def to_svg(sig: list[float], title: str, subtitle: str) -> str:
    """Renderiza la señal como SVG con rejilla tipo papel ECG (rosa)."""
    w = int(DURATION * MM_PER_S * PX_PER_MM)      # ancho px
    h = 300
    mid = h * 0.6
    gain = 60  # px por mV

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="sans-serif">',
        f'<rect width="{w}" height="{h}" fill="white"/>',
    ]
    # rejilla menor (1 mm) y mayor (5 mm)
    step = PX_PER_MM
    for x in range(0, w, step):
        col = "#f3c0c0" if (x // step) % 5 == 0 else "#f8dede"
        parts.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke="{col}" stroke-width="0.5"/>')
    for y in range(0, h, step):
        col = "#f3c0c0" if (y // step) % 5 == 0 else "#f8dede"
        parts.append(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{col}" stroke-width="0.5"/>')

    # trazado
    pts = []
    for i, v in enumerate(sig):
        x = i / FS * MM_PER_S * PX_PER_MM
        y = mid - v * gain
        pts.append(f"{x:.1f},{y:.1f}")
    parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="black" stroke-width="1.2"/>')

    parts.append(f'<text x="8" y="22" font-size="16" font-weight="bold" fill="#222">{title}</text>')
    parts.append(f'<text x="8" y="42" font-size="12" fill="#555">{subtitle}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="samples", help="carpeta de salida (por defecto samples/)")
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    combined = ['<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="1860" '
                'viewBox="0 0 2000 1860" font-family="sans-serif">',
                '<rect width="2000" height="1860" fill="white"/>']
    y_off = 0
    for kind in CLASSES:
        sig = build_strip(kind)
        svg = to_svg(sig, kind.upper(), DESCRIPTIONS[kind])
        (out / f"{kind}.svg").write_text(svg, encoding="utf-8")
        print(f"[svg] {out / (kind + '.svg')}")
        inner = svg.split("\n", 1)[1].rsplit("</svg>", 1)[0]
        combined.append(f'<g transform="translate(0,{y_off})">{inner}</g>')
        y_off += 310
    combined.append("</svg>")
    (out / "todas_las_clases.svg").write_text("\n".join(combined), encoding="utf-8")
    print(f"[svg] {out / 'todas_las_clases.svg'} (panel combinado)")
    print(f"\nListo: {len(CLASSES)} clases sintetizadas en {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
