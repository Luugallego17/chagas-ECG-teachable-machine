# Mapeo de códigos SCP-ECG (PTB-XL) → clases del proyecto

PTB-XL etiqueta cada ECG con **códigos SCP-ECG** en la columna `scp_codes` de
`ptbxl_database.csv`. Ese campo es un diccionario serializado como texto, con la forma:

```python
{'NORM': 100.0, 'SR': 0.0}          # ECG normal, ritmo sinusal
{'IRBBB': 80.0, 'LAFB': 50.0}       # BRD incompleto + hemibloqueo anterior izq.
```

El número es la **probabilidad/confianza** (0–100) asignada por el cardiólogo. El catálogo
completo de códigos está en `scp_statements.csv` (incluido con el dataset).

La correspondencia con las clases de este proyecto está implementada como fuente única en
[`scripts/scp_class_map.py`](../scripts/scp_class_map.py) y se resume aquí:

| Clase del proyecto | Códigos SCP de PTB-XL         | Descripción |
|--------------------|-------------------------------|-------------|
| `normal`           | `NORM`                        | ECG normal |
| `rbbb`             | `CRBBB`, `IRBBB`              | Bloqueo de rama derecha (completo / incompleto) |
| `lafb`             | `LAFB`                        | Hemibloqueo anterior izquierdo |
| `rbbb_lafb`        | (`CRBBB`/`IRBBB`) **y** `LAFB` | Patrón chagásico clásico (se deriva al coincidir ambos) |
| `av_block`         | `1AVB`, `2AVB`, `3AVB`        | Bloqueo AV de 1.º / 2.º / 3.º grado |
| `pvc`              | `PVC`                         | Extrasístole ventricular |

## Reglas de asignación

1. **Casado por token completo.** El código se busca delimitado por caracteres no
   alfanuméricos, así `RBBB` no se dispara dentro de otra palabra y `CRBBB`/`IRBBB` se
   detectan como tales.
2. **Patrón chagásico (`rbbb_lafb`).** Si un mismo ECG lleva a la vez un código de BRD y
   `LAFB`, se colapsa en la clase única `rbbb_lafb` (no se cuenta dos veces).
3. **Por defecto `normal`.** Si no aparece ningún código mapeado, el registro va a `normal`.
   Para PTB-XL conviene además exigir `NORM` explícito si quieres una clase normal "limpia"
   (ver umbral abajo).

## Notas de calidad al muestrear PTB-XL

- **Umbral de confianza.** Considera quedarte solo con códigos de confianza alta
  (p. ej. ≥ 80) para reducir ruido de etiquetas dudosas.
- **Multi-etiqueta.** Un ECG puede pertenecer a varias clases; el pipeline genera una imagen
  por clase aplicable (útil para Teachable Machine, que admite el mismo trazado en más de una
  clase solo si tú decides duplicarlo — por defecto se hace).
- **Balance.** `NORM` domina en PTB-XL; `LAFB` y `PVC` son minoritarias. Submuestrea `normal`
  o sobre-muestrea las clases raras para no sesgar el modelo.
- **Derivación split.** PTB-XL trae la columna `strat_fold` (1–10): usa el fold 10 como test
  y el resto para entrenar, para resultados comparables con la literatura.

## Uso

```bash
python scripts/wfdb_to_images.py \
    --input data/raw/ptbxl --format wfdb \
    --labels data/raw/ptbxl/ptbxl_database.csv \
    --id-col filename_hr --label-col scp_codes \
    --out data/images --limit 500        # empieza con pocas para validar
```

El módulo de mapeo trae una autocomprobación:

```bash
python scripts/scp_class_map.py   # imprime casos de prueba y sale con código 0 si todo OK
```
