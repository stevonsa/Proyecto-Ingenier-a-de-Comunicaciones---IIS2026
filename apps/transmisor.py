"""Punto de entrada futuro para la Raspberry Pi transmisora (no funcional aun).

Orden previsto:
  Esperar boton GPIO17 y leer selector GPIO27.
  Medir instante inicial (perf_counter).
  Leer BMP/PGM desde USB y validar.
  Aplicar RLE o DCT, medir tiempo, calcular CRC32.
  Enviar INICIO / DATOS / FIN con pyRF24.
  Resolver RESPUESTA, faltantes, reintentos y timeout.
  Registrar tiempo, bytes transmitidos, reintentos y LED.
"""


def main():
    raise NotImplementedError(
        "Transmisor RF pendiente: primero ejecutar apps/simular.py y pruebas")


if __name__ == "__main__":
    main()
