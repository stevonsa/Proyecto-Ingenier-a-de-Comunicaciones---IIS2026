"""Codec DCT simplificado, NO es un archivo JPEG compatible.

Flujo determinista propio (metadatos externos en trama INICIO):
  cada bloque: delta DC (int16 big-endian), seguido de tokens AC
  [numero_de_ceros:uint8 (0..62), valor:int16] para AC no nulos,
  final de bloque: marcador 0xFF (no puede ser longitud de ceros).
La calidad Q (1..100) y dimensiones viajan en INICIO.
"""
import math
import struct

import numpy as np
from ie0527.image_io import validate_image

# Matriz base luminancia del JPEG (referencia; no interoperable con JPEG).
BASE = np.array([
    [16, 11, 10, 16, 24, 40, 51, 61],
    [12, 12, 14, 19, 26, 58, 60, 55],
    [14, 13, 16, 24, 40, 57, 69, 56],
    [14, 17, 22, 29, 51, 87, 80, 62],
    [18, 22, 37, 56, 68, 109, 103, 77],
    [24, 35, 55, 64, 81, 104, 113, 92],
    [49, 64, 78, 87, 103, 121, 120, 101],
    [72, 92, 95, 98, 112, 100, 103, 99],
], dtype=np.int32)


# Construye la base ortonormal de la DCT-II de ocho muestras, reutilizada en ambas
# direcciones.
def _dct_matrix():
    return np.array([
        [(math.sqrt(1 / 8) if u == 0 else math.sqrt(2 / 8))
         * math.cos((2 * x + 1) * u * math.pi / 16)
         for x in range(8)]
        for u in range(8)
    ], dtype=np.float64)


C = _dct_matrix()


# Recorre diagonales alternando su sentido para ordenar los 64 coeficientes desde DC hacia
# frecuencias altas.
def _zigzag():
    order = []
    for s in range(15):
        coords = [(r, s - r) for r in range(8) if 0 <= s - r < 8]
        if s % 2 == 0:
            coords.reverse()
        order.extend(coords)
    return order


ZIGZAG = _zigzag()


# Escala la tabla de luminancia con Q (1–100); Q alto reduce el paso de cuantización.
# Limita cada paso a 1–255.
def quant_table(q: int) -> np.ndarray:
    if type(q) is not int or not (1 <= q <= 100):
        raise ValueError("El factor de calidad Q debe ser entero de 1 a 100")
    scale = 5000 / q if q < 50 else 200 - 2 * q
    return np.clip(np.floor((BASE * scale + 50) / 100), 1, 255).astype(np.int32)


# Calcula el número de bloques de 8 × 8 incluyendo el relleno de los bordes.
def _block_count(width: int, height: int) -> int:
    return math.ceil(width / 8) * math.ceil(height / 8)


# Transforma, cuantiza y serializa bloques; el flujo no incluye dimensiones ni Q, que
# viajan en INICIO.
def comprimir_con_perdidas(imagen: np.ndarray, nivel: int) -> bytes:
    validate_image(imagen)
    table = quant_table(nivel)
    height, width = imagen.shape
    # Completa bloques parciales replicando el borde en lugar de introducir un borde
    # negro.
    pad_h, pad_w = (-height) % 8, (-width) % 8
    padded = np.pad(imagen, ((0, pad_h), (0, pad_w)), mode="edge")
    previous_dc = 0
    data = bytearray()
    for row in range(0, padded.shape[0], 8):
        for col in range(0, padded.shape[1], 8):
            block = padded[row:row + 8, col:col + 8].astype(np.float64) - 128.0
            # DCT bidimensional separable tras centrar las intensidades alrededor de cero.
            coefficients = C @ block @ C.T
            # La cuantización es la etapa que descarta información y controla la
            # distorsión.
            quantized = np.rint(coefficients / table).astype(np.int32)
            seq = [int(quantized[r, c]) for r, c in ZIGZAG]
            dc = seq[0]
            # Codificación diferencial del coeficiente DC respecto al bloque anterior.
            delta_dc = dc - previous_dc
            if not (-32768 <= delta_dc <= 32767):
                raise ValueError("Delta DC fuera del rango int16")
            data.extend(struct.pack(">h", delta_dc))
            previous_dc = dc
            # Los AC nulos se representan por la longitud de la corrida antes del
            # siguiente no nulo.
            zeros = 0
            for value in seq[1:]:
                if value == 0:
                    zeros += 1
                else:
                    if not (-32768 <= value <= 32767):
                        raise ValueError("Coeficiente AC fuera del rango int16")
                    data.extend(struct.pack(">Bh", zeros, value))
                    zeros = 0
            data.append(255)  # Fin de bloque, ceros restantes implicitos.
    return bytes(data)


# Interpreta el flujo de bloques, recupera DC y AC, aplica DCT inversa y recorta el
# relleno. Devuelve píxeles uint8.
def descomprimir_con_perdidas(datos: bytes, ancho: int, alto: int, nivel: int) -> np.ndarray:
    if not (1 <= ancho <= 320 and 1 <= alto <= 240):
        raise ValueError("Dimensiones invalidas")
    table = quant_table(nivel)
    padded_h = math.ceil(alto / 8) * 8
    padded_w = math.ceil(ancho / 8) * 8
    output = np.zeros((padded_h, padded_w), dtype=np.uint8)
    previous_dc = 0
    pos = 0
    for row in range(0, padded_h, 8):
        for col in range(0, padded_w, 8):
            if pos + 2 > len(datos):
                raise ValueError("DCT truncado: falta DC")
            (delta,) = struct.unpack_from(">h", datos, pos)
            pos += 2
            dc = previous_dc + delta
            previous_dc = dc
            # Inicializa AC a cero; los tokens solo rellenan las posiciones no nulas.
            seq = [dc] + [0] * 63
            idx = 1
            while True:
                if pos >= len(datos):
                    raise ValueError("DCT truncado: falta fin de bloque")
                run = datos[pos]
                pos += 1
                if run == 255:
                    break
                if run > 62 or idx + run >= 64 or pos + 2 > len(datos):
                    raise ValueError("Token AC mal formado")
                (value,) = struct.unpack_from(">h", datos, pos)
                pos += 2
                if value == 0:
                    raise ValueError("AC cero debe codificarse como longitud de ceros")
                idx += run
                seq[idx] = value
                idx += 1
            qblock = np.zeros((8, 8), dtype=np.float64)
            for (r, c), value in zip(ZIGZAG, seq):
                qblock[r, c] = value
            # Descuantiza e invierte la transformación; luego redondea y satura a 0–255.
            restored = C.T @ (qblock * table) @ C + 128.0
            output[row:row + 8, col:col + 8] = np.clip(np.rint(restored), 0, 255).astype(np.uint8)
    if pos != len(datos):
        raise ValueError("DCT contiene bytes sobrantes")
    # El receptor conoce las dimensiones originales y elimina el relleno.
    return output[:alto, :ancho].copy()
