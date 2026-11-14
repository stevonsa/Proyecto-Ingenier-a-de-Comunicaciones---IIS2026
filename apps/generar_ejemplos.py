"""Genera datos sinteticos para desarrollo; no sustituyen la fotografia del profesor."""
from pathlib import Path
import numpy as np
from ie0527.image_io import save_image


def main():
    folder = Path("data/entrada")
    folder.mkdir(parents=True, exist_ok=True)
    uniform = np.zeros((240, 320), dtype=np.uint8)
    uniform[:, :100] = 30
    uniform[:, 100:240] = 130
    uniform[:, 240:] = 220
    save_image(uniform, folder / "areas_uniformes.pgm")

    yy, xx = np.indices((240, 320))
    detail = np.where((xx + yy) % 2 == 0, 0, 255).astype(np.uint8)
    save_image(detail, folder / "detalle_fino.pgm")

    gradient = np.broadcast_to(np.linspace(0, 255, 320, dtype=np.uint8), (240, 320)).copy()
    save_image(gradient, folder / "gradiente.pgm")
    print("Tres imagenes sinteticas creadas en", folder)


if __name__ == "__main__":
    main()
