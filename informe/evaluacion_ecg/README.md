# Evaluación del modelo de ECG (120 imágenes sintéticas)

Las cifras de la Tabla 7 y la Figura 6 del informe salen de evaluar el modelo
exportado de Teachable Machine (`modelo/model.json`) sobre las 120 imágenes
sintéticas de `datasets/pruebas_nuevas/por_clase/` (20 por clase). No son
electrocardiogramas reales.

## Resultados guardados

- Exactitud: **75 %** (90 de 120).
- `predicciones_ecg_120.csv`: una fila por imagen, con la clase real, la
  predicción y las seis probabilidades.
- `metricas_ecg_120.json`: matriz de confusión, exactitud y recuento de lecturas
  con confianza baja (probabilidad máxima menor que 0,7).
- `predicciones_raw.json`: salida cruda del modelo.
- `lista.json`: orden de las 120 imágenes usadas en la evaluación.

## Cómo comprobar las métricas guardadas

Desde la raíz del repositorio, sin dependencias extra:

```bash
python informe/evaluacion_ecg/evaluar_ecg.py
```

Para calcularlas otra vez a partir de la salida cruda:

```bash
python informe/evaluacion_ecg/evaluar_ecg.py --desde-crudo
```

## Cómo volver a correr el modelo

Hace falta un servidor HTTP en la raíz del repositorio, porque el navegador
carga TensorFlow.js, el modelo y las imágenes por rutas relativas:

```bash
python -m http.server 8765
```

Abra [http://127.0.0.1:8765/informe/evaluacion_ecg/eval.html](http://127.0.0.1:8765/informe/evaluacion_ecg/eval.html).
Al terminar, la página muestra el JSON de métricas, el CSV y la salida cruda.
Luego puede contrastarlos con `python informe/evaluacion_ecg/evaluar_ecg.py`.
