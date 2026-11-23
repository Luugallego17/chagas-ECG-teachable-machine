#!/usr/bin/env python3
"""Entrena la CNN de fonocardiograma y la exporta a TensorFlow.js.

Teachable Machine Audio no entra: no se puede automatizar y sus ventanas de
cerca de un segundo están pensadas para voz o sonidos ambientales. Aquí el
modelo ve el log-mel de 5 s (scripts/audio_comun.py) y solo los WAV del split
train. El split test se evalúa una vez, al final.

Uso:
  python scripts/entrenar_audio.py \
      --manifest data/audio/manifest.csv \
      --audio data/audio \
      --out modelo/audio

No afirma un diagnóstico de Chagas. Las métricas que escribe son las que
calcula; si un denominador es cero, el valor queda en null.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audio_comun import (  # noqa: E402
    ETIQUETA_A_INDICE,
    FMAX,
    FMIN,
    FRAME_LENGTH,
    FRAME_STEP,
    FFT_LENGTH,
    N_FRAMES,
    N_MELS,
    N_SAMPLES,
    SR,
    leer_wav_mono,
    log_mel,
    metricas_binarias,
)
from exportar_tfjs import exportar_tfjs  # noqa: E402


def cargar(manifest: Path, audio: Path, cache: Path):
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        return z["x"], z["y"], z["ids"], z["splits"]

    import csv

    with manifest.open(newline="") as fh:
        filas = list(csv.DictReader(fh))
    x = np.empty((len(filas), N_MELS, N_FRAMES, 1), dtype=np.float32)
    y = np.empty(len(filas), dtype=np.int64)
    ids = np.empty(len(filas), dtype="U16")
    splits = np.empty(len(filas), dtype="U8")
    for i, fila in enumerate(filas):
        if fila["class"] not in ETIQUETA_A_INDICE:
            raise SystemExit(f"clase fuera de contrato: {fila['class']}")
        if "sintetico=si" in fila["notes"]:
            raise SystemExit("el manifiesto real no puede traer audio sintético")
        onda, sr = leer_wav_mono(str(audio / fila["file"]))
        if sr != SR or len(onda) != N_SAMPLES:
            raise SystemExit(f"{fila['file']}: se esperaba {N_SAMPLES} muestras a {SR} Hz")
        x[i, :, :, 0] = log_mel(onda)
        y[i] = ETIQUETA_A_INDICE[fila["class"]]
        ids[i] = fila["record_id"]
        splits[i] = fila["split"]
        if (i + 1) % 2000 == 0:
            print(f"[entrenar] espectrogramas {i + 1}/{len(filas)}")
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, x=x, y=y, ids=ids, splits=splits)
    return x, y, ids, splits


def partir_validacion(ids: np.ndarray, y: np.ndarray, semilla: int = 43, fraccion: float = 0.15):
    """15 % de los sujetos de train, estratificado. No toca el test."""
    rng = np.random.default_rng(semilla)
    clase_de = {}
    for rid, clase in zip(ids.tolist(), y.tolist()):
        clase_de[rid] = int(clase)
    por_clase: dict[int, list[str]] = {0: [], 1: []}
    for rid, clase in clase_de.items():
        por_clase[clase].append(rid)
    val: set[str] = set()
    for lista in por_clase.values():
        orden = list(lista)
        rng.shuffle(orden)
        n = int(round(len(orden) * fraccion))
        if len(orden) >= 2:
            n = min(max(1, n), len(orden) - 1)
        else:
            n = 0
        val.update(orden[:n])
    ajuste = np.array([rid not in val for rid in ids.tolist()])
    return ajuste, val


def indices_equilibrados(y: np.ndarray, semilla: int = 42) -> np.ndarray:
    """Repite ventanas reales de soplo hasta igualar a normal. No crea audio nuevo."""
    rng = np.random.default_rng(semilla)
    i0 = np.flatnonzero(y == 0)
    i1 = np.flatnonzero(y == 1)
    if len(i1) == 0 or len(i0) == 0:
        return np.arange(len(y))
    rep = int(np.ceil(len(i0) / len(i1)))
    orden = np.concatenate([i0, np.tile(i1, rep)])
    rng.shuffle(orden)
    return orden


def construir():
    import tensorflow as tf

    return tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(N_MELS, N_FRAMES, 1), name="entrada"),
            tf.keras.layers.Conv2D(16, 3, padding="same", activation="relu", name="conv_1"),
            tf.keras.layers.MaxPooling2D(2, name="pool_1"),
            tf.keras.layers.Conv2D(32, 3, padding="same", activation="relu", name="conv_2"),
            tf.keras.layers.MaxPooling2D(2, name="pool_2"),
            tf.keras.layers.Conv2D(64, 3, padding="same", activation="relu", name="conv_3"),
            tf.keras.layers.GlobalAveragePooling2D(name="gap"),
            tf.keras.layers.Dropout(0.3, name="drop"),
            tf.keras.layers.Dense(32, activation="relu", name="densa"),
            tf.keras.layers.Dense(2, activation="softmax", name="salida"),
        ],
        name="fonocardiograma",
    )


def entrenar_una(x, y, x_val, y_val, id_val, epocas: int, paciencia: int):
    """Ajusta con lotes equilibrados y se queda con el Youden más alto en validación.

    Youden = sensibilidad + especificidad - 1, por sujeto, umbral 0,5.
    La pérdida de validación no sirve aquí: el lote de ajuste está equilibrado
    y el de validación no.
    """
    import tensorflow as tf

    tf.keras.utils.set_random_seed(42)
    modelo = construir()
    modelo.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
    )
    orden = indices_equilibrados(y)
    mejor_j = -1.0
    mejor_pesos = None
    mejor_epoca = 0
    sin_mejora = 0
    corridas = 0
    for epoca in range(1, epocas + 1):
        modelo.fit(x[orden], y[orden], epochs=1, batch_size=64, verbose=2)
        corridas = epoca
        p = prob_soplo(modelo, x_val)
        real, pred = por_sujeto(id_val, y_val, p, 0.5)
        m = metricas_binarias(real, pred)
        youden = -1.0
        if m["sensibilidad"] is not None and m["especificidad"] is not None:
            youden = m["sensibilidad"] + m["especificidad"] - 1.0
        print(
            f"[entrenar] época {epoca}: sensibilidad {m['sensibilidad']} "
            f"especificidad {m['especificidad']} youden {youden:.4f}"
        )
        if youden > mejor_j:
            mejor_j = youden
            mejor_epoca = epoca
            mejor_pesos = modelo.get_weights()
            sin_mejora = 0
        else:
            sin_mejora += 1
            if sin_mejora >= paciencia:
                break
    if mejor_pesos is not None:
        modelo.set_weights(mejor_pesos)
    return modelo, mejor_epoca, corridas, mejor_j


def prob_soplo(modelo, x: np.ndarray) -> np.ndarray:
    pred = modelo.predict(x, batch_size=128, verbose=0)
    return pred[:, 1]


def por_sujeto(ids: np.ndarray, y: np.ndarray, p_soplo: np.ndarray, umbral: float):
    grupos: dict[str, list[int]] = {}
    for i, rid in enumerate(ids.tolist()):
        grupos.setdefault(rid, []).append(i)
    y_real = []
    y_pred = []
    for indices in grupos.values():
        real = int(y[indices[0]])
        media = float(np.mean(p_soplo[indices]))
        y_real.append(real)
        y_pred.append(1 if media >= umbral else 0)
    return np.array(y_real), np.array(y_pred)


def sensibilidad_val(modelo, x, y, ids) -> float | None:
    p = prob_soplo(modelo, x)
    real, pred = por_sujeto(ids, y, p, 0.5)
    return metricas_binarias(real, pred)["sensibilidad"]


def redondear(valor):
    if valor is None:
        return None
    return round(float(valor), 4)


def bloque(m: dict) -> dict:
    return {
        "n": m["n"],
        "tp": m["tp"],
        "tn": m["tn"],
        "fp": m["fp"],
        "fn": m["fn"],
        "matriz": m["matriz"],
        "exactitud": redondear(m["exactitud"]),
        "sensibilidad_soplo": redondear(m["sensibilidad"]),
        "especificidad_soplo": redondear(m["especificidad"]),
    }


def linea_base(y_real: np.ndarray) -> dict:
    n = len(y_real)
    n_soplo = int(np.sum(y_real == 1))
    n_normal = n - n_soplo
    if n_normal >= n_soplo:
        clase, aciertos = "normal", n_normal
    else:
        clase, aciertos = "soplo", n_soplo
    return {
        "clase": clase,
        "exactitud": redondear(aciertos / n if n else None),
        "n": n,
    }


def redactar(metricas: dict, meta: dict, destino: Path) -> None:
    s = metricas["sujeto_umbral_0_5"]
    c = metricas["clip_umbral_0_5"]
    base = metricas["linea_base_sujeto"]

    def pct(v):
        if v is None:
            return "no calculable (denominador cero)"
        return f"{v:.4f}"

    texto = f"""# Modelo de fonocardiograma

