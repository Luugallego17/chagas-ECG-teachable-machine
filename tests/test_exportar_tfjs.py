"""Exporta una CNN diminuta y comprueba que TensorFlow.js da los mismos números.

Los pesos salen de un ajuste de un paso sobre ruido sintético, no de CirCor.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

RAIZ = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
TFJS = os.environ.get("TFJS_NODE_MODULES", "/tmp/tfjs-test/node_modules/@tensorflow/tfjs")


class ExportarTfjs(unittest.TestCase):
    def test_prediccion_coincide(self):
        if NODE is None or not Path(TFJS).exists():
            self.skipTest("hace falta node y @tensorflow/tfjs")
        import tensorflow as tf

        from exportar_tfjs import exportar_tfjs

        tf.keras.utils.set_random_seed(3)
        modelo = tf.keras.Sequential(
            [
                tf.keras.layers.Input(shape=(8, 8, 1)),
                tf.keras.layers.Conv2D(2, 3, padding="same", activation="relu", name="conv_a"),
                tf.keras.layers.MaxPooling2D(2, name="pool_a"),
                tf.keras.layers.GlobalAveragePooling2D(name="gap"),
                tf.keras.layers.Dropout(0.3, name="drop"),
                tf.keras.layers.Dense(2, activation="softmax", name="salida"),
            ],
            name="prueba",
        )
        x = np.random.default_rng(1).standard_normal((4, 8, 8, 1)).astype(np.float32)
        y = np.array([0, 1, 0, 1])
        modelo.compile(optimizer="adam", loss="sparse_categorical_crossentropy")
        modelo.fit(x, y, epochs=1, verbose=0)
        entrada = x[:1]
        esperado = modelo.predict(entrada, verbose=0)[0].tolist()
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "modelo"
            exportar_tfjs(modelo, destino)
            caso = Path(tmp) / "caso.json"
            caso.write_text(
                json.dumps({"entrada": entrada.tolist(), "esperado": esperado}),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["TFJS_NODE_MODULES"] = TFJS
            proc = subprocess.run(
                [NODE, str(RAIZ / "scripts" / "verificar_modelo_tfjs.js"), str(destino), str(caso)],
                cwd=RAIZ,
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
