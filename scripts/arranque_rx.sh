#!/bin/bash
# Arranque del receptor en modo autonomo (lo ejecuta el servicio ie0527-rx).
DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec "$HOME/venv/bin/python" "$DIR/apps/receptor.py" --referencias "$DIR/data/entrada" \
     --salida "$DIR/data/salida" --gpio --mostrar --potencia "${POTENCIA:-max}"
