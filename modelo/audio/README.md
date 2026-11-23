# Modelo de fonocardiograma

CNN pequeña sobre el log-mel de 5 s. No es Teachable Machine Audio: esa herramienta
no se puede automatizar y está pensada para ventanas de cerca de un segundo de voz
o de sonidos ambientales. El fonocardiograma es más largo y de frecuencia baja.

| | |
|---|---|
| Fuente | CirCor DigiScope v1.0.3, ODC-By 1.0, https://doi.org/10.13026/tshs-mw03 |
| Clases | `normal`, `soplo`. `incierto` no se entrenó. |
| Datos | Solo el split `train` del manifiesto. Dentro de train, un 15 % de sujetos (semilla 43) eligió la época por el índice de Youden. En el ajuste, las ventanas reales de soplo se repiten hasta igualar a las normales; no hay audio sintético. El test no se usó para elegir nada. |
| Fecha | 2026-11-23 |
| Diagnóstico | No. No detecta Chagas. CirCor es pediátrico (0 a 21 años). |

## Métricas en el test, por sujeto

La etiqueta de CirCor es del sujeto. La probabilidad del sujeto es la media de
sus ventanas. Umbral 0,5. La matriz es [[tn, fp], [fn, tp]] con orden [normal, soplo].

| | |
|---|---|
| Sujetos | 171 |
| Exactitud | 0.8421 |
| Sensibilidad (soplo) | 0.8485 |
| Especificidad (soplo) | 0.8406 |
| Matriz | [[116, 22], [5, 28]] |
| Línea de base (siempre la clase mayoritaria del test, `normal`) | 0.8070 |

Por ventana, con el mismo umbral: exactitud 0.7722, sensibilidad 0.8639, especificidad 0.7553, n = 1892, matriz [[1207, 391], [40, 254]].

Estas cifras no son una validación clínica. El 40 % que CirCor retuvo para el
reto de PhysioNet 2022 no está en los datos públicos, así que esto es un corte
interno por sujeto, no el ranking del reto.

El detalle numérico está en `metricas.json`. Si un denominador fue cero, el
campo correspondiente es null.
