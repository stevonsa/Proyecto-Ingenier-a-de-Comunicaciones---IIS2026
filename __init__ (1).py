"""Decodificacion y metricas en el receptor (seccion 12.1 del anteproyecto).

El receptor reconoce la imagen original por el CRC32 de sus pixeles, que
viaja en INICIO. Si tiene una copia de referencia (carpeta --referencias):
  - PSNR: original contra reconstruida.
  - BER residual: sin perdidas, bits distintos entre imagenes; con perdidas,
    recomprime la referencia con el mismo Q (el codec es determinista) y
    compara bit a bit con los datos comprimidos recibidos.
"""
import csv
import math
import time
from pathlib import Path

import numpy as np

from ie0527.codecs.dct import comprimir_con_perdidas, descomprimir_con_perdidas
from ie0527.codecs.rle import descomprimir_sin_perdidas
from ie0527.image_io import load_image
from ie0527.link import ResultadoRX
from ie0527.metrics import bit_errors, psnr
from ie0527.protocol import crc32

BITS_POR_TRAMA_AIRE = 329   # trama DATOS completa a 2 Mbps (seccion 7.6)


# Indexa imágenes válidas por CRC32 de píxeles para identificar la referencia sin
# transmitir su nombre.
def cargar_referencias(carpeta: Path | None) -> dict[int, tuple[str, np.ndarray]]:
    refs = {}
    if carpeta is None:
        return refs
    for ruta in sorted(Path(carpeta).iterdir()):
        if ruta.suffix.lower() in {".bmp", ".pgm"}:
            try:
                img = load_image(ruta)
            except ValueError:
                continue
            refs[crc32(img.tobytes())] = (ruta.name, img)
    return refs


# Selecciona el decodificador según INICIO y devuelve la imagen y el tiempo de
# descompresión en segundos.
def decodificar(res: ResultadoRX) -> tuple[np.ndarray, float]:
    m = res.meta
    t0 = time.perf_counter()
    if m.mode == "rle":
        imagen = descomprimir_sin_perdidas(res.datos, m.width, m.height)
    else:
        imagen = descomprimir_con_perdidas(res.datos, m.width, m.height, m.quality)
    return imagen, time.perf_counter() - t0


# Calcula indicadores del receptor y, si existe referencia, PSNR y BER residual. La BER de
# canal es una estimación basada en reintentos.
def metricas(res: ResultadoRX, imagen: np.ndarray, t_descompresion: float,
             referencias: dict[int, tuple[str, np.ndarray]]) -> dict:
    m = res.meta
    t_previo = m.pre_start_ms / 1000
    reintentos = res.reintentos_tx
    # Aproximación a partir de reintentos, no una medición directa de errores de trama.
    per = reintentos / (m.total_frames + reintentos) if (m.total_frames + reintentos) else 0.0
    # Los bytes recibidos incluyen encabezados y duplicados observados por RX, no todos
    # los bits en el aire.
    datos = {
        "sesion": m.session,
        "modo": m.mode,
        "calidad_Q": m.quality,
        "ancho": m.width,
        "alto": m.height,
        "bytes_originales": m.original_length,
        "bytes_comprimidos": m.compressed_length,
        "bytes_recibidos_app": res.bytes_recibidos,
        "razon_compresion_codec": round(m.original_length / m.compressed_length, 3),
        "razon_compresion_enunciado": round(m.original_length / res.bytes_recibidos, 3),
        "sobrecarga_pct": round(100 * (res.bytes_recibidos - m.compressed_length) / res.bytes_recibidos, 2),
        "t_previo_tx_s": round(t_previo, 4),
        "t_transmision_s": round(res.segundos_transmision, 4),
        "t_descompresion_s": round(t_descompresion, 4),
        "t_total_s": round(t_previo + res.segundos_transmision + t_descompresion, 4),
        "tasa_util_kbps": round(m.compressed_length * 8 / res.segundos_transmision / 1000, 1)
        if res.segundos_transmision > 0 else None,
        "reintentos_tx": reintentos,
        "tramas_recibidas": res.tramas_recibidas,
        "duplicadas": res.duplicadas,
        "rondas_fin": res.rondas_fin,
        "errores_crc32": res.errores_crc32,
        "per_estimada": round(per, 5),
        "ber_canal_estimada": per / BITS_POR_TRAMA_AIRE,
        "crc32_original_ok": crc32(imagen.tobytes()) == m.crc_original if m.mode == "rle" else None,
        "referencia": None,
        "psnr_db": None,
        "ber_residual": None,
    }
    # Sin una referencia local no se puede calcular PSNR ni BER residual.
    ref = referencias.get(m.crc_original)
    if ref is not None:
        nombre, original = ref
        datos["referencia"] = nombre
        valor = psnr(original, imagen)
        datos["psnr_db"] = "inf" if math.isinf(valor) else round(valor, 2)
        if m.mode == "rle":
            errores, bits = bit_errors(original.tobytes(), imagen.tobytes()), original.size * 8
        else:
            # En DCT se compara el flujo comprimido determinista para no confundir
            # distorsión con errores de canal.
            esperado = comprimir_con_perdidas(original, m.quality)
            if len(esperado) == len(res.datos):
                errores, bits = bit_errors(esperado, res.datos), len(esperado) * 8
            else:
                errores, bits = None, None
        datos["ber_residual"] = None if errores is None else errores / bits
    return datos


# Añade una fila fechada al CSV; escribe encabezados únicamente al crear el archivo.
def guardar_csv(ruta: Path, fila: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not ruta.exists()
    with ruta.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["fecha_hora", *fila.keys()])
        if nuevo:
            w.writeheader()
        w.writerow({"fecha_hora": time.strftime("%Y-%m-%d %H:%M:%S"), **fila})
