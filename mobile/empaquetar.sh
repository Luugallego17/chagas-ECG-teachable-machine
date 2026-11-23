#!/bin/sh
# Copia la app y los modelos al directorio que empaqueta Capacitor.
# No incluye datos crudos ni el APK.
set -e
ROOT=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
WWW="$ROOT/mobile/www"
rm -rf "$WWW"
mkdir -p "$WWW/app" "$WWW/modelo"
cp -a "$ROOT/app/." "$WWW/app/"
cp -a "$ROOT/modelo/." "$WWW/modelo/"
find "$WWW" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
cat > "$WWW/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Chagas ECG</title>
<script>location.replace("app/asistente.html");</script>
</head>
<body>
<p><a href="app/asistente.html">Abrir el asistente</a></p>
</body>
</html>
EOF
echo "Listo: $WWW"
