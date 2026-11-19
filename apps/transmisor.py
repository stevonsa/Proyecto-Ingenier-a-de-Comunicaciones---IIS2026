"""Programa del transmisor (Raspberry Pi TX), seccion 10.3 del anteproyecto.

Uso basico (Enter en vez de boton):
  python apps/transmisor.py data/entrada/01_fotografica.bmp --modo rle
  python apps/transmisor.py data/entrada/01_fotografica.bmp --modo dct --q 50
Con boton, selector y LEDs reales:
  python apps/transmisor.py IMAGEN --gpio      (el selector GPIO27 decide el modo)
Repetir en bucle (una transmision por cada pulsacion):
  python apps/transmisor.py IMAGEN --gpio --bucle
Con una carpeta, cada pulsacion envia la siguiente imagen (orden alfabetico):
  python apps/transmisor.py /mnt/usb --gpio --bucle

LEDs: GPIO5 modo con perdidas, GPIO6 transmitiendo, GPIO13 fin correcto, GPIO19 error.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

from ie0527.hardware.gpio import crear_panel
from ie0527.link import ConfigEnlace, EnlaceCaido, enviar_imagen
from ie0527.sesion import preparar

LED_MODO, LED_TX, LED_FIN, LED_ERROR = range(4)


def main() -> int:
    p = argparse.ArgumentParser(description="IE0527: transmisor de imagenes por nRF24L01")
    p.add_argument("imagen", type=Path,
                   help="BMP/PGM gris 8 bits (max 320x240) o carpeta con varias")
    p.add_argument("--modo", choices=["rle", "dct"], default="rle")
    p.add_argument("--q", type=int, default=50, help="calidad DCT 1..100")
    p.add_argument("--grupo", type=int, default=1, help="numero de grupo (direccion del radio)")
    p.add_argument("--potencia", choices=["min", "low", "high", "max"], default="low",
                   help="low para pruebas en mesa, max para 30 m")
    p.add_argument("--tasa", choices=["2M", "1M", "250K"], default="2M")
    p.add_argument("--gpio", action="store_true", help="usar boton, selector y LEDs")
    p.add_argument("--bucle", action="store_true", help="transmitir en cada pulsacion")
    args = p.parse_args()

    if args.imagen.is_dir():
        imagenes = sorted(f for f in args.imagen.iterdir() if f.suffix.lower() in {".bmp", ".pgm"})
        if not imagenes:
            print("ERROR: la carpeta no tiene imagenes BMP/PGM", file=sys.stderr)
            return 1
    else:
        imagenes = [args.imagen]
    print("Imagenes:", ", ".join(f.name for f in imagenes))

    panel = crear_panel(args.gpio)
    from ie0527.hardware.radio import Nrf24Radio, direcciones
    dir_tx, dir_rx = direcciones(args.grupo)
    radio = Nrf24Radio(dir_tx, dir_rx, potencia=args.potencia, tasa=args.tasa)
    print("Radio listo. Version +:", radio.version_plus)

    codigo = 0
    sesion = random.randint(0, 255)      # luego se incrementa: dos seguidas nunca coinciden
    indice = -1
    while True:
        indice = (indice + 1) % len(imagenes)
        print(f"Siguiente: {imagenes[indice].name}. Esperando boton...")
        panel.esperar_boton()
        t_boton = time.perf_counter()
        panel.apagar_todo()
        modo = args.modo
        if (sel := panel.modo_con_perdidas()) is not None:
            modo = "dct" if sel else "rle"
        panel.led(LED_MODO, modo == "dct")
        panel.led(LED_TX, True)
        sesion = (sesion + 1) % 256
        try:
            meta, datos, t_comp = preparar(imagenes[indice], modo, args.q, sesion, args.grupo, t_boton)
            stats = enviar_imagen(radio, meta, datos, ConfigEnlace())
        except (EnlaceCaido, ValueError) as exc:
            panel.led(LED_TX, False)
            panel.parpadear(LED_ERROR)
            print("ERROR:", exc, file=sys.stderr)
            codigo = 1
        else:
            panel.led(LED_TX, False)
            panel.led(LED_FIN, True)
            codigo = 0
            resumen = {
                "imagen": imagenes[indice].name, "sesion": sesion, "modo": modo, "calidad_Q": meta.quality,
                "bytes_comprimidos": len(datos), "tramas_datos": meta.total_frames,
                "segundos_compresion": round(t_comp, 4),
                "segundos_transmision": round(stats.segundos_transmision, 4),
                "tramas_enviadas": stats.tramas_enviadas,
                "bytes_enviados_app": stats.bytes_enviados,
                "retransmisiones_app": stats.retransmisiones_app,
                "reenviadas_por_faltantes": stats.tramas_reenviadas_por_faltantes,
                "reintentos_hw": stats.reintentos_hw,
                "rondas_fin": stats.rondas_fin,
                "tasa_util_kbps": round(len(datos) * 8 / stats.segundos_transmision / 1000, 1),
            }
            print(json.dumps(resumen, indent=2, ensure_ascii=False))
        if not args.bucle:
            if args.gpio:
                time.sleep(5)             # deja ver el LED de fin o de error
            return codigo


if __name__ == "__main__":
    sys.exit(main())
