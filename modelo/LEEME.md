# Modelo entrenado en Teachable Machine

Exportación en formato **TensorFlow.js** del clasificador de seis clases:

| Archivo         | Contenido                                   |
|-----------------|---------------------------------------------|
| `model.json`    | Arquitectura (MobileNetV2 + 2 capas densas) |
| `weights.bin`   | Pesos (≈ 2,06 MiB)                          |
| `metadata.json` | Etiquetas, tamaño de entrada (224 px) y versión (2.4.18) |

Etiquetas: `ECG NORMAL`, `BRD`, `HBAI`, `BRD + HBAI`, `Bloqueo AV`, `Extrasistole ventricular`.

Se entrenó con **imágenes sintéticas** (300 por clase) generadas con
`scripts/generar_dataset_demo.py`. Es un modelo de demostración educativa, **no clínico**.

Uso: `app/asistente.html` ya lo lleva incorporado; `app/index.html` permite cargar estos tres
archivos desde el navegador.
