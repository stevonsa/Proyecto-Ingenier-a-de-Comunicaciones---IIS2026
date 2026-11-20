#!/bin/bash
# Vuelve al modo de desarrollo: detiene el modo autonomo y enciende WiFi y Bluetooth.
# Uso (con teclado y monitor conectados): sudo bash scripts/modo_desarrollo.sh
set -u
for rol in tx rx; do
    systemctl disable --now "ie0527-$rol.service" 2>/dev/null && echo "Servicio ie0527-$rol detenido"
done
rfkill unblock wifi
rfkill unblock bluetooth
sleep 3
echo "WiFi encendido. Conectando al hotspot guardado..."
nmcli device wifi rescan >/dev/null 2>&1; sleep 2
nmcli connection up "$(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="802-11-wireless"{print $1; exit}')" 2>/dev/null
hostname -I
