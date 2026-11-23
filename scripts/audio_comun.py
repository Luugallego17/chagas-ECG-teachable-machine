#!/usr/bin/env python3
"""Constantes y reglas compartidas del fonocardiograma.

Las clases salen de CirCor (Present / Absent / Unknown). No existe una clase
de Chagas: no hay audio público para sostenerla. Los sonidos sintéticos solo
se construyen en los tests y tienen que decirlo en el nombre o en la nota.
"""
from __future__ import annotations

import math
import wave
from dataclasses import dataclass, field

import numpy as np

# Ventana que ve el modelo. CirCor ya viene a 4 kHz, mono.
SR = 4000
DURATION_S = 5.0
N_SAMPLES = int(SR * DURATION_S)  # 20 000

# STFT. 155 cuadros: el último empieza en la muestra 19 712 y sobran 32 muestras.
FRAME_LENGTH = 256
FRAME_STEP = 128
FFT_LENGTH = 256
N_BINS = FFT_LENGTH // 2 + 1  # 129
N_FRAMES = 1 + (N_SAMPLES - FRAME_LENGTH) // FRAME_STEP  # 155

# Banco mel HTK, de 20 a 800 Hz: cubre S1/S2 y el grueso de los soplos.
N_MELS = 64
FMIN = 20.0
FMAX = 800.0
LOG_EPS = 1e-6

# Como mucho cuatro ventanas de 5 s por grabación, desde el inicio.
# Así un registro de 80 s no aplasta al resto.
MAX_VENTANAS = 4

SEMILLA_SPLIT = 42
FRACCION_TEST = 0.20

CLASES_ENTRENADAS = ("normal", "soplo")
# Orden fijo de la última capa: índice 0 = normal, índice 1 = soplo.
ETIQUETA_A_INDICE = {"normal": 0, "soplo": 1}

MURMUR_A_CLASE = {
    "Absent": "normal",
    "Present": "soplo",
    "Unknown": "incierto",
}

# Silencio absoluto (RMS). Por debajo, la app no inventa una clase.
UMBRAL_SILENCIO = 1e-4

COLUMNAS_MANIFIESTO = (
    "file",
    "class",
    "source",
    "record_id",
    "split",
    "duration_s",
    "notes",
)


@dataclass
class Paciente:
    """Una ficha de sujeto de training_data.csv. Los ids son los del dataset público."""

    record_id: str
    murmur: str
    focos_soplo: frozenset[str]
    additional_id: str | None
    campana: str
    edad: str
    foco_mas_audible: str


@dataclass
class ArchivoAudio:
    record_id: str
    nombre: str  # p. ej. 2530_MV.wav o 2530_MV_1.wav
    n_muestras: int
    sr: int


@dataclass
class FilaManifiesto:
    file: str
    clase: str
    source: str
    record_id: str
    split: str
    duration_s: float
    notes: str
    grupo: str = ""
    ventana: int = 0

    def como_dict(self) -> dict[str, str]:
        return {
            "file": self.file,
            "class": self.clase,
            "source": self.source,
            "record_id": self.record_id,
            "split": self.split,
            "duration_s": f"{self.duration_s:.1f}",
            "notes": self.notes,
        }


@dataclass
class FilaExcluida:
    record_id: str
    nombre: str
    motivo: str
    notes: str


@dataclass
class PlanAudio:
    filas: list[FilaManifiesto] = field(default_factory=list)
    excluidas: list[FilaExcluida] = field(default_factory=list)
    grupos: dict[str, str] = field(default_factory=dict)  # record_id -> grupo
    motivo_grupo: dict[str, str] = field(default_factory=dict)  # grupo -> motivo o ""


def foco_de_nombre(nombre: str) -> str:
    """2530_MV.wav -> MV; 50782_MV_2.wav -> MV."""
    tallo = nombre.rsplit(".", 1)[0]
    partes = tallo.split("_")
    if len(partes) < 2 or not partes[1]:
        raise ValueError(f"nombre de grabación no reconocido: {nombre}")
    return partes[1]


def _vacio(valor: str | None) -> bool:
    return valor is None or valor.strip() == "" or valor.strip().lower() == "nan"


def focos_desde_texto(texto: str | None) -> frozenset[str]:
    if _vacio(texto):
        return frozenset()
    return frozenset(p.strip() for p in str(texto).split("+") if p.strip() and p.strip().lower() != "nan")


