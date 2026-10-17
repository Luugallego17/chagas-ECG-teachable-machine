# Chagas ECG · Teachable Machine

Clasificador de **patrones electrocardiográficos asociados a la enfermedad de Chagas**, hecho con
[Google Teachable Machine](https://teachablemachine.withgoogle.com/) y una interfaz web que
funciona por completo en el navegador.

Proyecto de **Luna Saleth Gallego Martínez** · Ingeniería en Inteligencia Artificial ·
Universidad Católica Boliviana «San Pablo».

La enfermedad de Chagas (infección por *Trypanosoma cruzi*) produce una miocardiopatía cuyo
sello en el electrocardiograma son ciertas alteraciones de la conducción y del ritmo. Bolivia
tiene la mayor prevalencia mundial, y en las zonas rurales faltan especialistas que lean el ECG.
El proyecto convierte cada trazado en una **imagen** y entrena un clasificador de seis clases.

> ⚠️ **Aviso médico.** Proyecto educativo y de investigación. No es un dispositivo médico y no
> debe usarse para diagnosticar a pacientes.

---

## Probarlo en un minuto

Abre **`app/asistente.html`** con doble clic (el modelo ya viene incorporado en el archivo).
Arrastra la imagen de un ECG y verás el patrón estimado y la confianza de cada clase. En
`app/presentacion.html` está la presentación del proyecto (navega con ← →; `P` reproduce solo,
`F` pantalla completa). Para que el botón «Abrir el asistente» de la presentación funcione,
deja ambos archivos en la misma carpeta.

## Qué se usó realmente (transparencia)

- **Modelo incluido:** seis clases, entrenado en Teachable Machine con **1.800 imágenes
  sintéticas** (300 por clase) generadas con `scripts/generar_dataset_demo.py`. Es un modelo de
  **demostración**: reconoce ese tipo de trazados y **no está validado con ECG reales**.
- **Imágenes de prueba:** 120 imágenes nuevas (20 por clase), con semillas distintas a las del
  entrenamiento y sin coincidencia con ellas (verificado por huella SHA-256). Se regeneran con:
  `python scripts/generar_dataset_demo.py --n 0 --test 20 --semilla-base 700000 --out pruebas_nuevas`
- **Fuentes de datos previstas para el flujo real:** SaMi-Trop, CODE-15 % y PTB-XL (bajo sus
  licencias) y electrocardiogramas facilitados por la **Caja CORDES (sede Cochabamba)**,
  des-identificados. Los datos de pacientes **no se incluyen** en este repositorio.
- No se calcularon métricas de desempeño (exactitud, sensibilidad, especificidad).

## Las seis clases

| Clase                    | Etiqueta del modelo         | Carpeta del dataset demo   | Carpeta `data/images/` |
|--------------------------|-----------------------------|----------------------------|------------------------|
| ECG normal               | `ECG NORMAL`                | `normal`                   | `normal`               |
| Bloqueo de rama derecha  | `BRD`                       | `brd`                      | `rbbb`                 |
| Hemibloqueo ant. izq.    | `HBAI`                      | `hbai`                     | `lafb`                 |
| BRD + HBAI (clásico)     | `BRD + HBAI`                | `brd_hbai`                 | `rbbb_lafb`            |
| Bloqueo AV               | `Bloqueo AV`                | `bloqueo_av`               | `av_block`             |
| Extrasístole ventricular | `Extrasistole ventricular`  | `extrasistole_ventricular` | `pvc`                  |

## Estructura del repositorio

```
.
├── app/
│   ├── asistente.html        # asistente clínico con el modelo YA incorporado (un solo archivo)
│   ├── index.html            # versión genérica: carga un modelo exportado de Teachable Machine
│   └── presentacion.html     # presentación interactiva del proyecto
├── modelo/                   # modelo exportado (TensorFlow.js): model.json, weights.bin, metadata.json
├── informe/                  # artículo científico (formato Revista 3i): .docx y .pdf imprimible
├── scripts/
│   ├── generar_dataset_demo.py  # imágenes sintéticas por clase (multiclase o binario)
│   ├── synthesize_ecg.py     # trazados sintéticos en SVG (validación del flujo)
│   ├── download_data.py      # descarga datasets desde Zenodo / indicaciones de PhysioNet
│   ├── wfdb_to_images.py     # señales ECG (WFDB / HDF5) -> imágenes PNG por clase
│   ├── scp_class_map.py      # mapeo de etiquetas (PTB-XL SCP / CODE-15 %) -> clases
│   ├── plan_balanced_set.py  # distribución de clases + manifiesto balanceado
│   └── deidentify_images.py  # des-identifica fotos de ECG (quita metadatos y tapa datos)
├── docs/                     # catálogo de datasets y mapeo de etiquetas PTB-XL
├── notebooks/01_explorar_datos.ipynb  # explorar -> balancear -> renderizar
├── samples/                  # SVGs de ejemplo, uno por clase
├── data/                     # datos locales (ignorados por git)
├── requirements.txt
└── .gitignore
```

## Flujo con datos reales

```bash
pip install -r requirements.txt

# 1. Descargar datasets (revisa acceso y licencia en docs/datasets.md)
python scripts/download_data.py --dataset code15 --dest data/raw

# 2. Ver la distribución de clases y generar un manifiesto balanceado
python scripts/plan_balanced_set.py --labels data/raw/ptbxl/ptbxl_database.csv \
    --id-col filename_hr --label-col scp_codes --out data/manifest.csv --per-class 300

# 3. Convertir a imágenes por clase (solo los registros del manifiesto)
python scripts/wfdb_to_images.py --input data/raw/ptbxl --manifest data/manifest.csv --out data/images

# 4. Subir cada carpeta como una clase en Teachable Machine, entrenar y exportar (TensorFlow.js)
```

Si usas fotos de ECG de pacientes, **des-identifícalas primero** con
`scripts/deidentify_images.py` (modo `--grid` para ubicar las zonas a tapar) y no las subas al
repositorio: las carpetas `fotos/`, `fotos_anon/`, `previews/`, `anon/` están en `.gitignore`.

## Dataset de demostración

```bash
python scripts/generar_dataset_demo.py --modo multiclase --n 300 --out dataset_demo   # 6 clases
python scripts/generar_dataset_demo.py --modo binario   --n 300 --out dataset_demo    # chagas / no_chagas
```

Solo usa la librería estándar de Python. Las imágenes son **sintéticas** y sirven para demostrar
el sistema, no para diagnóstico.

## Verificación rápida

```bash
python -m py_compile scripts/*.py        # los scripts compilan
python scripts/scp_class_map.py          # autocomprobación del mapeo de etiquetas (7 casos)
python scripts/synthesize_ecg.py --out /tmp/samples
python scripts/generar_dataset_demo.py --n 2 --test 1 --out /tmp/demo
```

## Informe

`informe/Articulo_ECG_Chagas_Revista3i.docx` sigue la plantilla de la Revista 3i (Arial, interlineado
1,5, normas APA 7.ª edición) e incluye el resumen en español, el *abstract* en inglés y el *resumo*
en portugués. `informe/Articulo_ECG_Chagas_Revista3i.pdf` es la versión imprimible.

## Créditos

Se agradece a la **Caja CORDES (sede Cochabamba)** y a su director por facilitar los
electrocardiogramas. Los conjuntos públicos (SaMi-Trop, CODE-15 %, PTB-XL) se usan bajo sus
licencias y deben citarse según sus términos.
