"""Punto de entrada futuro para la Raspberry Pi receptora (no funcional aun).

Orden previsto:
  Radio en escucha continua; LED espera; no conocer inicio.
  Recibir INICIO y crear Reassembler.
  Recibir DATOS / omitir duplicados / solicitar faltantes.
  En FIN verificar CRC32 comprimido, enviar RESPUESTA.
  Decodificar RLE o DCT segun metadata.
  En RLE verificar CRC32 original de pixeles.
  Guardar BMP/PGM y mostrar imagen en HDMI (pygame).
  Registrar metricas en CSV y senalizar LED.
"""


def main():
    raise NotImplementedError(
        "Receptor RF pendiente: primero ejecutar apps/simular.py y pruebas")


if __name__ == "__main__":
    main()
