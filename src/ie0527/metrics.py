"""Metricas de imagen y de transferencia (contabilizacion de capa aplicacion)."""
import math
import numpy as np


def mse(original: np.ndarray, reconstruida: np.ndarray) -> float:
    if original.shape != reconstruida.shape:
        raise ValueError("Las imagenes tienen dimensiones distintas")
    if original.dtype != np.uint8 or reconstruida.dtype != np.uint8:
        raise ValueError("Las imagenes deben tener pixeles uint8")
    delta = original.astype(np.float64) - reconstruida.astype(np.float64)
    return float(np.mean(delta ** 2))


def psnr(original: np.ndarray, reconstruida: np.ndarray) -> float:
    error = mse(original, reconstruida)
    return math.inf if error == 0.0 else 10 * math.log10((255.0 ** 2) / error)


def razon_compresion(tamano_original: int, tamano_destino: int) -> float:
    if tamano_destino <= 0:
        raise ValueError("El tamano destino debe ser positivo")
    return tamano_original / tamano_destino


def overhead_pct(tamano_enviado: int, carga_util: int) -> float:
    if tamano_enviado <= 0 or not (0 <= carga_util <= tamano_enviado):
        raise ValueError("Conteos de bytes invalidos")
    return 100 * (tamano_enviado - carga_util) / tamano_enviado


def bit_errors(a: bytes, b: bytes) -> int:
    if len(a) != len(b):
        raise ValueError("Para calcular BER los flujos deben tener igual longitud")
    return sum((x ^ y).bit_count() for x, y in zip(a, b))
