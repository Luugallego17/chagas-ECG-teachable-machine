"""La onda de esta prueba es sintética (un seno). No es CirCor.

Comprueba que el preproceso del navegador coincide con scripts/audio_comun.py.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audio_comun import N_SAMPLES, SR, log_mel, matriz_mel, remuestrear_lineal  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


class PreprocesoJs(unittest.TestCase):
    def test_js_coincide_con_python(self):
        if NODE is None:
            self.skipTest("node no está instalado")
        rng = np.random.default_rng(7)
        # Señal sintética: seno de 120 Hz más un poco de ruido. No es un corazón real.
        t = np.arange(N_SAMPLES, dtype=np.float64) / SR
        onda = (0.25 * np.sin(2 * np.pi * 120 * t) + 0.01 * rng.standard_normal(N_SAMPLES)).astype(np.float32)
        corta = onda[:800].copy()
        rem = remuestrear_lineal(corta, 8000, SR)
        mel = matriz_mel().astype(np.float64).reshape(-1)
        spec = log_mel(onda).astype(np.float64).reshape(-1)
        caso = {
            "onda": onda.tolist(),
            "mel": mel.tolist(),
            "logmel": spec.tolist(),
            "ondaCorta": corta.tolist(),
            "srCorta": 8000,
            "remuestreo": rem.astype(np.float64).tolist(),
            "origen": "sintetico",
        }
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "caso_sintetico.json"
            ruta.write_text(json.dumps(caso), encoding="utf-8")
            proc = subprocess.run(
                [NODE, str(RAIZ / "tests" / "comparar_preproceso.js"), str(ruta)],
                cwd=RAIZ,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        diff = json.loads(proc.stdout)
        self.assertLess(diff["maxMel"], 1e-6)
        self.assertLess(diff["maxSpec"], 1e-4)
        self.assertLess(diff["maxRs"], 1e-5)


if __name__ == "__main__":
    unittest.main()
