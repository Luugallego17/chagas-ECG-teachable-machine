# Datasets del proyecto

Todos los conjuntos de esta carpeta son **imágenes sintéticas** de trazados de ECG, generadas con
`scripts/generar_dataset_demo.py` (ondas P, QRS y T gaussianas con variación de frecuencia,
amplitud, ruido y línea base). **No contienen datos de pacientes** ni fotografías reales.

| Carpeta | Contenido | Uso |
|---|---|---|
| `multiclase_6_clases/` | 6 clases × 300 imágenes de entrenamiento + `pruebas/` (60) | **Es el conjunto con el que se entrenó el modelo de `modelo/`** (1.800 imágenes) |
| `pruebas_nuevas/` | 120 imágenes nuevas (20 por clase) con semillas distintas; `a_ciegas/` trae las mismas mezcladas y `clave_respuestas.csv` | Probar el asistente con imágenes que el modelo nunca vio |
| `binario_500_por_clase/` | `chagas` / `no_chagas`, 500 por clase + `pruebas/` | Experimento binario (no es el modelo final) |
| `binario_60_por_clase/` | `chagas` / `no_chagas`, 60 por clase + `pruebas/` | Versión pequeña del experimento binario |

## Clases del conjunto multiclase

| Carpeta | Etiqueta en Teachable Machine |
|---|---|
| `normal` | ECG NORMAL |
| `brd` | BRD (bloqueo de rama derecha) |
| `hbai` | HBAI (hemibloqueo anterior izquierdo) |
| `brd_hbai` | BRD + HBAI (bloqueo bifascicular) |
| `bloqueo_av` | Bloqueo AV |
| `extrasistole_ventricular` | Extrasistole ventricular |

En los conjuntos binarios, `chagas` mezcla los patrones BRD, HBAI, BRD+HBAI, bloqueo AV y
extrasístole, y `no_chagas` es ECG normal. Es una simplificación didáctica, no un criterio clínico.

## Reproducir

```bash
python scripts/generar_dataset_demo.py --modo multiclase --n 300 --out datasets/multiclase_6_clases
python scripts/generar_pruebas_nuevas.py      # regenera datasets/pruebas_nuevas/ (idéntico)
```

`generar_pruebas_nuevas.py` además comprueba que ninguna imagen de prueba coincide byte a byte con
una de entrenamiento (resultado: 0 coincidencias sobre 2.875 imágenes comparadas).

## Qué no se incluye (y por qué)

- **Datos públicos reales** (SaMi-Trop, CODE-15 %, PTB-XL): son muy grandes y tienen sus propias
  condiciones de uso; se descargan desde la fuente con `scripts/download_data.py` (ver `docs/datasets.md`).
- **Fotografías de ECG de la Caja CORDES (Cochabamba)**: son registros de pacientes. Aunque se
  anonimicen, no se versionan en un repositorio público (`.gitignore` las excluye).

## Aviso

Que el modelo reconozca estas imágenes demuestra que el flujo funciona, no que diagnostique ECG
reales. No se han medido sensibilidad ni especificidad clínicas.
