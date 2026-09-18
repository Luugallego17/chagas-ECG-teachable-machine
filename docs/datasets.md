# Catálogo de datasets de ECG para Chagas

Este documento reúne los conjuntos de datos públicos de ECG útiles para entrenar un
clasificador de patologías chagásicas. Para cada uno se indica: contenido, tamaño, formato,
licencia/acceso y enlace. **Verifica siempre el enlace y la licencia antes de descargar** —
los identificadores de Zenodo/PhysioNet pueden cambiar.

Leyenda de acceso:
- 🟢 **Abierto**: descarga directa.
- 🟡 **Registro**: requiere crear cuenta y aceptar términos (p. ej. PhysioNet credentialed).

---

## 1. SaMi-Trop — cohorte de Chagas (referencia)

- **Qué es:** estudio de cohorte de pacientes brasileños con enfermedad de Chagas crónica.
  Contiene ECG de 12 derivaciones con anotaciones clínicas. Es el dataset **específico de
  Chagas** por excelencia.
- **Formato:** WFDB / HDF5 + tabla de metadatos (CSV).
- **Acceso:** 🟡 Zenodo (registro para algunas versiones).
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
- **Acceso:** 🟡 PhysioNet (registro).
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
