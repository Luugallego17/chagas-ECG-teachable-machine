#!/usr/bin/env python3
"""Escribe un Sequential de Keras como LayersModel de TensorFlow.js.

`tensorflowjs` no se usa: con TensorFlow 2.19 el conversor falla al importar
(protobuf del paquete de árboles de decisión no coincide con el runtime).
Este módulo escribe el JSON que `tf.loadLayersModel` espera y los pesos en
float32, en el mismo orden que Keras (kernel y luego bias).

La comprobación numérica está en tests/test_exportar_tfjs.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

_INICIALIZADOR = {
    "class_name": "VarianceScaling",
    "config": {"scale": 1, "mode": "fan_avg", "distribution": "normal", "seed": None},
}
_CEROS = {"class_name": "Zeros", "config": {}}


def _activacion(capa) -> str:
    fn = getattr(capa, "activation", None)
    nombre = getattr(fn, "__name__", None)
    if nombre is None:
        raise TypeError(f"la capa {capa.name} no tiene activación con nombre")
    return nombre


def _config_capa(capa, forma_entrada: list[int] | None) -> dict:
    tipo = capa.__class__.__name__
    if tipo == "Conv2D":
        cfg = {
            "filters": int(capa.filters),
            "kernel_initializer": _INICIALIZADOR,
            "kernel_regularizer": None,
            "kernel_constraint": None,
            "kernel_size": [int(k) for k in capa.kernel_size],
            "strides": [int(s) for s in capa.strides],
            "padding": capa.padding,
            "data_format": "channels_last",
            "dilation_rate": [int(d) for d in capa.dilation_rate],
            "activation": _activacion(capa),
            "use_bias": bool(capa.use_bias),
            "bias_initializer": _CEROS,
            "bias_regularizer": None,
            "activity_regularizer": None,
            "bias_constraint": None,
            "name": capa.name,
            "trainable": True,
        }
    elif tipo == "MaxPooling2D":
        cfg = {
            "pool_size": [int(k) for k in capa.pool_size],
            "padding": capa.padding,
            "strides": [int(s) for s in capa.strides],
            "data_format": "channels_last",
            "name": capa.name,
            "trainable": True,
        }
    elif tipo == "GlobalAveragePooling2D":
        cfg = {
            "data_format": "channels_last",
            "name": capa.name,
            "trainable": True,
        }
    elif tipo == "Dropout":
        cfg = {
            "rate": float(capa.rate),
            "noise_shape": None,
            "seed": None,
            "name": capa.name,
            "trainable": True,
        }
    elif tipo == "Dense":
        cfg = {
            "units": int(capa.units),
            "activation": _activacion(capa),
            "use_bias": bool(capa.use_bias),
            "kernel_initializer": _INICIALIZADOR,
            "bias_initializer": _CEROS,
            "kernel_regularizer": None,
            "bias_regularizer": None,
            "activity_regularizer": None,
            "kernel_constraint": None,
            "bias_constraint": None,
            "name": capa.name,
            "trainable": True,
        }
    else:
        raise TypeError(f"capa no prevista en la exportación: {tipo}")
    if forma_entrada is not None:
        cfg["batch_input_shape"] = [None, *forma_entrada]
        cfg["dtype"] = "float32"
    return {"class_name": tipo, "config": cfg}


def exportar_tfjs(modelo, destino: str | Path) -> None:
    """Guarda model.json y weights.bin. `destino` es la carpeta modelo/audio."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    forma = [int(d) for d in modelo.input_shape[1:]]
    capas = []
    primera = True
    trozos = []
    specs = []
    for capa in modelo.layers:
        if capa.__class__.__name__ == "InputLayer":
            continue
        capas.append(_config_capa(capa, forma if primera else None))
        primera = False
        pesos = capa.get_weights()
        if not pesos:
            continue
        if len(pesos) != 2:
            raise RuntimeError(f"{capa.name} tiene {len(pesos)} tensores; se esperaban kernel y bias")
        for nombre, tensor in (("kernel", pesos[0]), ("bias", pesos[1])):
            arr = np.ascontiguousarray(tensor, dtype=np.float32)
            specs.append({"name": f"{capa.name}/{nombre}", "shape": list(arr.shape), "dtype": "float32"})
            trozos.append(arr.tobytes())

    topologia = {
        "class_name": "Sequential",
        "config": {"name": modelo.name, "layers": capas},
        "keras_version": "tfjs-layers 4.20.0",
        "backend": "tensor_flow.js",
    }
    documento = {
        "modelTopology": topologia,
        "format": "layers-model",
        "generatedBy": "scripts/exportar_tfjs.py",
        "convertedBy": "exportación directa, sin tensorflowjs_converter",
        "weightsManifest": [{"paths": ["weights.bin"], "weights": specs}],
    }
    (destino / "model.json").write_text(json.dumps(documento), encoding="utf-8")
    (destino / "weights.bin").write_bytes(b"".join(trozos))
