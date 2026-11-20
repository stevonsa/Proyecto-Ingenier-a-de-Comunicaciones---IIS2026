#!/bin/bash
# Modo autonomo: el programa arranca solo al encender, con WiFi y Bluetooth
# apagados, y se maneja solo con el boton, el selector y los LEDs.
#
# Uso (desde la carpeta del proyecto, con el usuario normal):
#   sudo bash scripts/instalar_servicio.sh tx      en la Raspberry transmisora
#   sudo bash scripts/instalar_servicio.sh rx      en la Raspberry receptora
# Para volver al modo de desarrollo (WiFi y SSH): sudo bash scripts/modo_desarrollo.sh
set -euo pipefail
ROL="${1:-}"
if [[ "$ROL" != "tx" && "$ROL" != "rx" ]]; then
    echo "Uso: sudo $0 tx|rx"; exit 1
fi
USUARIO="${SUDO_USER:-}"
if [[ -z "$USUARIO" || "$USUARIO" == "root" ]]; then
    echo "Ejecutar con sudo desde el usuario normal (comu o comu2)"; exit 1
fi
DIR="$(cd "$(dirname "$0")/.." && pwd)"
chmod +x "$DIR"/scripts/*.sh

if [[ "$ROL" == "tx" ]]; then
    # Memoria USB de solo lectura en /mnt/usb, montada al usarla; si no esta, no
    # bloquea el arranque (nofail) y el script usa data/entrada.
    mkdir -p /mnt/usb
    if ! grep -q " /mnt/usb " /etc/fstab; then
        echo "/dev/sda1 /mnt/usb auto ro,nofail,noatime,x-systemd.automount,x-systemd.device-timeout=5 0 0" >> /etc/fstab
        systemctl daemon-reload
    fi
else
    # Pantalla: sin apagado por inactividad y sin cursor parpadeando sobre la imagen.
    CMDLINE=/boot/firmware/cmdline.txt
    for opcion in consoleblank=0 vt.global_cursor_default=0; do
        grep -q "$opcion" "$CMDLINE" || sed -i "1 s/\$/ $opcion/" "$CMDLINE"
    done
fi

cat > "/etc/systemd/system/ie0527-$ROL.service" <<UNIT
[Unit]
Description=IE0527 $ROL de imagenes por nRF24L01 (modo autonomo)
After=local-fs.target getty@tty1.service

[Service]
User=$USUARIO
WorkingDirectory=$DIR
Environment=PYTHONUNBUFFERED=1
ExecStartPre=+/usr/sbin/rfkill block wifi
ExecStartPre=+/usr/sbin/rfkill block bluetooth
ExecStart=$DIR/scripts/arranque_$ROL.sh
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable "ie0527-$ROL.service"
echo
echo "Listo. Al reiniciar (sudo reboot) arranca solo, con WiFi y Bluetooth apagados."
echo "OJO: desde ese momento ya no hay SSH. Para volver: teclado y monitor, y"
echo "     sudo bash $DIR/scripts/modo_desarrollo.sh"