CNN pequeña sobre el log-mel de 5 s. No es Teachable Machine Audio: esa herramienta
no se puede automatizar y está pensada para ventanas de cerca de un segundo de voz
o de sonidos ambientales. El fonocardiograma es más largo y de frecuencia baja.

| | |
|---|---|
| Fuente | CirCor DigiScope v1.0.3, ODC-By 1.0, https://doi.org/10.13026/tshs-mw03 |
| Clases | `normal`, `soplo`. `incierto` no se entrenó. |
| Datos | Solo el split `train` del manifiesto. Dentro de train, un 15 % de sujetos (semilla 43) eligió la época por el índice de Youden. En el ajuste, las ventanas reales de soplo se repiten hasta igualar a las normales; no hay audio sintético. El test no se usó para elegir nada. |
| Fecha | {meta["fecha"]} |
| Diagnóstico | No. No detecta Chagas. CirCor es pediátrico (0 a 21 años). |

## Métricas en el test, por sujeto

La etiqueta de CirCor es del sujeto. La probabilidad del sujeto es la media de
sus ventanas. Umbral 0,5. La matriz es [[tn, fp], [fn, tp]] con orden [normal, soplo].

| | |
|---|---|
| Sujetos | {s["n"]} |
| Exactitud | {pct(s["exactitud"])} |
| Sensibilidad (soplo) | {pct(s["sensibilidad_soplo"])} |
| Especificidad (soplo) | {pct(s["especificidad_soplo"])} |
| Matriz | {s["matriz"]} |
| Línea de base (siempre la clase mayoritaria del test, `{base["clase"]}`) | {pct(base["exactitud"])} |

