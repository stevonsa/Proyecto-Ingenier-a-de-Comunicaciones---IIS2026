"""Metricas de imagen y de transferencia (contabilizacion de capa aplicacion)."""
import math
import numpy as np


# Calcula el error cuadrático medio usando float64 para evitar desbordamiento o resta
# modular de uint8.
def mse(original: np.ndarray, reconstruida: np.ndarray) -> float:
    if original.shape != reconstruida.shape:
        raise ValueError("Las imagenes tienen dimensiones distintas")
    if original.dtype != np.uint8 or reconstruida.dtype != np.uint8:
        raise ValueError("Las imagenes deben tener pixeles uint8")
    delta = original.astype(np.float64) - reconstruida.astype(np.float64)
    return float(np.mean(delta ** 2))


# Calcula 10 log10(255²/MSE); devuelve infinito si las imágenes coinciden.
def psnr(original: np.ndarray, reconstruida: np.ndarray) -> float:
    error = mse(original, reconstruida)
    return math.inf if error == 0.0 else 10 * math.log10((255.0 ** 2) / error)


# Divide el tamaño original por el destino; un valor inferior a 1 indica expansión.
def razon_compresion(tamano_original: int, tamano_destino: int) -> float:
    if tamano_destino <= 0:
        raise ValueError("El tamano destino debe ser positivo")
    return tamano_original / tamano_destino


# Expresa el porcentaje del total enviado que no corresponde a la carga útil.
def overhead_pct(tamano_enviado: int, carga_util: int) -> float:
    if tamano_enviado <= 0 or not (0 <= carga_util <= tamano_enviado):
        raise ValueError("Conteos de bytes invalidos")
    return 100 * (tamano_enviado - carga_util) / tamano_enviado


# Cuenta bits distintos mediante XOR y bit_count en flujos de igual longitud.
def bit_errors(a: bytes, b: bytes) -> int:
    if len(a) != len(b):
        raise ValueError("Para calcular BER los flujos deben tener igual longitud")
    return sum((x ^ y).bit_count() for x, y in zip(a, b))
