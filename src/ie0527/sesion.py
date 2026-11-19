"""Preparacion de una transferencia en el transmisor: leer, comprimir y armar INICIO."""
import time
from pathlib import Path

import numpy as np

from ie0527.codecs.dct import comprimir_con_perdidas
from ie0527.codecs.rle import comprimir_sin_perdidas
from ie0527.image_io import load_image
from ie0527.protocol import StartFrame, crc32, split_data


def preparar(imagen: Path | np.ndarray, modo: str, q: int, sesion: int, grupo: int,
             t_boton: float) -> tuple[StartFrame, bytes, float]:
    """Devuelve (metadatos de INICIO, datos comprimidos, segundos de compresion).

    t_boton es el instante (perf_counter) en que se pulso el boton; la diferencia
    hasta armar INICIO viaja en el campo de marca temporal (seccion 10.5).
    """
    if not isinstance(imagen, np.ndarray):
        imagen = load_image(imagen)
    alto, ancho = imagen.shape
    t0 = time.perf_counter()
    if modo == "rle":
        datos, calidad = comprimir_sin_perdidas(imagen), 0
    elif modo == "dct":
        datos, calidad = comprimir_con_perdidas(imagen, q), q
    else:
        raise ValueError("Modo debe ser rle o dct")
    t_compresion = time.perf_counter() - t0
    meta = StartFrame(
        session=sesion, group=grupo, mode=modo, quality=calidad,
        width=ancho, height=alto, compressed_length=len(datos),
        original_length=imagen.size, total_frames=len(split_data(datos)),
        crc_compressed=crc32(datos), crc_original=crc32(imagen.tobytes()),
        pre_start_ms=min(int((time.perf_counter() - t_boton) * 1000), 0xFFFFFFFF),
    )
    return meta, datos, t_compresion
