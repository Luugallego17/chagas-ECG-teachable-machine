# Catálogo de datasets de ECG para Chagas

Este documento reúne los conjuntos de datos públicos de ECG útiles para entrenar un
clasificador de patologías chagásicas. Para cada uno se indica: contenido, tamaño, formato,
licencia/acceso y enlace. **Verifica siempre el enlace y la licencia antes de descargar** —
los identificadores de Zenodo/PhysioNet pueden cambiar.

> **Nota de transparencia.** Estos conjuntos son las fuentes previstas para el flujo con datos
> reales (`scripts/`). El modelo incluido en `modelo/` se entrenó con imágenes **sintéticas**
> (ver `scripts/generar_dataset_demo.py`); los datos públicos y los ECG de la Caja CORDES no se
> incluyen en el repositorio.

Leyenda de acceso:
- 🟢 **Abierto**: descarga directa.
- 🟡 **Registro**: requiere crear cuenta y aceptar términos (p. ej. PhysioNet credentialed).

---

## 1. SaMi-Trop — cohorte de Chagas (referencia)

- **Qué es:** estudio de cohorte de pacientes brasileños con enfermedad de Chagas crónica.
  Contiene ECG de 12 derivaciones con anotaciones clínicas. Es el dataset **específico de
  Chagas** por excelencia.
- **Formato:** WFDB / HDF5 + tabla de metadatos (CSV).
- **Acceso:** consulta en Zenodo las condiciones y la licencia de la versión vigente.
- **Enlace:** https://zenodo.org/record/4905618  ·  DOI: `10.5281/zenodo.4905618`
- **Uso en este proyecto:** fuente principal de la clase *positiva de Chagas* y de sus
  patrones de conducción.

## 2. CODE-15% — ECG brasileños con etiquetas de conducción

- **Qué es:** subconjunto (15 %) del dataset CODE del Telehealth Network of Minas Gerais.
  **345.779** ECG de 12 derivaciones de ~233.000 pacientes, con etiquetas de 6 anomalías:
  1dAVb, RBBB, LBBB, SB (bradicardia sinusal), AF (fibrilación auricular), ST.
- **Formato:** HDF5 (señales) + `exams.csv` (etiquetas por examen).
- **Acceso:** 🟢 Zenodo.
- **Enlace:** https://zenodo.org/record/4916206  ·  DOI: `10.5281/zenodo.4916206`
- **Uso en este proyecto:** fuente principal de las clases **RBBB**, **BAV** y **normal**;
  gran volumen para balancear el entrenamiento.

## 3. PTB-XL — ECG clínicos con diagnósticos SCP

- **Qué es:** **21.837** ECG clínicos de 10 s / 12 derivaciones, de 18.885 pacientes, con
  diagnósticos codificados en SCP-ECG (incluye RBBB, LAFB, BAV, etc.).
- **Formato:** WFDB (`.dat`/`.hea`) + `ptbxl_database.csv`, `scp_statements.csv`.
- **Acceso:** 🟢 PhysioNet (acceso abierto, licencia CC BY 4.0).
- **Enlace:** https://physionet.org/content/ptb-xl/
- **Uso en este proyecto:** clase **LAFB** y comparación / control con población no chagásica.

## 4. PhysioNet Challenge 2025 — Detección de Chagas por ECG

- **Qué es:** reto *George B. Moody PhysioNet Challenge 2025* dedicado a **detectar la
  enfermedad de Chagas a partir del ECG**. Combina CODE-15%, SaMi-Trop y PTB-XL con
  etiquetas de Chagas armonizadas. Incluye código base de referencia.
- **Acceso:** 🟡 PhysioNet.
- **Enlaces:**
  - Descripción del reto: https://physionet.org/content/challenge-2025/
  - Código base oficial: https://github.com/physionetchallenges/python-example-2025
- **Uso en este proyecto:** etiquetas Chagas ↔ no-Chagas ya armonizadas; punto de partida
  metodológico recomendado.

## 5. PTB-XL+ / otros (opcional)

- **MIMIC-IV-ECG**, **Georgia 12-lead (PhysioNet 2020)**, **Chapman-Shaoxing** — grandes
  bancos de ECG de 12 derivaciones útiles para aumentar la clase *normal* y las arritmias.
  Todos en PhysioNet (🟡). Ver https://physionet.org/about/database/.

---

## Mapa: patología chagásica ↔ etiqueta en cada dataset

| Clase del proyecto | CODE-15% | PTB-XL (SCP) | SaMi-Trop |
|--------------------|----------|--------------|-----------|
| `normal`           | (sin anomalías) | `NORM` | controles |
| `rbbb`             | `RBBB`   | `CRBBB`/`IRBBB` | presente |
| `lafb`             | —        | `LAFB`       | presente |
| `rbbb_lafb`        | derivar de RBBB+LAFB | `CRBBB`+`LAFB` | patrón clásico |
| `av_block`         | `1dAVb`  | `1AVB`/`2AVB`/`3AVB` | presente |
| `pvc`              | —        | `PVC`        | presente |

> El *patrón chagásico clásico* (`rbbb_lafb`) rara vez viene como etiqueta única: se deriva
> cuando un mismo ECG está etiquetado a la vez con RBBB **y** con LAFB.

## Consideraciones éticas y de licencia

- Todos estos datos son de investigación y están **des-identificados**; respeta los términos
  de uso de cada fuente (la mayoría prohíben re-identificar pacientes).
