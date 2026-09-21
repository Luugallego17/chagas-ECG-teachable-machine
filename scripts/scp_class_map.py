"""Mapeo de etiquetas de los datasets a las clases del proyecto (fuente única de verdad).

Lo importan tanto `wfdb_to_images.py` como cualquier notebook, para no duplicar el mapa.

- SCP_TO_CLASS: códigos SCP-ECG de PTB-XL  -> clase del proyecto.
- CODE15_TO_CLASS: etiquetas del dataset CODE-15%  -> clase del proyecto.
- map_labels(raw): dada una cadena de etiquetas cruda (p. ej. el campo scp_codes de
  PTB-XL, que es un dict serializado como texto), devuelve la lista de clases del proyecto.

El patrón chagásico clásico (rbbb + lafb simultáneos) se colapsa en la clase `rbbb_lafb`.
"""
from __future__ import annotations

import re

# --- PTB-XL: códigos SCP-ECG relevantes -----------------------------------------------
# Referencia: scp_statements.csv del dataset PTB-XL (physionet.org/content/ptb-xl).
SCP_TO_CLASS: dict[str, str] = {
    # Normal
    "NORM": "normal",
    # Bloqueo de rama derecha
    "CRBBB": "rbbb",   # completo
    "IRBBB": "rbbb",   # incompleto
    # Hemibloqueo anterior izquierdo (fascicular)
    "LAFB": "lafb",
    # Bloqueos AV
    "1AVB": "av_block",
    "2AVB": "av_block",
    "3AVB": "av_block",
    # Extrasístoles / arritmia ventricular
    "PVC": "pvc",
}

# --- CODE-15%: columnas de anomalía (exams.csv, valores booleanos por columna) ---------
# Referencia: Ribeiro et al., dataset CODE-15% (zenodo.org/record/4916206).
CODE15_TO_CLASS: dict[str, str] = {
    "RBBB": "rbbb",
    "1dAVb": "av_block",   # bloqueo AV de 1er grado
    # CODE-15% no distingue LAFB ni PVC como columnas propias.
    # 'normal' se deriva cuando todas las columnas de anomalía son 0 (ver map_labels).
}

# Todas las claves conocidas, ordenadas de más larga a más corta para casar tokens de forma
# determinista y evitar solapamientos accidentales.
_ALL_KEYS = sorted(set(SCP_TO_CLASS) | set(CODE15_TO_CLASS), key=len, reverse=True)
_KEY_TO_CLASS = {**CODE15_TO_CLASS, **SCP_TO_CLASS}  # SCP tiene prioridad si hay choque


def map_labels(raw: str, *, default_normal: bool = True) -> list[str]:
    """Convierte una cadena de etiquetas cruda en clases del proyecto.

    Casa cada código conocido como *token* completo (delimitado por caracteres no
    alfanuméricos), de modo que 'CRBBB' no dispara la clave 'RBBB' por accidente.
    Si aparecen a la vez 'rbbb' y 'lafb', se colapsa en el patrón chagásico 'rbbb_lafb'.
    """
    text = str(raw)
    found: set[str] = set()
    for key in _ALL_KEYS:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(key)}(?![A-Za-z0-9])", text):
            found.add(_KEY_TO_CLASS[key])
    if "rbbb" in found and "lafb" in found:
        found.discard("rbbb")
        found.discard("lafb")
        found.add("rbbb_lafb")
    if not found and default_normal:
        return ["normal"]
    return sorted(found)


if __name__ == "__main__":  # pequeña autocomprobación
    casos = {
        "{'NORM': 100.0, 'SR': 0.0}": ["normal"],
        "{'CRBBB': 100.0}": ["rbbb"],
        "{'IRBBB': 80.0, 'LAFB': 50.0}": ["rbbb_lafb"],
        "{'3AVB': 100.0}": ["av_block"],
        "{'PVC': 100.0}": ["pvc"],
        "{'LAFB': 100.0}": ["lafb"],
        "": ["normal"],
    }
    ok = True
    for raw, esperado in casos.items():
        got = map_labels(raw)
        flag = "OK " if got == esperado else "FALLA"
        ok &= got == esperado
        print(f"[{flag}] {raw!r:40s} -> {got}")
    raise SystemExit(0 if ok else 1)