Por ventana, con el mismo umbral: exactitud {pct(c["exactitud"])}, sensibilidad {pct(c["sensibilidad_soplo"])}, especificidad {pct(c["especificidad_soplo"])}, n = {c["n"]}, matriz {c["matriz"]}.

Estas cifras no son una validación clínica. El 40 % que CirCor retuvo para el
reto de PhysioNet 2022 no está en los datos públicos, así que esto es un corte
interno por sujeto, no el ranking del reto.

El detalle numérico está en `metricas.json`. Si un denominador fue cero, el
campo correspondiente es null.
"""
    (destino / "README.md").write_text(texto, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Entrena y exporta el modelo de audio.")
    parser.add_argument("--manifest", default="data/audio/manifest.csv")
    parser.add_argument("--audio", default="data/audio")
    parser.add_argument("--cache", default="data/audio/cache/features.npz")
    parser.add_argument("--out", default="modelo/audio")
    parser.add_argument("--epocas", type=int, default=12)
    parser.add_argument("--paciencia", type=int, default=3)
    args = parser.parse_args()

    import tensorflow as tf

    tf.keras.utils.set_random_seed(42)
    x, y, ids, splits = cargar(Path(args.manifest), Path(args.audio), Path(args.cache))
    ent = splits == "train"
    prueba = splits == "test"
    ajuste_mask, sujetos_val = partir_validacion(ids[ent], y[ent])
    # ajuste_mask está alineado con el subconjunto train, no con el arreglo completo.
    x_tr, y_tr, id_tr = x[ent], y[ent], ids[ent]
    x_fit, y_fit = x_tr[ajuste_mask], y_tr[ajuste_mask]
    x_val, y_val, id_val = x_tr[~ajuste_mask], y_tr[~ajuste_mask], id_tr[~ajuste_mask]
    print(f"[entrenar] fit {len(y_fit)} val {len(y_val)} test {int(prueba.sum())}")
    print(f"[entrenar] sujetos de validación interna: {len(sujetos_val)}")

    modelo, mejor, corridas, youden = entrenar_una(
        x_fit, y_fit, x_val, y_val, id_val, args.epocas, args.paciencia
    )
    sens = sensibilidad_val(modelo, x_val, y_val, id_val)
    print(f"[entrenar] sensibilidad de soplo en validación, pesos elegidos: {sens}")

    p_clip = prob_soplo(modelo, x[prueba])
    y_test = y[prueba]
    id_test = ids[prueba]
    pred_clip = (p_clip >= 0.5).astype(int)
    m_clip = metricas_binarias(y_test, pred_clip)
    y_suj, pred_suj = por_sujeto(id_test, y_test, p_clip, 0.5)
    m_suj = metricas_binarias(y_suj, pred_suj)
    base = linea_base(y_suj)

    destino = Path(args.out)
    destino.mkdir(parents=True, exist_ok=True)
    exportar_tfjs(modelo, destino)

    meta = {
        "labels": ["normal", "soplo"],
        "etiquetasApp": {
            "normal": "Sonido cardíaco sin soplo",
            "soplo": "Soplo cardíaco (anomalía general)",
            "incierto": "Incierto",
        },
        "umbralSoplo": 0.5,
        "umbralConfianzaBaja": 0.6,
        "entrada": {"mel": N_MELS, "tiempo": N_FRAMES, "canales": 1},
        "preproceso": {
            "sampleRate": SR,
            "durationS": 5,
            "samples": N_SAMPLES,
            "frameLength": FRAME_LENGTH,
            "frameStep": FRAME_STEP,
            "fftLength": FFT_LENGTH,
            "nMels": N_MELS,
            "fmin": FMIN,
            "fmax": FMAX,
            "ventana": "hann periodica",
            "mel": "HTK triangular, sin normalizar el área",
            "normalizacion": "z-score del recorte, desviación con divisor n",
            "recorte": "primeros 5 s",
        },
        "fuente": "The CirCor DigiScope Phonocardiogram Dataset, versión 1.0.3",
        "enlace": "https://physionet.org/content/circor-heart-sound/1.0.3/",
        "doi": "https://doi.org/10.13026/tshs-mw03",
        "licencia": "Open Data Commons Attribution License v1.0",
        "herramienta": "Keras / TensorFlow, exportado a TensorFlow.js por scripts/exportar_tfjs.py",
        "motivoAlternativa": (
            "Teachable Machine Audio no se puede automatizar y trabaja con ventanas "
            "de cerca de 1 s pensadas para voz o sonidos ambientales. El fonocardiograma "
            "es más largo y de frecuencia baja, así que se entrenó una CNN pequeña sobre el log-mel."
        ),
        "fecha": date.today().isoformat(),
        "entrenadoConDatosReales": True,
        "esDemostracion": False,
        "noDiagnosticaChagas": True,
        "poblacion": "Pediátrica (CirCor, 0 a 21 años). No equivale a la miocardiopatía chagásica del adulto.",
        "clasesEntrenadas": ["normal", "soplo"],
        "incierto": (
            "No es una clase entrenada. La aplicación la muestra si el audio dura menos de 5 s, "
            "no se puede leer o está en silencio."
        ),
    }
    metricas = {
        "unidad_principal": "sujeto",
        "umbral": 0.5,
        "positivo": "soplo",
        "orden_matriz": "filas = real [normal, soplo]; columnas = predicho [normal, soplo]; valores [[tn, fp], [fn, tp]]",
        "sujeto_umbral_0_5": bloque(m_suj),
        "clip_umbral_0_5": bloque(m_clip),
        "linea_base_sujeto": base,
        "n_clips_train_ajuste": int(len(y_fit)),
        "n_clips_validacion_interna": int(len(y_val)),
        "n_sujetos_validacion_interna": len(sujetos_val),
        "sensibilidad_soplo_validacion_interna": redondear(sens),
        "youden_validacion_interna": redondear(youden),
        "equilibrio_ajuste": (
            "En el ajuste se repiten ventanas reales de soplo hasta igualar el número "
            "de ventanas normales. No se sintetiza audio. Validación y test quedan como están."
        ),
        "epocas_mejor_youden": mejor,
        "epocas_corridas": corridas,
        "semilla_split_manifest": 42,
        "semilla_validacion_interna": 43,
        "no_es_validacion_clinica": True,
        "no_diagnostica_chagas": True,
    }
    (destino / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destino / "metricas.json").write_text(
        json.dumps(metricas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    redactar(metricas, meta, destino)
    print(json.dumps(metricas["sujeto_umbral_0_5"], ensure_ascii=False))
    print("[entrenar] escrito en", destino)


if __name__ == "__main__":
    main()
