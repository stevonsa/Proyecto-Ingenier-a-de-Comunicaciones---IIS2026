"""Programa del receptor (Raspberry Pi RX), seccion 10.4 del anteproyecto.

Escucha permanente: no necesita saber cuando empieza la transmision.
  python apps/receptor.py --referencias data/entrada
  python apps/receptor.py --referencias data/entrada --gpio --mostrar
Por cada imagen: guarda data/salida/sesionNNN_modo.pgm, agrega una fila a
data/salida/metricas.csv e imprime las metricas.

LEDs: GPIO5 en espera, GPIO6 recibiendo, GPIO13 fin correcto, GPIO19 error.
"""
import argparse
import json
import sys
from pathlib import Path

from ie0527.evaluacion import cargar_referencias, decodificar, guardar_csv, metricas
from ie0527.hardware.gpio import crear_panel
from ie0527.image_io import save_image
from ie0527.link import ConfigEnlace, Receptor, TransferenciaAbortada

LED_ESPERA, LED_RX, LED_FIN, LED_ERROR = range(4)


# Inicializa radio, referencias e indicadores; recibe, decodifica, guarda y muestra cada
# imagen.
def main() -> int:
    p = argparse.ArgumentParser(description="IE0527: receptor de imagenes por nRF24L01")
    p.add_argument("--grupo", type=int, default=1)
    p.add_argument("--potencia", choices=["min", "low", "high", "max"], default="low")
    p.add_argument("--tasa", choices=["2M", "1M", "250K"], default="2M")
    p.add_argument("--referencias", type=Path, default=None,
                   help="carpeta con las imagenes originales (para PSNR y BER)")
    p.add_argument("--salida", type=Path, default=Path("data/salida"))
    p.add_argument("--gpio", action="store_true", help="usar LEDs")
    p.add_argument("--mostrar", action="store_true", help="mostrar en el monitor HDMI (framebuffer)")
    p.add_argument("--una", action="store_true", help="terminar despues de una imagen")
    args = p.parse_args()

    from ie0527.hardware.radio import Nrf24Radio, direcciones
    # Las direcciones se invierten respecto al transmisor.
    dir_tx, dir_rx = direcciones(args.grupo)
    radio = Nrf24Radio(dir_rx, dir_tx, potencia=args.potencia, tasa=args.tasa)
    print("Radio listo. Version +:", radio.version_plus)

    panel = crear_panel(args.gpio, con_boton=False)
    referencias = cargar_referencias(args.referencias)
    print(f"Referencias cargadas: {len(referencias)}")
    pantalla = None
    # Un fallo al abrir el monitor no impide seguir recibiendo y guardando imágenes.
    if args.mostrar:
        try:
            from ie0527.pantalla import Pantalla
            pantalla = Pantalla()
        except Exception as exc:
            print(f"Aviso: no se pudo abrir la pantalla ({exc}); se sigue sin ella")

    # Actualiza LEDs, consola y pantalla cuando el enlace acepta un nuevo INICIO.
    def al_iniciar(meta):
        panel.apagar_todo()               # borra el estado de la imagen anterior
        panel.led(LED_RX, True)
        print(f"INICIO sesion {meta.session}: {meta.mode} Q={meta.quality} "
              f"{meta.width}x{meta.height}, {meta.total_frames} tramas")
        if pantalla:
            pantalla.mensaje("Recibiendo...")

    receptor = Receptor(radio, ConfigEnlace(), al_iniciar=al_iniciar)
    while True:
        panel.led(LED_ESPERA, True)       # FIN o ERROR siguen encendidos hasta el proximo INICIO
        print("Esperando transmision...")
        try:
            # El enlace verifica el flujo antes de que la aplicación lo descomprima.
            res = receptor.recibir()
            imagen, t_desc = decodificar(res)
        except (TransferenciaAbortada, ValueError) as exc:
            panel.led(LED_RX, False)
            panel.parpadear(LED_ERROR)
            print("ERROR:", exc, file=sys.stderr)
            if pantalla:
                pantalla.mensaje(f"Error: {exc}")
            continue
        panel.led(LED_RX, False)
        panel.led(LED_FIN, True)
        datos = metricas(res, imagen, t_desc, referencias)
        # El nombre de salida se construye con sesión y modo, no con el nombre original.
        archivo = args.salida / f"sesion{res.meta.session:03d}_{res.meta.mode}.pgm"
        save_image(imagen, archivo)
        guardar_csv(args.salida / "metricas.csv", datos)
        print(json.dumps(datos, indent=2, ensure_ascii=False, default=str))
        print("Imagen guardada en", archivo)
        if pantalla:
            pantalla.mostrar(imagen, datos)
        if args.una:
            return 0


if __name__ == "__main__":
    sys.exit(main())
