#!/usr/bin/env python3
"""Convierte CirCor a WAV de 5 s y escribe data/audio/manifest.csv.

Cada ventana hereda la clase del sujeto según docs/audio_class_map.md.
El reparto train/test es por persona (y por Additional ID), semilla 42, 20 % test.
Los WAV procesados no se versionan. El manifiesto, los excluidos y el conteo sí.

Uso:
  python scripts/download_audio.py --dest data/audio/raw
  python scripts/prepare_audio.py --raw data/audio/raw --out data/audio

Salida:
  data/audio/processed/<clase>/*.wav     (gitignore)
  data/audio/manifest.csv                (sí se versiona)
  data/audio/excluidos.csv               (sí se versiona)
  data/audio/grupos.csv                  (record_id, grupo, split; para auditar la fuga)
  docs/audio_conteo.md                   (conteos reales de esta corrida)
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

import numpy as np

# El script vive en scripts/ y se ejecuta desde la raíz del repo.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audio_comun import (  # noqa: E402
    COLUMNAS_MANIFIESTO,
    SR,
    ArchivoAudio,
    Paciente,
    PlanAudio,
    comprobar_sin_fuga,
    focos_desde_texto,
    indices_ventanas,
    leer_wav_mono,
    n_muestras_a_4k,
    planificar,
    recortar_a_4k,
    resumir,
    escribir_wav,
)


def _vacio(valor: str | None) -> bool:
    return valor is None or str(valor).strip() == "" or str(valor).strip().lower() == "nan"


def encontrar_raiz(raw: Path) -> Path:
    candidatos = list(raw.rglob("training_data.csv"))
    if not candidatos:
        print(f"no está training_data.csv bajo {raw}. Ejecuta download_audio.py.", file=sys.stderr)
        sys.exit(1)
    return candidatos[0].parent


def leer_pacientes(csv_path: Path) -> list[Paciente]:
    with csv_path.open(newline="") as fh:
        filas = list(csv.DictReader(fh))
    pacientes = []
    for fila in filas:
        adicional = fila.get("Additional ID")
        pacientes.append(
            Paciente(
                record_id=str(fila["Patient ID"]).strip(),
                murmur=str(fila["Murmur"]).strip(),
                focos_soplo=focos_desde_texto(fila.get("Murmur locations")),
                additional_id=None if _vacio(adicional) else str(adicional).strip(),
                campana="" if _vacio(fila.get("Campaign")) else str(fila["Campaign"]).strip(),
                edad="" if _vacio(fila.get("Age")) else str(fila["Age"]).strip(),
                foco_mas_audible=""
                if _vacio(fila.get("Most audible location"))
                else str(fila["Most audible location"]).strip(),
            )
        )
    return pacientes


def leer_archivos(carpeta_wav: Path) -> list[ArchivoAudio]:
    import wave

    archivos = []
    for wav in sorted(carpeta_wav.glob("*.wav")):
        # El id es el primer tramo: 2530_MV.wav y 2530_MV_1.wav pertenecen a 2530.
        record_id = wav.stem.split("_", 1)[0]
        with wave.open(str(wav), "rb") as w:
            archivos.append(
                ArchivoAudio(
                    record_id=record_id,
                    nombre=wav.name,
                    n_muestras=w.getnframes(),
                    sr=w.getframerate(),
                )
            )
    return archivos


def escribir_csv(ruta: Path, columnas: list[str], filas: list[dict[str, str]]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columnas)
        writer.writeheader()
        for fila in filas:
            writer.writerow(fila)


def materializar(plan: PlanAudio, carpeta_wav: Path, out: Path) -> None:
    """Corta las ventanas que el plan ya aceptó. El orden de cortes coincide con indices_ventanas."""
    por_nombre: dict[str, list] = {}
    for fila in plan.filas:
        # processed/soplo/2530_MV_t0.wav -> 2530_MV.wav (se le quita _tN)
        tallo = Path(fila.file).stem
        base = tallo.rsplit("_t", 1)[0] + ".wav"
        por_nombre.setdefault(base, []).append(fila)

    hechas = 0
    for nombre, filas in por_nombre.items():
        onda, sr = leer_wav_mono(str(carpeta_wav / nombre))
        onda4 = recortar_a_4k(onda, sr)
        cortes = indices_ventanas(len(onda4))
        if len(cortes) < len(filas):
            raise RuntimeError(f"{nombre}: el plan pedía {len(filas)} ventanas y hay {len(cortes)}")
        for fila in filas:
            ini, fin = cortes[fila.ventana]
            destino = out / fila.file  # file ya incluye processed/...
            # `out` es data/audio y file es processed/clase/x.wav
            destino.parent.mkdir(parents=True, exist_ok=True)
            escribir_wav(str(destino), np.asarray(onda4[ini:fin]))
            hechas += 1
            if hechas % 500 == 0:
                print(f"[audio] ventanas escritas: {hechas}")
    print(f"[audio] ventanas escritas: {hechas}")


def redactar_conteo(plan: PlanAudio, destino: Path, murmullo_csv: Counter | None = None) -> None:
    resumen = resumir(plan)
    motivos = Counter(e.motivo for e in plan.excluidas)
    sujetos_excl = Counter()
    vistos = set()
    for e in plan.excluidas:
        clave = (e.record_id, e.motivo)
        if clave not in vistos:
            vistos.add(clave)
            sujetos_excl[e.motivo] += 1

    lineas = [
        "# Conteo del audio preparado",
        "",
        "Lo escribió `scripts/prepare_audio.py` a partir de CirCor 1.0.3.",
        "No hay filas sintéticas. `incierto` no está en el manifiesto: los sujetos",
        "`Unknown` y el resto de exclusiones están en `data/audio/excluidos.csv`.",
        "",
        "Unidad del reparto: sujeto (y pareja de `Additional ID`). Semilla 42, 20 % test.",
        "Cada clip dura 5,0 s, mono, 4 000 Hz. Como mucho 4 ventanas por grabación.",
        "",
        "## Clips (ventanas de 5 s)",
        "",
        "| Clase | Train | Test | Total |",
        "|---|---:|---:|---:|",
    ]
    for clase in ("normal", "soplo"):
        tr = resumen["clips"][clase]["train"]
        te = resumen["clips"][clase]["test"]
        lineas.append(f"| `{clase}` | {tr} | {te} | {tr + te} |")
    lineas += [
        "",
        "## Sujetos (un id de CirCor, una vez)",
        "",
        "| Clase | Train | Test | Total |",
        "|---|---:|---:|---:|",
    ]
    for clase in ("normal", "soplo"):
        tr = resumen["sujetos"][clase]["train"]
        te = resumen["sujetos"][clase]["test"]
        lineas.append(f"| `{clase}` | {tr} | {te} | {tr + te} |")
    lineas += [
        "",
        "## Exclusiones",
        "",
        "Un mismo sujeto puede aportar varias grabaciones. «Grabaciones» cuenta WAV;",
        "«sujetos» cuenta ids distintos con ese motivo (si un id tiene dos motivos, suma en los dos).",
        "",
        "| Motivo | Grabaciones | Sujetos |",
        "|---|---:|---:|",
    ]
    for motivo, n in sorted(motivos.items()):
        lineas.append(f"| `{motivo}` | {n} | {sujetos_excl[motivo]} |")
    if murmullo_csv is not None:
        ausentes = murmullo_csv.get("Absent", 0)
        presentes = murmullo_csv.get("Present", 0)
        desconocidos = murmullo_csv.get("Unknown", 0)
        lineas += [
            "",
            "## Cuadre con training_data.csv",
            "",
            f"El CSV público tiene {ausentes + presentes + desconocidos} sujetos: "
            f"{ausentes} Absent, {presentes} Present y {desconocidos} Unknown.",
            "Un sujeto Unknown ligado a otra ficha con otra etiqueta cuenta solo en",
            "`etiqueta_discordante`. Los sujetos con un foco excluido (`foco_sin_soplo`)",
            "siguen en el manifiesto por los focos donde sí se anotó el soplo.",
            "",
        ]
    lineas += [
        "",
        "Motivos:",
        "",
        "- `murmur_unknown`: el anotador no decidió. No se entrena como `incierto`.",
        "- `etiqueta_discordante`: la misma persona, en las dos campañas, no tiene el mismo `Murmur`.",
        "- `foco_sin_soplo`: el sujeto tiene soplo, pero no en ese foco.",
        "- `duracion_menor_5s`: no cabe una ventana de 5 s.",
        "",
        "Ningún sujeto del manifiesto está a la vez en train y en test.",
        "La comprobación también cubre el id de grupo (Additional ID).",
        "",
    ]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepara ventanas WAV y el manifiesto de CirCor.")
    parser.add_argument("--raw", default="data/audio/raw")
    parser.add_argument("--out", default="data/audio", help="raíz de processed/, manifest.csv y grupos.csv")
    parser.add_argument("--conteo", default="docs/audio_conteo.md")
    parser.add_argument(
        "--sin-wav",
        action="store_true",
        help="solo reescribe manifiesto, exclusiones y conteo; no vuelve a cortar los WAV",
    )
    args = parser.parse_args()

    raiz = encontrar_raiz(Path(args.raw))
    print(f"[audio] dataset en {raiz}")
    pacientes = leer_pacientes(raiz / "training_data.csv")
    archivos = leer_archivos(raiz / "training_data")
    print(f"[audio] sujetos en el CSV: {len(pacientes)}; WAV: {len(archivos)}")

    plan = planificar(pacientes, archivos)
    comprobar_sin_fuga(plan.filas)

    out = Path(args.out)
    if args.sin_wav:
        print("[audio] se omite el recorte de WAV")
    else:
        materializar(plan, raiz / "training_data", out)

    filas_csv = [f.como_dict() for f in sorted(plan.filas, key=lambda r: (r.record_id, r.file))]
    escribir_csv(out / "manifest.csv", list(COLUMNAS_MANIFIESTO), filas_csv)

    excl = sorted(plan.excluidas, key=lambda e: (e.motivo, e.record_id, e.nombre))
    escribir_csv(
        out / "excluidos.csv",
        ["record_id", "file", "motivo", "notes"],
        [
            {"record_id": e.record_id, "file": e.nombre, "motivo": e.motivo, "notes": e.notes}
            for e in excl
        ],
    )

    # Una fila por sujeto incluido, para comprobar que el grupo no cruza el split.
    visto_sujeto: dict[str, dict[str, str]] = {}
    for fila in plan.filas:
        visto_sujeto[fila.record_id] = {
            "record_id": fila.record_id,
            "grupo": fila.grupo,
            "split": fila.split,
            "class": fila.clase,
        }
    escribir_csv(
        out / "grupos.csv",
        ["record_id", "grupo", "split", "class"],
        [visto_sujeto[k] for k in sorted(visto_sujeto)],
    )

    redactar_conteo(plan, Path(args.conteo), Counter(p.murmur for p in pacientes))
    resumen = resumir(plan)
    print("[audio] clips", resumen["clips"])
    print("[audio] sujetos", resumen["sujetos"])
    print("[audio] exclusiones", Counter(e.motivo for e in plan.excluidas))
    print(f"[audio] manifiesto: {out / 'manifest.csv'} ({len(filas_csv)} filas)")


if __name__ == "__main__":
    main()
