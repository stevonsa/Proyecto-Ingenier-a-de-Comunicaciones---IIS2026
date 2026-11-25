"""Carga y guardado de imagenes de hasta 320x240 pixeles, 8 bits grises."""
from pathlib import Path
import numpy as np
from PIL import Image

MAX_WIDTH = 320
MAX_HEIGHT = 240


# Exige una matriz NumPy bidimensional uint8, no vacía y de hasta 320 × 240.
def validate_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise TypeError("La imagen debe ser una matriz NumPy")
    if image.ndim != 2 or image.dtype != np.uint8:
        raise ValueError("Se requiere una imagen de escala de grises de 8 bits")
    height, width = image.shape
    if not (1 <= width <= MAX_WIDTH and 1 <= height <= MAX_HEIGHT):
        raise ValueError("Dimensiones fuera del maximo 320x240")


# Lee BMP o PGM ya en gris de 8 bits; valida extensión, formato real y dimensiones sin
# conversión automática.
def load_image(path: str | Path) -> np.ndarray:
    path = Path(path)
    if path.suffix.lower() not in {".bmp", ".pgm"}:
        raise ValueError("Solamente BMP o PGM")
    with Image.open(path) as img:
        if img.format not in {"BMP", "PPM"}:  # Pillow usa PPM para PGM
            raise ValueError("El archivo no contiene BMP ni PGM")
        if img.mode != "L":
            raise ValueError("La imagen debe estar ya en gris de 8 bits (L), sin convertirla")
        array = np.array(img, dtype=np.uint8)
    validate_image(array)
    return array


# Valida los píxeles y guarda BMP o PGM, creando el directorio de salida si hace falta.
def save_image(image: np.ndarray, path: str | Path) -> None:
    validate_image(image)
    path = Path(path)
    if path.suffix.lower() not in {".bmp", ".pgm"}:
        raise ValueError("Solamente salida BMP o PGM")
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image, mode="L").save(path)
