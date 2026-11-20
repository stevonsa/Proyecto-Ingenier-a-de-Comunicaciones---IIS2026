#!/bin/bash
# Arranque del transmisor en modo autonomo (lo ejecuta el servicio ie0527-tx).
# Usa las imagenes de la memoria USB (/mnt/usb); si no hay memoria o no tiene
# imagenes, usa las de data/entrada para que la demostracion no se detenga.
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="$HOME/venv/bin/python"
IMAGENES=/mnt/usb
if ! ls "$IMAGENES"/*.[bB][mM][pP] "$IMAGENES"/*.[pP][gG][mM] >/dev/null 2>&1; then
    echo "Sin imagenes en $IMAGENES: se usan las de data/entrada"
    IMAGENES="$DIR/data/entrada"
fi
exec "$PY" "$DIR/apps/transmisor.py" "$IMAGENES" --gpio --bucle \
     --potencia "${POTENCIA:-max}" --q "${CALIDAD_Q:-50}"
