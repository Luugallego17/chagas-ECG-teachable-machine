# Anexo. Ampliación de noviembre de 2026

Este anexo acompaña a `Articulo_ECG_Chagas_Revista3i.docx`. El PDF imprimible
no se regeneró: en este entorno no hay un procesador de textos que respete la
plantilla de la Revista 3i. El artículo original no se reescribe con cifras nuevas.

## Fonocardiograma

El módulo de sonido es independiente del electrocardiograma. La fuente es
The CirCor DigiScope Phonocardiogram Dataset, versión 1.0.3 (PhysioNet,
DOI 10.13026/tshs-mw03, licencia ODC-By 1.0). Es un conjunto pediátrico
(0 a 21 años). No existe un dataset público de soplos específicos de Chagas
y el modelo no tiene una clase `chagas`. Estima un soplo o una anomalía
cardíaca general.

Las clases entrenadas son `normal` y `soplo`. `incierto` no se entrenó: la
aplicación la muestra si el audio dura menos de 5 s, no se puede leer o está
en silencio. No se graba con el micrófono; solo se elige un archivo.

El modelo es una CNN pequeña sobre el log-mel de 5 s, exportada a
TensorFlow.js en `modelo/audio/`. No es Teachable Machine Audio. Se entrenó
con ventanas reales de CirCor. No hay audio sintético en ese entrenamiento.

En el test interno por sujeto (171 personas, umbral 0,5; semilla 42 del
manifiesto): exactitud 0,8421, sensibilidad del soplo 0,8485, especificidad
0,8406. Matriz [[116, 22], [5, 28]], con filas [normal, soplo] y columnas
[predicho normal, predicho soplo]. Decir siempre `normal` acertaría 0,807.
No es una validación clínica ni el ranking del reto de PhysioNet 2022.

## Teléfono

La interfaz está pensada para un celular. El ECG entra por «Tomar foto» o
«Galería». No hay arrastrar y soltar. El proyecto Capacitor está en `mobile/`
(`bo.ucb.chagas.ecg`). El APK de depuración lleva TensorFlow.js, Teachable
Machine y los dos modelos; no depende de la red. El único permiso de uso es
la cámara, y se pide al tomar la foto. No hay `RECORD_AUDIO`.

El modelo de ECG que se muestra sigue siendo el de 1.800 imágenes sintéticas.
No está validado con electrocardiogramas reales.

## Verificación

El detalle y las capturas están en `docs/verificacion.md`. Un wav real de
CirCor (`13918_TV.wav`, 6,6 s, soplo presente en el manifiesto) se leyó en la
interfaz como «Soplo cardíaco (anomalía general)», con 92,9 % de confianza.
Eso es una comprobación de que el archivo llega al modelo, no una métrica nueva.
