#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Imágenes de prueba NUEVAS (semillas disjuntas del entrenamiento) para el asistente ECG.

Uso:  python scripts/generar_pruebas_nuevas.py   ->  datasets/pruebas_nuevas/
"""
import csv, hashlib, os, random, shutil, subprocess, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(RAIZ, "datasets")
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
from generar_dataset_demo import render, MULTICLASE  # mismo generador del dataset de entrenamiento

OUT = os.path.join(BASE, "pruebas_nuevas")
N = 20
SEED0 = 700000          # el entrenamiento usó semillas 1000–4000; estas no se solapan

# nombre que muestra el modelo (metadata.json) para cada carpeta
ETIQUETA = {
    "normal": "ECG NORMAL", "brd": "BRD", "hbai": "HBAI", "brd_hbai": "BRD + HBAI",
    "bloqueo_av": "Bloqueo AV", "extrasistole_ventricular": "Extrasistole ventricular",
}

if os.path.isdir(OUT): shutil.rmtree(OUT)
os.makedirs(os.path.join(OUT, "por_clase"))
os.makedirs(os.path.join(OUT, "a_ciegas"))

items = []   # (ruta, carpeta, kind)
sid = SEED0
for folder, kind in MULTICLASE.items():
    os.makedirs(os.path.join(OUT, "por_clase", folder))
    for i in range(N):
        p = os.path.join(OUT, "por_clase", folder, f"{folder}_nueva_{i+1:02d}.png")
        render(p, kind, sid); sid += 1
        items.append((p, folder))

# copia a ciegas: nombres numéricos mezclados + clave de respuestas
random.Random(7).shuffle(items)
with open(os.path.join(OUT, "a_ciegas", "clave_respuestas.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["archivo", "clase_correcta"])
    for k, (src, folder) in enumerate(items, 1):
        name = f"prueba_{k:03d}.png"
        shutil.copyfile(src, os.path.join(OUT, "a_ciegas", name))
        w.writerow([name, ETIQUETA[folder]])

open(os.path.join(OUT, "LEEME.txt"), "w", encoding="utf-8").write(
"""IMAGENES DE PRUEBA NUEVAS - Asistente ECG Chagas
================================================

Son imagenes que el modelo NUNCA vio durante el entrenamiento (generadas con
semillas distintas; se verifico que ninguna es identica a una de entrenamiento).

  por_clase/   20 imagenes por patologia, en carpetas con su nombre (120 en total).
               Sirven para mostrar que cada patron se reconoce.
  a_ciegas/    las mismas 120 imagenes mezcladas y con nombre numerico, mas
               clave_respuestas.csv. Sirven para una prueba "a ciegas" ante el
               tribunal: se sube una, se lee la prediccion y luego se compara con la clave.

Como usarlas: abre asistente.html, arrastra una imagen y mira la lectura.

AVISO IMPORTANTE
Son imagenes SINTETICAS del mismo tipo que las de entrenamiento: son nuevas para
el modelo, pero no son fotos reales. Que las reconozca demuestra que el sistema
funciona, no que diagnostique ECG reales de pacientes.
""")

# verificación: ninguna imagen coincide byte a byte con el entrenamiento
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
train_hashes = set()
for root_dir in ("multiclase_6_clases", "binario_500_por_clase", "binario_60_por_clase"):
    d = os.path.join(BASE, root_dir)
    if os.path.isdir(d):
        for r, _, fs in os.walk(d):
            for f in fs:
                if f.endswith(".png"): train_hashes.add(sha(os.path.join(r, f)))
new_hashes = [sha(p) for p, _ in items]
print("imágenes nuevas:", len(new_hashes), "| únicas entre sí:", len(set(new_hashes)))
print("imágenes de entrenamiento comparadas:", len(train_hashes))
print("coincidencias con entrenamiento:", len(set(new_hashes) & train_hashes))
print("Carpeta generada:", OUT)
