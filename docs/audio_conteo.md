# Conteo del audio preparado

Lo escribió `scripts/prepare_audio.py` a partir de CirCor 1.0.3.
No hay filas sintéticas. `incierto` no está en el manifiesto: los sujetos
`Unknown` y el resto de exclusiones están en `data/audio/excluidos.csv`.

Unidad del reparto: sujeto (y pareja de `Additional ID`). Semilla 42, 20 % test.
Cada clip dura 5,0 s, mono, 4 000 Hz. Como mucho 4 ventanas por grabación.

## Clips (ventanas de 5 s)

| Clase | Train | Test | Total |
|---|---:|---:|---:|
| `normal` | 6639 | 1598 | 8237 |
| `soplo` | 1368 | 294 | 1662 |

## Sujetos (un id de CirCor, una vez)

| Clase | Train | Test | Total |
|---|---:|---:|---:|
| `normal` | 547 | 138 | 685 |
| `soplo` | 137 | 33 | 170 |

## Exclusiones

Un mismo sujeto puede aportar varias grabaciones. «Grabaciones» cuenta WAV;
«sujetos» cuenta ids distintos con ese motivo (si un id tiene dos motivos, suma en los dos).

| Motivo | Grabaciones | Sujetos |
|---|---:|---:|
| `etiqueta_discordante` | 91 | 30 |
| `foco_sin_soplo` | 103 | 60 |
| `murmur_unknown` | 130 | 57 |

## Cuadre con training_data.csv

El CSV público tiene 942 sujetos: 695 Absent, 179 Present y 68 Unknown.
Un sujeto Unknown ligado a otra ficha con otra etiqueta cuenta solo en
`etiqueta_discordante`. Los sujetos con un foco excluido (`foco_sin_soplo`)
siguen en el manifiesto por los focos donde sí se anotó el soplo.


Motivos:

- `murmur_unknown`: el anotador no decidió. No se entrena como `incierto`.
- `etiqueta_discordante`: la misma persona, en las dos campañas, no tiene el mismo `Murmur`.
- `foco_sin_soplo`: el sujeto tiene soplo, pero no en ese foco.
- `duracion_menor_5s`: no cabe una ventana de 5 s.

Ningún sujeto del manifiesto está a la vez en train y en test.
La comprobación también cubre el id de grupo (Additional ID).