- No subas datos de pacientes crudos a servicios de terceros. Teachable Machine solo recibe
  **imágenes de trazados** ya anonimizadas, sin metadatos personales.
- El directorio `data/` está en `.gitignore`: **no se versiona ningún dato de pacientes**.

---

## Sonidos cardíacos (fonocardiograma)

El módulo de audio **no clasifica la enfermedad de Chagas**. No existe un conjunto
público de soplos o fonocardiogramas específicos de Chagas; buscar uno y no citarlo
sería inventar una fuente. El audio estima un soplo o una anomalía **general**, en un
proyecto educativo. No es un diagnóstico.

### Fuente elegida: CirCor DigiScope v1.0.3

Ficha revisada el 23 de noviembre de 2026 en la página oficial de PhysioNet.

| Campo | Valor |
|---|---|
| Nombre | The CirCor DigiScope Phonocardiogram Dataset, versión 1.0.3 |
| Enlace | https://physionet.org/content/circor-heart-sound/1.0.3/ |
| DOI | https://doi.org/10.13026/tshs-mw03 |
| Licencia | Open Data Commons Attribution License v1.0 (ODC-By 1.0). El archivo `LICENSE.txt` del paquete empieza por «ODC Attribution License (ODC-By)». |
| Acceso | 🟢 Abierto. No hace falta cuenta credentialed de PhysioNet. |
| Tamaño (ficha) | 5.272 grabaciones de 1.568 sujetos, de 0 a 21 años (media 6,1 ± 4,3), duración 4,8–80,4 s (media 22,9 ± 7,4), más de 33,5 horas. El ZIP público pesa unos 449,5 MB (558,9 MB sin comprimir). |
| Qué se publica | El 60 % del total, como conjunto de entrenamiento del George B. Moody PhysioNet Challenge 2022. El 40 % restante (validación y prueba del reto) no está en esta versión. |
| Formato | WAV mono a 4.000 Hz, cabecera WFDB (`.hea`), segmentación S1/S2 (`.tsv`) y una ficha `.txt` por sujeto. El resumen está en `training_data.csv`. |
| Etiquetas | `Murmur`: Present, Absent o Unknown. También timing, forma, tono, grado, calidad y localización del soplo, y un `Outcome` clínico (Normal/Abnormal) que **no** es la etiqueta de soplo. |
| Reto | [George B. Moody PhysioNet Challenge 2022](https://moody-challenge.physionet.org/2022/), detección de soplo en el fonocardiograma. |

**Población.** CirCor es pediátrico (campañas de cribado en el noreste de Brasil, 2014 y 2015, participantes menores de 21 años). No equivale a la población adulta con miocardiopatía chagásica que estudia el clasificador de ECG de este repositorio. No se presenta el audio como «detector de Chagas».

**Cita que pide PhysioNet** (el proyecto y el artículo):

> Oliveira, J., Renna, F., Costa, P., Nogueira, M., Oliveira, A. C., Elola, A., Ferreira, C., Jorge, A., Bahrami Rad, A., Reyna, M., Sameni, R., Clifford, G., & Coimbra, M. (2022). *The CirCor DigiScope Phonocardiogram Dataset* (version 1.0.3). PhysioNet. https://doi.org/10.13026/tshs-mw03

> Oliveira, J. H., Renna, F., Costa, P., Nogueira, D., Oliveira, C., Ferreira, C., Jorge, A., Mattos, S., Hatem, T., Tavares, T., Elola, A., Rad, A., Sameni, R., Clifford, G. D., & Coimbra, M. T. (2021). The CirCor DigiScope Dataset: From Murmur Detection to Murmur Classification. *IEEE Journal of Biomedical and Health Informatics*. https://doi.org/10.1109/JBHI.2021.3137048

### Challenge 2016: no entra en el entrenamiento

Se revisó también la ficha del [PhysioNet/Computing in Cardiology Challenge 2016, versión 1.0.0](https://physionet.org/content/challenge-2016/1.0.0/) (23 de noviembre de 2026).

| Campo | Valor |
|---|---|
| Licencia | Open Data Commons Attribution License v1.0. Acceso abierto. |
| Contenido | El texto de la ficha describe cinco bases de entrenamiento (A–E) con 3.126 grabaciones, de 5 s a poco más de 120 s. Una nota de la misma página habla de 3.125 fonocardiogramas: se cita la cifra de la sección de datos (3.126) y no se reconcilia inventando otra. |
| Clases | `normal` / `abnormal`. Lo anormal mezcla valvulopatías y enfermedad coronaria; **no es una etiqueta de soplo**. |

**Decisión.** El entrenamiento usa **solo CirCor**. El Challenge 2016 no se descarga ni se mezcla: su clase `abnormal` no se puede traducir con honestidad a `soplo`, y juntarla con Present/Absent de CirCor borraría el significado de las clases. Sigue siendo una fuente abierta válida para otro trabajo de normal/anormal, no para este.

### Descarga

Los crudos van a `data/audio/raw/` y **no se versionan** (ni los WAV, ni el ZIP, ni los `.hea`).
PhysioNet publica este comando:

```bash
wget -r -N -c -np https://physionet.org/files/circor-heart-sound/1.0.3/
```

El ZIP único está en `https://physionet.org/content/circor-heart-sound/get-zip/1.0.3/`.
El manifiesto liviano, cuando se genere, sí puede versionarse; los WAV procesados, no.
Las clases y el recorte se fijan en los issues siguientes: no se adelanta aquí una tabla de clases.
