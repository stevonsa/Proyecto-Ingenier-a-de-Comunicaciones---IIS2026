"""RLE segun el anteproyecto: [intensidad:uint8, longitud:uint8]."""
import numpy as np
from ie0527.image_io import validate_image


def comprimir_sin_perdidas(imagen: np.ndarray) -> bytes:
    validate_image(imagen)
    pixels = imagen.tobytes(order="C")
    if not pixels:
        return b""
    encoded = bytearray()
    value, run = pixels[0], 1
    for pixel in pixels[1:]:
        if pixel == value and run < 255:
            run += 1
        else:
            encoded.extend((value, run))
            value, run = pixel, 1
    encoded.extend((value, run))
    return bytes(encoded)


def descomprimir_sin_perdidas(datos: bytes, ancho: int, alto: int) -> np.ndarray:
    if not (1 <= ancho <= 320 and 1 <= alto <= 240):
        raise ValueError("Dimensiones invalidas")
    if len(datos) % 2:
        raise ValueError("Flujo RLE incompleto: cada par ocupa dos bytes")
    esperado = ancho * alto
    decoded = bytearray()
    for i in range(0, len(datos), 2):
        value, run = datos[i], datos[i + 1]
        if run == 0:
            raise ValueError("RLE invalido: longitud de secuencia cero")
        if len(decoded) + run > esperado:
            raise ValueError("RLE supera el numero de pixeles esperado")
        decoded.extend(bytes([value]) * run)
    if len(decoded) != esperado:
        raise ValueError("RLE truncado: faltan pixeles")
    return np.frombuffer(decoded, dtype=np.uint8).reshape(alto, ancho).copy()
