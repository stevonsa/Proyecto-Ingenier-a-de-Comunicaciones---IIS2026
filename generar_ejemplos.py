"""Prueba offline (no transmite RF): python apps/simular.py imagen.pgm --modo rle"""
import argparse
import json
import math
from pathlib import Path

from ie0527.image_io import load_image, save_image
from ie0527.simulator import simular


# Carga una imagen, ejecuta la simulación ideal y guarda la reconstrucción con métricas
# JSON.
def main():
    parser = argparse.ArgumentParser(description="IE0527: prueba de codificacion y tramas SIN radio")
    parser.add_argument("imagen", type=Path, help="Ruta de una imagen BMP/PGM gris 8 bits")
    parser.add_argument("--modo", choices=["rle", "dct"], default="rle")
    parser.add_argument("--q", type=int, default=50, help="Factor de calidad DCT 1..100")
    parser.add_argument("--salida", type=Path, default=Path("data/salida/reconstruida.pgm"))
    args = parser.parse_args()
    original = load_image(args.imagen)
    restored, result = simular(original, args.modo, args.q)
    save_image(restored, args.salida)
    print("Archivo reconstruido:", args.salida)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=True))
    print("NOTA: sin prueba de radio; los bytes y tiempos NO son mediciones RF reales")


if __name__ == "__main__":
    main()
