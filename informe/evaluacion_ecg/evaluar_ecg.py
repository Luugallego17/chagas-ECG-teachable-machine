#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recalcula las métricas del modelo de ECG sobre las 120 imágenes sintéticas de prueba.

Uso, desde la raíz del repositorio:

    python informe/evaluacion_ecg/evaluar_ecg.py

Lee predicciones_ecg_120.csv (o predicciones_raw.json si se pasa --desde-crudo)
y comprueba que la exactitud, la matriz de confusión y el recuento de confianza
baja coincidan con metricas_ecg_120.json.

Estas cifras son las de la Tabla 7 y la Figura 6 del informe. Las imágenes son
sintéticas (datasets/pruebas_nuevas/por_clase/), no electrocardiogramas reales.
Para volver a correr el modelo en el navegador, ver el README de esta carpeta.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
UMBRAL_BAJA = 0.7

ETIQUETA = {
    "normal": "ECG NORMAL",
    "brd": "BRD",
    "hbai": "HBAI",
    "brd_hbai": "BRD + HBAI",
    "bloqueo_av": "Bloqueo AV",
    "extrasistole_ventricular": "Extrasistole ventricular",
}


def filas_desde_csv(ruta: Path) -> list[dict]:
    with ruta.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def filas_desde_crudo(ruta: Path) -> list[dict]:
    crudo = json.loads(ruta.read_text(encoding="utf-8"))
    filas = []
    for item in crudo:
        probs = {nombre: float(p) for nombre, p in item["probs"]}
        predicha = max(probs, key=probs.get)
        carpeta = item["carpeta"]
        filas.append(
            {
                "archivo": f"{carpeta}/{item['archivo']}",
                "clase_real": ETIQUETA[carpeta],
                "clase_predicha": predicha,
                "prob_max": probs[predicha],
                **probs,
            }
        )
    return filas


def metricas(filas: list[dict], etiquetas: list[str]) -> dict:
    indice = {e: i for i, e in enumerate(etiquetas)}
    cm = [[0] * len(etiquetas) for _ in etiquetas]
    aciertos = 0
    baja = 0
    for fila in filas:
        real = fila["clase_real"]
        pred = fila["clase_predicha"]
        cm[indice[real]][indice[pred]] += 1
        if real == pred:
            aciertos += 1
        if float(fila["prob_max"]) < UMBRAL_BAJA:
            baja += 1
    n = len(filas)
    return {"labels": etiquetas, "cm": cm, "acc": aciertos / n if n else 0.0, "n": n, "low": baja}


def resumen(filas: list[dict], etiq: list[str]) -> None:
    aciertos = sum(1 for f in filas if f["clase_real"] == f["clase_predicha"])
    errores = [f for f in filas if f["clase_real"] != f["clase_predicha"]]
    baja_en_error = sum(1 for f in errores if float(f["prob_max"]) < UMBRAL_BAJA)
    print(f"Imágenes: {len(filas)}")
    print(f"Aciertos: {aciertos}")
    print(f"Exactitud: {aciertos / len(filas):.2%} ({aciertos} de {len(filas)})")
    print(f"Confianza baja (prob_max < {UMBRAL_BAJA:g}): {sum(1 for f in filas if float(f['prob_max']) < UMBRAL_BAJA)}")
    print(f"Errores con confianza baja: {baja_en_error} de {len(errores)}")
    print("Por clase (aciertos / 20):")
    for e in etiq:
        ok = sum(1 for f in filas if f["clase_real"] == e and f["clase_predicha"] == e)
        print(f"  {e}: {ok}/20")
    pares = Counter((f["clase_real"], f["clase_predicha"]) for f in errores)
    if pares:
        print("Confusiones:")
        for (real, pred), n in pares.most_common():
            print(f"  {real} → {pred}: {n}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--desde-crudo",
        action="store_true",
        help="Calcular a partir de predicciones_raw.json en lugar del CSV",
    )
    args = parser.parse_args()

    if args.desde_crudo:
        filas = filas_desde_crudo(CARPETA / "predicciones_raw.json")
    else:
        filas = filas_desde_csv(CARPETA / "predicciones_ecg_120.csv")

    esperadas = json.loads((CARPETA / "metricas_ecg_120.json").read_text(encoding="utf-8"))
    obtenidas = metricas(filas, esperadas["labels"])
    resumen(filas, esperadas["labels"])

    ok = (
        obtenidas["n"] == esperadas["n"]
        and obtenidas["low"] == esperadas["low"]
        and obtenidas["cm"] == esperadas["cm"]
        and abs(obtenidas["acc"] - esperadas["acc"]) < 1e-12
    )
    if not ok:
        print("Las métricas calculadas no coinciden con metricas_ecg_120.json", file=sys.stderr)
        print(json.dumps(obtenidas, ensure_ascii=False, indent=1), file=sys.stderr)
        return 1
    print("Las métricas coinciden con metricas_ecg_120.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
