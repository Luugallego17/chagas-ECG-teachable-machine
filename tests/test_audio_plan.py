"""Pruebas del plan de audio con fichas sintéticas.

Los pacientes y las ondas de este archivo son sintéticos: no son CirCor
y no deben copiarse a data/audio/manifest.csv.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audio_comun import (  # noqa: E402
    N_SAMPLES,
    SR,
    ArchivoAudio,
    Paciente,
    comprobar_sin_fuga,
    escribir_wav,
    foco_de_nombre,
    leer_wav_mono,
    log_mel,
    planificar,
)


def paciente(rid, murmur, focos="", adicional=None, audible=""):
    return Paciente(
        record_id=rid,
        murmur=murmur,
        focos_soplo=frozenset(f for f in focos.split("+") if f),
        additional_id=adicional,
        campana="CC2015",
        edad="Child",
        foco_mas_audible=audible,
    )


def wav(rid, foco, n=N_SAMPLES * 2, sr=SR):
    return ArchivoAudio(record_id=rid, nombre=f"{rid}_{foco}.wav", n_muestras=n, sr=sr)


class PlanSintetico(unittest.TestCase):
    def test_clases_y_foco_sin_soplo(self):
        pacientes = [
            paciente("1", "Absent"),
            paciente("2", "Present", focos="MV+TV", audible="MV"),
            paciente("3", "Unknown"),
        ]
        archivos = [
            wav("1", "AV"),
            wav("2", "MV"),
            wav("2", "AV"),  # presente, pero el soplo no está en AV
            wav("3", "PV"),
        ]
        plan = planificar(pacientes, archivos, semilla=42)
        clases = {(f.record_id, Path(f.file).name.split("_t")[0].split("_")[-1] if False else f.notes): f.clase for f in plan.filas}
        por_archivo = {}
        for f in plan.filas:
            # processed/normal/1_AV_t0.wav
            por_archivo.setdefault(Path(f.file).name.split("_t")[0], []).append(f)
        self.assertEqual(por_archivo["1_AV"][0].clase, "normal")
        self.assertEqual(por_archivo["2_MV"][0].clase, "soplo")
        self.assertNotIn("2_AV", por_archivo)
        self.assertTrue(all(e.motivo == "foco_sin_soplo" for e in plan.excluidas if e.nombre.startswith("2_AV")))
        self.assertTrue(all(e.motivo == "murmur_unknown" for e in plan.excluidas if e.record_id == "3"))
        self.assertNotIn("chagas", {f.clase for f in plan.filas})
        self.assertTrue(all("sintetico=no" in f.notes for f in plan.filas))
        comprobar_sin_fuga(plan.filas)
        self.assertTrue(clases)

    def test_additional_id_no_se_parte_y_discordancia_se_excluye(self):
        pacientes = [
            paciente("10", "Absent", adicional="11"),
            paciente("11", "Absent", adicional="10"),
            paciente("20", "Present", focos="AV", adicional="21"),
            paciente("21", "Absent", adicional="20"),
        ]
        archivos = [wav(rid, "AV", n=N_SAMPLES * 3) for rid in ("10", "11", "20", "21")]
        plan = planificar(pacientes, archivos, semilla=1, fraccion=0.5)
        incluidos = {f.record_id for f in plan.filas}
        self.assertEqual(incluidos, {"10", "11"})
        splits = {f.record_id: f.split for f in plan.filas}
        self.assertEqual(splits["10"], splits["11"])
        self.assertTrue(all(e.motivo == "etiqueta_discordante" for e in plan.excluidas if e.record_id in {"20", "21"}))
        # Tres ventanas de 5 s, tope 4, así que 3.
        self.assertEqual(sum(1 for f in plan.filas if f.record_id == "10"), 3)

    def test_corto_y_nombre_de_foco(self):
        self.assertEqual(foco_de_nombre("50782_MV_2.wav"), "MV")
        plan = planificar(
            [paciente("9", "Absent")],
            [ArchivoAudio("9", "9_PV.wav", n_muestras=SR * 4, sr=SR)],
        )
        self.assertEqual(plan.filas, [])
        self.assertEqual(plan.excluidas[0].motivo, "duracion_menor_5s")

    def test_reparto_no_mezcla_sujetos(self):
        pacientes = [paciente(str(i), "Absent" if i % 3 else "Present", focos="MV") for i in range(1, 41)]
        archivos = [wav(str(i), "MV") for i in range(1, 41)]
        plan = planificar(pacientes, archivos, semilla=42, fraccion=0.2)
        comprobar_sin_fuga(plan.filas)
        train = {f.record_id for f in plan.filas if f.split == "train"}
        test = {f.record_id for f in plan.filas if f.split == "test"}
        self.assertFalse(train & test)
        self.assertTrue(test)
        self.assertTrue(train)
        # Hay soplo y normal en test: el corte es estratificado.
        clases_test = {f.clase for f in plan.filas if f.split == "test"}
        self.assertEqual(clases_test, {"normal", "soplo"})

    def test_wav_redondo_sintetico_y_logmel(self):
        """Onda sintética: un seno, no un fonocardiograma real."""
        seno = (0.2 * np.sin(2 * np.pi * 80 * np.arange(N_SAMPLES) / SR)).astype(np.float32)
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "sintetico_seno.wav"
            escribir_wav(str(ruta), seno)
            leido, sr = leer_wav_mono(str(ruta))
        self.assertEqual(sr, SR)
        self.assertEqual(len(leido), N_SAMPLES)
        self.assertLess(float(np.max(np.abs(leido - seno))), 1e-3)
        spec = log_mel(seno)
        self.assertEqual(spec.shape, (64, 155))
        self.assertAlmostEqual(float(spec.mean()), 0.0, places=4)


if __name__ == "__main__":
    unittest.main()
