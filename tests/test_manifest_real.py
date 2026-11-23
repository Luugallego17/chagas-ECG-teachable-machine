"""Comprueba el manifiesto real de CirCor que sí se versiona.

No abre los WAV (esos no están en git). Si falta el CSV, la prueba se salta:
en un clon sin haber corrido prepare_audio.py no hay nada que auditar.
"""
from __future__ import annotations

import csv
import unittest
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MANIFIESTO = RAIZ / "data" / "audio" / "manifest.csv"
GRUPOS = RAIZ / "data" / "audio" / "grupos.csv"
COLUMNAS = ["file", "class", "source", "record_id", "split", "duration_s", "notes"]


class ManifiestoReal(unittest.TestCase):
    def setUp(self):
        if not MANIFIESTO.exists():
            self.skipTest("aún no se generó data/audio/manifest.csv")

    def test_columnas_clases_y_sin_sinteticos(self):
        with MANIFIESTO.open(newline="") as fh:
            reader = csv.DictReader(fh)
            self.assertEqual(list(reader.fieldnames), COLUMNAS)
            filas = list(reader)
        self.assertGreater(len(filas), 0)
        clases = {f["class"] for f in filas}
        self.assertTrue(clases <= {"normal", "soplo"})
        self.assertNotIn("chagas", clases)
        self.assertTrue(all(f["source"] == "circor" for f in filas))
        self.assertTrue(all(f["split"] in {"train", "test"} for f in filas))
        self.assertTrue(all(f["duration_s"] == "5.0" for f in filas))
        self.assertTrue(all("sintetico=no" in f["notes"] for f in filas))
        self.assertFalse(any("sintetico=si" in f["notes"] for f in filas))
        self.assertTrue(all(f["file"].startswith("processed/") for f in filas))

    def test_el_sujeto_no_cruza_el_split(self):
        with MANIFIESTO.open(newline="") as fh:
            filas = list(csv.DictReader(fh))
        por_sujeto = defaultdict(set)
        for f in filas:
            por_sujeto[f["record_id"]].add(f["split"])
        cruce = [s for s, splits in por_sujeto.items() if len(splits) > 1]
        self.assertEqual(cruce, [])

        if not GRUPOS.exists():
            return
        with GRUPOS.open(newline="") as fh:
            grupos = list(csv.DictReader(fh))
        por_grupo = defaultdict(set)
        for g in grupos:
            por_grupo[g["grupo"]].add(g["split"])
        self.assertEqual([g for g, splits in por_grupo.items() if len(splits) > 1], [])


if __name__ == "__main__":
    unittest.main()
