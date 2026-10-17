#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera un dataset de imágenes de ECG SINTÉTICAS para entrenar en Teachable Machine.

Crea una carpeta por clase con trazados generados (con variación de frecuencia, amplitud,
ruido y deriva de línea base) para que el modelo aprenda a distinguir cada patrón.

Modos:
  --modo multiclase  -> 6 clases: normal, BRD, HBAI, BRD+HBAI, Bloqueo AV, Extrasístole (por defecto)
  --modo binario     -> 2 clases: chagas / no_chagas

Usa SOLO la librería estándar (no instala nada).

  python scripts/generar_dataset_demo.py --modo multiclase --n 300 --out dataset_demo

⚠️ Las imágenes son sintéticas, para DEMOSTRACIÓN educativa. El modelo resultante distingue
trazados de este tipo; NO es un modelo clínico ni diagnostica Chagas en pacientes reales.
"""
from __future__ import annotations
import argparse, math, os, random, shutil, struct, zlib

W, H = 520, 300

def gauss(t, c, w, a): return a * math.exp(-((t - c) ** 2) / (2 * w * w))

def beat(t, kind):
    v = gauss(t, .15, .02, .12)
    if kind in ("rbbb", "rbbb_lafb"):
        v += gauss(t, .35, .012, .85) + gauss(t, .385, .01, -.3) + gauss(t, .435, .016, .55)
        if kind == "rbbb_lafb": v += gauss(t, .325, .008, -.2)
    else:
        q = .46 if kind == "av_block" else .34
        v += gauss(t, q - .03, .012, -.1) + gauss(t, q, .012, 1) + gauss(t, q + .03, .012, -.22)
        if kind == "lafb": v += gauss(t, .322, .008, -.18)
        if kind == "av_block": v += gauss(t, .15, .02, .12)
    v += gauss(t, (.7 if kind == "av_block" else .58), .045, .28)
    return v

def write_png(path, rows):
    raw = bytearray()
    for r in rows: raw += b"\x00" + r
    comp = zlib.compress(bytes(raw), 6)
    def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n"
        + ch(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) + ch(b"IDAT", comp) + ch(b"IEND", b""))

def render(path, kind, seed):
    rnd = random.Random(seed)
    rows = [bytearray(b"\xff\xff\xff" * W) for _ in range(H)]
    def px(x, y, c):
        xi, yi = int(x), int(y)
        if 0 <= xi < W and 0 <= yi < H:
            o = xi * 3; rows[yi][o:o + 3] = bytes(c)
    tint = rnd.choice([(246, 214, 218), (248, 220, 210), (244, 210, 214)])
    for x in range(0, W, 13):
        for y in range(H): px(x, y, tint)
    for y in range(0, H, 13):
        for x in range(W): px(x, y, tint)
    rr = rnd.uniform(.70, 1.02); gain = H * .30 * rnd.uniform(.85, 1.20)
    mid = H * .55 + rnd.uniform(-18, 18); sx = (W - 40) / 4.8 * rnd.uniform(.9, 1.1)
    bw_a = rnd.uniform(0, 10); bw_f = rnd.uniform(.5, 1.5); noise = rnd.uniform(.6, 2.2)
    x0 = 20 + rnd.uniform(-6, 6); prev = [None]
    def plot(x, y):
        y += bw_a * math.sin(2 * math.pi * bw_f * (x / W)) + rnd.uniform(-noise, noise)
        if prev[0] is not None:
            x1, y1 = prev[0]; steps = max(1, int(abs(y - y1)) + 1)
            for s in range(steps + 1):
                xx = x1 + (x - x1) * s / steps; yy = y1 + (y - y1) * s / steps
                px(xx, yy, (20, 20, 20)); px(xx, yy - 1, (20, 20, 20))
        prev[0] = (x, y)
    fs = 250
    if kind == "pvc":
        pos = .12
        for b in ["N", "N", "V", "N", "N"]:
            isV = b == "V"
            for i in range(int(.8 * fs)):
                tt = i / fs
                vv = (gauss(tt, .33, .05, -1.1) + gauss(tt, .46, .07, .55)) if isV else beat(tt, "normal")
                plot(x0 + (pos + tt) * sx, mid - vv * gain)
            pos += rr * 1.4 if isV else rr
    else:
        p = .12
        while p < 4.7:
            for j in range(int(.8 * fs)):
                tj = j / fs; plot(x0 + (p + tj) * sx, mid - beat(tj, kind) * gain)
            p += rr
    write_png(path, rows)

MULTICLASE = {
    "normal": "normal", "brd": "rbbb", "hbai": "lafb",
    "brd_hbai": "rbbb_lafb", "bloqueo_av": "av_block", "extrasistole_ventricular": "pvc",
}
# para el modo binario, 'chagas' rota entre estos patrones
CHAGAS_KINDS = ["rbbb", "lafb", "rbbb_lafb", "av_block", "pvc"]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--modo", choices=["multiclase", "binario"], default="multiclase")
    p.add_argument("--n", type=int, default=300, help="imágenes por clase (entrenamiento)")
    p.add_argument("--test", type=int, default=10, help="imágenes por clase para pruebas/")
    p.add_argument("--out", default="dataset_demo", help="carpeta de salida")
    args = p.parse_args()

    if os.path.isdir(args.out): shutil.rmtree(args.out)
    if args.modo == "multiclase":
        folders = {k: [v] for k, v in MULTICLASE.items()}
    else:
        folders = {"no_chagas": ["normal"], "chagas": CHAGAS_KINDS}
    for f in folders: os.makedirs(os.path.join(args.out, f))
    os.makedirs(os.path.join(args.out, "pruebas"))

    sid = 1000
    for folder, kinds in folders.items():
        for i in range(args.n):
            render(os.path.join(args.out, folder, f"{folder}_{i:03d}.png"), kinds[i % len(kinds)], sid); sid += 1
        for i in range(args.test):
            render(os.path.join(args.out, "pruebas", f"prueba_{folder}_{i:02d}.png"), kinds[i % len(kinds)], sid); sid += 1

    total = args.n * len(folders)
    print(f"Listo ({args.modo}): {len(folders)} clases · {total} imágenes en {args.out}/")
    print("Sube cada carpeta como una clase en https://teachablemachine.withgoogle.com/")
    print("Recuerda: imágenes sintéticas para demostración educativa, no clínicas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
