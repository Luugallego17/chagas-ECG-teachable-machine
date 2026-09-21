# Chagas ECG · Teachable Machine

Proyecto para **identificar patologías cardíacas asociadas a la enfermedad de Chagas** a
partir de electrocardiogramas (ECG), usando [Google Teachable Machine](https://teachablemachine.withgoogle.com/)
como clasificador de imágenes.

La enfermedad de Chagas (infección por *Trypanosoma cruzi*) produce una miocardiopatía cuyo
sello electrocardiográfico son ciertas alteraciones de la conducción y del ritmo. La idea del
proyecto es reunir ECG etiquetados, convertir cada trazado en una **imagen**, y entrenar un
modelo de clasificación de imágenes en Teachable Machine.

> ⚠️ **Aviso médico.** Este proyecto es educativo / de investigación. No es un dispositivo
> médico y no debe usarse para diagnóstico clínico.

---

## ¿Por qué imágenes?

Teachable Machine (modo *Image Project*) clasifica **imágenes**, no señales crudas. Por eso el
flujo de trabajo es:

```
Señal ECG (WFDB/CSV)  ──►  Imagen del trazado (PNG)  ──►  Teachable Machine  ──►  modelo
```

Cada clase del modelo se corresponde con una carpeta dentro de `data/images/`.

## Clases (patologías chagásicas típicas en ECG)

| Carpeta                 | Clase                                             | Relevancia en Chagas |
|-------------------------|---------------------------------------------------|----------------------|
| `data/images/normal`    | ECG normal                                        | Control negativo |
| `data/images/rbbb`      | Bloqueo completo de rama derecha (BRD / RBBB)     | Hallazgo más frecuente |
| `data/images/lafb`      | Hemibloqueo anterior izquierdo (HBAI / LAFB)      | Muy frecuente |
| `data/images/rbbb_lafb` | BRD + HBAI (patrón chagásico "clásico")           | Alta especificidad para Chagas |
| `data/images/av_block`  | Bloqueo aurículo-ventricular (BAV)                | Marcador de progresión |
| `data/images/pvc`       | Extrasístoles / arritmia ventricular              | Riesgo de muerte súbita |

Puedes añadir o quitar clases creando/eliminando subcarpetas en `data/images/`.

---

## Datasets

El catálogo completo de datasets públicos, con enlaces, licencias y notas, está en
[`docs/datasets.md`](docs/datasets.md). Los principales:

- **SaMi-Trop** — cohorte brasileña de pacientes con Chagas (el dataset de referencia).
- **CODE-15%** — 345.779 ECG de Brasil con etiquetas de anomalías de conducción.
- **PTB-XL** — 21.837 ECG clínicos con diagnósticos SCP-ECG (control / comparación).
- **PhysioNet Challenge 2025** — reto oficial de *detección de Chagas por ECG*.

## Estructura del repositorio

```
.
├── README.md
├── docs/
│   └── datasets.md          # catálogo de datasets con enlaces y licencias
├── scripts/
│   ├── download_data.py     # descarga los datasets desde Zenodo / PhysioNet
│   ├── wfdb_to_images.py    # convierte señales ECG en imágenes PNG por clase
│   ├── scp_class_map.py     # mapeo etiquetas (PTB-XL SCP / CODE-15%) -> clases
│   ├── plan_balanced_set.py # distribución de clases + manifiesto balanceado
│   └── synthesize_ecg.py    # ECG sintéticos por clase (validación del pipeline, sin datos)
├── samples/                 # SVGs sintéticos de ejemplo, uno por clase
├── notebooks/
│   └── 01_explorar_datos.ipynb  # flujo explorar -> balancear -> renderizar
├── data/
│   ├── raw/                 # datasets descargados (ignorado por git)
│   └── images/              # imágenes listas para Teachable Machine, una carpeta por clase
├── notebooks/
├── requirements.txt
└── .gitignore
```

## Puesta en marcha

```bash
# 1. Dependencias
pip install -r requirements.txt

# 2. Descargar datasets (ver docs/datasets.md para credenciales/PhysioNet)
python scripts/download_data.py --dataset samitrop --dest data/raw

# 3. Ver distribución de clases y generar un manifiesto balanceado
python scripts/plan_balanced_set.py \
    --labels data/raw/ptbxl/ptbxl_database.csv \
    --id-col filename_hr --label-col scp_codes \
    --out data/manifest.csv --per-class 300

# 4. Convertir a imágenes por clase (solo los registros del manifiesto balanceado)
python scripts/wfdb_to_images.py --input data/raw/ptbxl \
    --manifest data/manifest.csv --out data/images

# 5. Subir data/images/ a https://teachablemachine.withgoogle.com/ (Image Project)
#    y entrenar arrastrando cada carpeta como una clase.
#
# Alternativa guiada: notebooks/01_explorar_datos.ipynb hace los pasos 3-4 con gráficas.
```

Consulta [`docs/datasets.md`](docs/datasets.md) antes de descargar: SaMi-Trop y la mayoría de
datos de PhysioNet requieren registro y aceptar los términos de uso.

### Validar el pipeline sin descargar datos

Antes de tocar datos reales puedes comprobar la taxonomía y el render con ECG **sintéticos**
(solo librería estándar, no instala nada):

```bash
python scripts/synthesize_ecg.py --out samples
```

Genera un trazado ilustrativo por clase en `samples/` (ver `samples/todas_las_clases.svg`).
Son solo para validación visual — **no deben usarse para entrenar**.

El mapeo de etiquetas de cada dataset a las clases del proyecto vive en
[`scripts/scp_class_map.py`](scripts/scp_class_map.py) (detalles de PTB-XL en
[`docs/ptbxl_scp_mapping.md`](docs/ptbxl_scp_mapping.md)); trae autocomprobación:

```bash
python scripts/scp_class_map.py
```