def agrupar_sujetos(pacientes: list[Paciente]) -> dict[str, str]:
    """Une a quien comparte Additional ID. El id de grupo es el menor record_id."""
    ids = [p.record_id for p in pacientes]
    padre = {i: i for i in ids}

    def encontrar(x: str) -> str:
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    def unir(a: str, b: str) -> None:
        ra, rb = encontrar(a), encontrar(b)
        if ra != rb:
            # El menor id queda como raíz para que el grupo no dependa del orden de unión.
            if ra < rb:
                padre[rb] = ra
            else:
                padre[ra] = rb

    por_id = {p.record_id: p for p in pacientes}
    for p in pacientes:
        otro = p.additional_id
        if otro and otro in por_id and otro != p.record_id:
            unir(p.record_id, otro)

    miembros: dict[str, list[str]] = {}
    for i in ids:
        miembros.setdefault(encontrar(i), []).append(i)
    canon: dict[str, str] = {}
    for mem in miembros.values():
        grupo = min(mem)
        for i in mem:
            canon[i] = grupo
    return canon


def n_muestras_a_4k(n_muestras: int, sr: int) -> int:
    if sr == SR:
        return n_muestras
    if sr <= 0:
        return 0
    return int(round(n_muestras * SR / float(sr)))


def indices_ventanas(n_muestras_4k: int, max_ventanas: int = MAX_VENTANAS) -> list[tuple[int, int]]:
    n_win = min(max_ventanas, n_muestras_4k // N_SAMPLES)
    return [(i * N_SAMPLES, (i + 1) * N_SAMPLES) for i in range(n_win)]


def asignar_splits(
    grupos_por_clase: dict[str, list[str]],
    semilla: int = SEMILLA_SPLIT,
    fraccion: float = FRACCION_TEST,
) -> dict[str, str]:
    """Reparte grupos (no archivos) en train/test, estratificado por la clase del grupo.

    La misma persona no puede quedar en los dos lados: aquí el id ya es el del grupo.
    """
    import random

    rng = random.Random(semilla)
    salida: dict[str, str] = {}
    for clase in ("normal", "soplo"):
        ids = list(grupos_por_clase.get(clase, []))
        rng.shuffle(ids)
        n_test = int(round(len(ids) * fraccion))
        if len(ids) >= 2:
            n_test = min(max(1, n_test), len(ids) - 1)
        else:
            n_test = 0
        for i, gid in enumerate(ids):
            salida[gid] = "test" if i < n_test else "train"
    return salida


def planificar(
    pacientes: list[Paciente],
    archivos: list[ArchivoAudio],
    semilla: int = SEMILLA_SPLIT,
    fraccion: float = FRACCION_TEST,
    max_ventanas: int = MAX_VENTANAS,
) -> PlanAudio:
    """Decide filas del manifiesto y exclusiones. No lee ni escribe WAV."""
    plan = PlanAudio()
    por_id = {p.record_id: p for p in pacientes}
    grupos = agrupar_sujetos(pacientes)
    plan.grupos = grupos

    miembros: dict[str, list[Paciente]] = {}
    for p in pacientes:
        miembros.setdefault(grupos[p.record_id], []).append(p)

    clase_grupo: dict[str, str] = {}
    for gid, grupo in miembros.items():
        etiquetas = {p.murmur for p in grupo}
        if len(etiquetas) != 1:
            plan.motivo_grupo[gid] = "etiqueta_discordante"
            continue
        murmur = next(iter(etiquetas))
        if murmur == "Unknown":
            plan.motivo_grupo[gid] = "murmur_unknown"
            continue
        if murmur not in ("Present", "Absent"):
            plan.motivo_grupo[gid] = "murmur_no_reconocido"
            continue
        plan.motivo_grupo[gid] = ""
        clase_grupo[gid] = MURMUR_A_CLASE[murmur]

    splits = asignar_splits(
        {
            "normal": [g for g, c in clase_grupo.items() if c == "normal"],
            "soplo": [g for g, c in clase_grupo.items() if c == "soplo"],
        },
        semilla=semilla,
        fraccion=fraccion,
    )

    for archivo in archivos:
        paciente = por_id.get(archivo.record_id)
        if paciente is None:
            plan.excluidas.append(
                FilaExcluida(archivo.record_id, archivo.nombre, "sin_etiqueta", "no está en training_data.csv")
            )
            continue
        gid = grupos[archivo.record_id]
        motivo = plan.motivo_grupo.get(gid, "sin_grupo")
        if motivo:
            plan.excluidas.append(
                FilaExcluida(archivo.record_id, archivo.nombre, motivo, f"grupo {gid}")
            )
            continue
        try:
            foco = foco_de_nombre(archivo.nombre)
        except ValueError as exc:
            plan.excluidas.append(FilaExcluida(archivo.record_id, archivo.nombre, "nombre_raro", str(exc)))
            continue

        clase = clase_grupo[gid]
        if clase == "soplo" and foco not in paciente.focos_soplo:
            plan.excluidas.append(
                FilaExcluida(
                    archivo.record_id,
                    archivo.nombre,
                    "foco_sin_soplo",
                    f"foco {foco} fuera de Murmur locations",
                )
            )
            continue

        n4k = n_muestras_a_4k(archivo.n_muestras, archivo.sr)
        ventanas = indices_ventanas(n4k, max_ventanas=max_ventanas)
        if not ventanas:
            plan.excluidas.append(
                FilaExcluida(
                    archivo.record_id,
                    archivo.nombre,
                    "duracion_menor_5s",
                    f"{n4k / SR:.2f} s a {SR} Hz",
                )
            )
            continue

        tallo = archivo.nombre.rsplit(".", 1)[0]
        split = splits[gid]
        for i, _recorte in enumerate(ventanas):
            notas = [
                f"murmur {paciente.murmur}",
                f"foco {foco}",
                f"ventana {i}",
                "sintetico=no",
            ]
            if not _vacio(paciente.edad):
                notas.append(f"edad {paciente.edad}")
            if not _vacio(paciente.campana):
                notas.append(f"campana {paciente.campana}")
            if clase == "soplo" and not _vacio(paciente.foco_mas_audible):
                notas.append(f"mas audible {paciente.foco_mas_audible}")
            plan.filas.append(
                FilaManifiesto(
                    file=f"processed/{clase}/{tallo}_t{i}.wav",
                    clase=clase,
                    source="circor",
                    record_id=archivo.record_id,
                    split=split,
                    duration_s=DURATION_S,
                    notes=", ".join(notas),
                    grupo=gid,
                    ventana=i,
                )
            )

    # El reparto es por grupo: ningún record_id (ni su pareja de campaña) cruza el corte.
    vistos: dict[str, str] = {}
    for fila in plan.filas:
        previo = vistos.get(fila.grupo)
        if previo is not None and previo != fila.split:
            raise RuntimeError(f"el grupo {fila.grupo} quedó en train y en test")
        vistos[fila.grupo] = fila.split
        if fila.clase not in CLASES_ENTRENADAS:
            raise RuntimeError(f"clase no entrenable en el manifiesto: {fila.clase}")
    return plan


def resumir(plan: PlanAudio) -> dict[str, dict[str, int]]:
    """Conteos de clips y de sujetos por clase y split. Los sujetos se cuentan una vez."""
    clips: dict[str, dict[str, int]] = {
        clase: {"train": 0, "test": 0} for clase in CLASES_ENTRENADAS
    }
    sujetos: dict[str, dict[str, set[str]]] = {
        clase: {"train": set(), "test": set()} for clase in CLASES_ENTRENADAS
    }
    for fila in plan.filas:
        clips[fila.clase][fila.split] += 1
        sujetos[fila.clase][fila.split].add(fila.record_id)
    return {
        "clips": clips,
        "sujetos": {c: {s: len(ids) for s, ids in lados.items()} for c, lados in sujetos.items()},
    }


# --- señal -----------------------------------------------------------------


def hann_periodica(n: int) -> np.ndarray:
    """Hann periódica: 0,5 - 0,5 cos(2π k / n). La misma fórmula está en el JS."""
    k = np.arange(n, dtype=np.float64)
    return 0.5 - 0.5 * np.cos(2.0 * math.pi * k / n)


def hz_a_mel(hz: np.ndarray | float) -> np.ndarray:
    return 2595.0 * np.log10(1.0 + np.asarray(hz, dtype=np.float64) / 700.0)


def mel_a_hz(mel: np.ndarray | float) -> np.ndarray:
    return 700.0 * (np.power(10.0, np.asarray(mel, dtype=np.float64) / 2595.0) - 1.0)


def matriz_mel(
    sr: int = SR,
    n_fft: int = FFT_LENGTH,
    n_mels: int = N_MELS,
    fmin: float = FMIN,
    fmax: float = FMAX,
) -> np.ndarray:
    """Filtros triangulares HTK, forma (n_mels, n_bins). Sin normalizar el área."""
    n_bins = n_fft // 2 + 1
    puntos_mel = np.linspace(hz_a_mel(fmin), hz_a_mel(fmax), n_mels + 2)
    puntos_hz = mel_a_hz(puntos_mel)
    bins = np.floor((n_fft + 1) * puntos_hz / sr).astype(np.int64)
    banco = np.zeros((n_mels, n_bins), dtype=np.float64)
    for i in range(n_mels):
        izquierda, centro, derecha = int(bins[i]), int(bins[i + 1]), int(bins[i + 2])
        if centro <= izquierda:
            centro = izquierda + 1
        if derecha <= centro:
            derecha = centro + 1
        for j in range(izquierda, centro):
            if 0 <= j < n_bins:
                banco[i, j] = (j - izquierda) / (centro - izquierda)
        for j in range(centro, derecha):
            if 0 <= j < n_bins:
                banco[i, j] = (derecha - j) / (derecha - centro)
    return banco


_MEL: np.ndarray | None = None
_HANN: np.ndarray | None = None


def mel_cache() -> np.ndarray:
    global _MEL
    if _MEL is None:
        _MEL = matriz_mel()
    return _MEL


def magnitud_stft(onda: np.ndarray) -> np.ndarray:
    """Magnitud de la STFT, forma (n_frames, n_bins), float32."""
    global _HANN
    if onda.shape != (N_SAMPLES,):
        raise ValueError(f"se esperaban {N_SAMPLES} muestras y llegaron {onda.shape}")
    if _HANN is None:
        _HANN = hann_periodica(FRAME_LENGTH)
    x = np.asarray(onda, dtype=np.float64)
    inicios = np.arange(N_FRAMES)[:, None] * FRAME_STEP
    idx = inicios + np.arange(FRAME_LENGTH)[None, :]
    cuadros = x[idx] * _HANN
    return np.abs(np.fft.rfft(cuadros, n=FFT_LENGTH, axis=1)).astype(np.float32)


def log_mel(onda: np.ndarray) -> np.ndarray:
    """Log-mel con z-score del propio recorte. Forma (n_mels, n_frames), float32.

    El z-score por recorte absorbe la ganancia del archivo o del estetoscopio.
    numpy.std usa ddof=0; el JS tiene que hacer lo mismo.
    """
    mag = magnitud_stft(onda).astype(np.float64)  # (tiempo, bins)
    mel = mag @ mel_cache().T  # (tiempo, mels)
    logm = np.log(mel + LOG_EPS).T  # (mels, tiempo)
    media = float(logm.mean())
    desv = float(logm.std())
    if desv < 1e-8:
        desv = 1.0
    return ((logm - media) / desv).astype(np.float32)


def remuestrear_lineal(onda: np.ndarray, sr_desde: int, sr_hasta: int = SR) -> np.ndarray:
    """Interpolación lineal. Misma regla que `remuestrearLineal` en el navegador."""
    onda = np.asarray(onda, dtype=np.float64)
    if sr_desde == sr_hasta:
        return onda.astype(np.float32)
    if len(onda) < 2 or sr_desde <= 0 or sr_hasta <= 0:
        return np.zeros(0, dtype=np.float32)
    n_out = int(round(len(onda) * sr_hasta / float(sr_desde)))
    if n_out < 2:
        return np.zeros(n_out, dtype=np.float32)
    posicion = np.linspace(0.0, len(onda) - 1, n_out)
    i0 = np.floor(posicion).astype(np.int64)
    i1 = np.minimum(i0 + 1, len(onda) - 1)
    frac = posicion - i0
    return ((1.0 - frac) * onda[i0] + frac * onda[i1]).astype(np.float32)


def leer_wav_mono(ruta: str) -> tuple[np.ndarray, int]:
    """Lee un WAV PCM de 16 bits. Si hay más de un canal, promedia."""
    with wave.open(ruta, "rb") as w:
        canales = w.getnchannels()
        sr = w.getframerate()
        ancho = w.getsampwidth()
        n = w.getnframes()
        crudo = w.readframes(n)
    if ancho != 2:
        raise ValueError(f"{ruta}: se esperaba PCM de 16 bits y el ancho es {ancho}")
    muestras = np.frombuffer(crudo, dtype="<i2").astype(np.float32)
    if canales > 1:
        muestras = muestras.reshape(-1, canales).mean(axis=1)
    # 32768 deja el rango en (-1, 1].
    return muestras / 32768.0, sr


def escribir_wav(ruta: str, onda: np.ndarray, sr: int = SR) -> None:
    onda = np.asarray(onda, dtype=np.float32)
    enteros = np.clip(np.round(onda * 32767.0), -32768, 32767).astype("<i2")
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(enteros.tobytes())


def recortar_a_4k(onda: np.ndarray, sr: int) -> np.ndarray:
    return remuestrear_lineal(onda, sr, SR)


def metricas_binarias(y_real: np.ndarray, y_pred: np.ndarray, positivo: int = 1) -> dict:
    """Exactitud, sensibilidad y especificidad del clase positiva, más la matriz.

    La matriz es [[tn, fp], [fn, tp]] con el orden [negativo, positivo].
    Si un denominador es cero, el valor queda en null: no se inventa un 0 ni un 1.
    """
    y_real = np.asarray(y_real).astype(int)
    y_pred = np.asarray(y_pred).astype(int)
    tp = int(np.sum((y_real == positivo) & (y_pred == positivo)))
    tn = int(np.sum((y_real != positivo) & (y_pred != positivo)))
    fp = int(np.sum((y_real != positivo) & (y_pred == positivo)))
    fn = int(np.sum((y_real == positivo) & (y_pred != positivo)))
    n = tp + tn + fp + fn

    def razon(num: int, den: int):
        if den == 0:
            return None
        return num / den

    return {
        "n": n,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "matriz": [[tn, fp], [fn, tp]],
        "exactitud": razon(tp + tn, n),
        "sensibilidad": razon(tp, tp + fn),
        "especificidad": razon(tn, tn + fp),
    }


def comprobar_sin_fuga(filas: list[FilaManifiesto]) -> None:
    """Ningún sujeto (record_id) y ningún grupo ligado aparecen en train y en test."""
    por_sujeto: dict[str, set[str]] = {}
    por_grupo: dict[str, set[str]] = {}
    for fila in filas:
        por_sujeto.setdefault(fila.record_id, set()).add(fila.split)
        if fila.grupo:
            por_grupo.setdefault(fila.grupo, set()).add(fila.split)
    cruce_s = [s for s, splits in por_sujeto.items() if len(splits) > 1]
    cruce_g = [g for g, splits in por_grupo.items() if len(splits) > 1]
    if cruce_s or cruce_g:
        raise RuntimeError(f"fuga de sujetos={cruce_s[:5]} grupos={cruce_g[:5]}")


def main() -> None:
    """Autocomprobación corta, sin datos reales."""
    assert MURMUR_A_CLASE["Absent"] == "normal"
    assert MURMUR_A_CLASE["Present"] == "soplo"
    assert MURMUR_A_CLASE["Unknown"] == "incierto"
    assert "chagas" not in MURMUR_A_CLASE.values()
    assert foco_de_nombre("2530_MV.wav") == "MV"
    assert foco_de_nombre("50782_MV_2.wav") == "MV"
    assert N_FRAMES == 155
    assert len(indices_ventanas(N_SAMPLES)) == 1
    assert len(indices_ventanas(N_SAMPLES * 4 + 10)) == 4
    assert indices_ventanas(N_SAMPLES - 1) == []
    onda = np.zeros(N_SAMPLES, dtype=np.float32)
    onda[::50] = 0.2
    spec = log_mel(onda)
    assert spec.shape == (N_MELS, N_FRAMES), spec.shape
    print("audio_comun: autocomprobación correcta")
    print(f"  {SR} Hz, {DURATION_S} s, mel {N_MELS} x {N_FRAMES}, clases {CLASES_ENTRENADAS}")


if __name__ == "__main__":
    main()
