# Clases del fonocardiograma

Contrato entre la preparación del audio, el entrenamiento y la app.
La fuente es CirCor DigiScope v1.0.3 (ver `docs/datasets.md`). El
PhysioNet/CinC Challenge 2016 no aporta etiquetas.

Ninguna clase se llama `chagas`, `no_chagas` ni nada equivalente.
El electrocardiograma sigue con sus seis patrones; este mapa no los toca.

## Tabla

| Clase del modelo | Etiqueta en la app | Origen en CirCor (`Murmur`) | ¿Entra al entrenamiento? |
|---|---|---|---|
| `normal` | Sonido cardíaco sin soplo | `Absent` | Sí |
| `soplo` | Soplo cardíaco (anomalía general) | `Present` | Sí |
| `incierto` | Calidad insuficiente o soplo no determinable | `Unknown`, o audio que la app no puede leer | No |

`incierto` no se entrena. En el CSV público del conjunto de entrenamiento hay sujetos
`Unknown` (el anotador no pudo decidir; la ficha los liga a grabaciones que no alcanzaron
calidad). Son pocos frente a Absent y Present, y la clase no es un soplo ni un corazón
normal: meterlos en el modelo le pondría una etiqueta que el propio anotador no dio.
La app usa `incierto` solo cuando no hay una predicción honesta:

- la grabación dura menos de 5 s (el modelo siempre ve 5 s);
- el archivo no se puede decodificar;
- la señal está en silencio (RMS por debajo de 0,0001);
- el usuario niega el micrófono o detiene la toma antes de tiempo.

Si el audio sí se clasifica pero la probabilidad máxima queda por debajo del umbral
guardado en `modelo/audio/metadata.json`, la app muestra la clase y la confianza y añade
el aviso de confianza baja. No cambia el nombre de la clase a `incierto`: la clase
entrenada y la confianza se ven las dos.

`Outcome` (Normal/Abnormal en CirCor) **no** se usa. Es el juicio global del cardiólogo
pediátrico con historia, exploración y ecocardiograma, y la ficha dice que no implica
que hubiera un soplo en la auscultación digital.

## De la ficha del sujeto al archivo

La etiqueta `Murmur` es del **sujeto**, no de cada foco. Cada WAV hereda una clase con
estas reglas, sin inventar otra:

1. Sujetos ligados por `Additional ID` (la misma persona en las dos campañas) forman un
   solo grupo. Si las etiquetas `Murmur` del grupo no coinciden, **todo el grupo se
   excluye**: no se parte a la misma persona entre clases ni entre `train` y `test`.
2. `Unknown` → excluido del manifiesto de entrenamiento. Queda contado aparte
   (`docs/audio_conteo.md` cuando se preparan los datos).
3. `Absent` → cada foco del sujeto es `normal`.
4. `Present` → solo los focos listados en `Murmur locations` son `soplo`. Un foco no
   listado no es un soplo grabado ni un sujeto normal: se excluye (`foco_sin_soplo`).
   No se rellena con audio sintético.
5. Cada ventana de 5 s hereda la clase del archivo. No se reetiqueta al cortar.

Un archivo por foco (y por repetición `*_AV_1.wav` si existe). No se elige «el foco más
audible» y se tiran los demás: el foco entra o se excluye con la regla de arriba.
`Most audible location` se anota en `notes` cuando viene informado; no crea una clase.

## Qué no es este mapa

- No es un diagnóstico de Chagas, ni de una valvulopatía concreta (estenosis, insuficiencia).
- CirCor es pediátrico. No representa la miocardiopatía chagásica del adulto.
- Los audios sintéticos, si hacen falta para probar un script o la interfaz, viven en
  `tests/` y se etiquetan como sintéticos. No entran en `data/audio/manifest.csv`.
