"""Transferencia local de extremo a extremo SIN hardware de radio."""
import time
import numpy as np

from ie0527.codecs.rle import comprimir_sin_perdidas, descomprimir_sin_perdidas
from ie0527.codecs.dct import comprimir_con_perdidas, descomprimir_con_perdidas
from ie0527.image_io import validate_image
from ie0527.metrics import psnr, razon_compresion, overhead_pct, bit_errors
from ie0527.protocol import (
    StartFrame, Reassembler, crc32, split_data, pack_end, unpack_end,
    pack_reply, unpack_reply, OK,
)


# Ejecuta una transferencia ideal de aplicación en memoria, comprueba la reconstrucción y
# devuelve métricas locales sin modelar la radio.
def simular(imagen: np.ndarray, modo: str = "rle", calidad: int = 50) -> tuple[np.ndarray, dict]:
    """Simula paquetes a nivel de aplicacion: sin tiempos/radio/ACK fisicos reales."""
    validate_image(imagen)
    height, width = imagen.shape
    original = imagen.tobytes()
    t_start = time.perf_counter()
    if modo == "rle":
        compressed = comprimir_sin_perdidas(imagen)
        q = 0
    elif modo == "dct":
        compressed = comprimir_con_perdidas(imagen, calidad)
        q = calidad
    else:
        raise ValueError("Modo debe ser rle o dct")
    t_compress = time.perf_counter() - t_start

    # Construye y procesa tramas reales del protocolo, pero sin pérdidas ni ACK de
    # hardware.
    data_frames = split_data(compressed)
    meta = StartFrame(
        session=1, group=1, mode=modo, quality=q,
        width=width, height=height, compressed_length=len(compressed),
        original_length=len(original), total_frames=len(data_frames),
        crc_compressed=crc32(compressed), crc_original=crc32(original),
        pre_start_ms=0,
    )
    start_frame = meta.pack()
    end_frame = pack_end(meta.session, meta.crc_compressed)
    rx_meta = StartFrame.unpack(start_frame)
    rx = Reassembler(rx_meta)
    for frame in data_frames:
        rx.add(frame)
    session, ending_crc, retry_count = unpack_end(end_frame)
    if session != rx_meta.session or ending_crc != rx_meta.crc_compressed or rx.missing():
        raise ValueError("Fallo de sesion, integridad o fragmentacion")
    received_compressed = rx.reconstruct()
    reply = pack_reply(session, OK)
    _, reply_status, _ = unpack_reply(reply)
    if reply_status != OK:
        raise ValueError("El receptor no confirmó la transferencia")

    t_dec_start = time.perf_counter()
    if modo == "rle":
        restored = descomprimir_sin_perdidas(received_compressed, width, height)
        if crc32(restored.tobytes()) != rx_meta.crc_original or not np.array_equal(imagen, restored):
            raise ValueError("El modo sin perdidas no recuperó la imagen")
    else:
        restored = descomprimir_con_perdidas(received_compressed, width, height, calidad)
    t_decompress = time.perf_counter() - t_dec_start
    # Contabiliza las cuatro clases de tramas de aplicación, incluida RESPUESTA.
    application_bytes = sum(map(len, [start_frame, *data_frames, end_frame, reply]))
    info = {
        "modo": modo,
        "calidad_Q": q,
        "bytes_originales_pixeles": len(original),
        "bytes_comprimidos": len(compressed),
        "tramas_datos": len(data_frames),
        "bytes_aplicacion_sin_acks_fisicos": application_bytes,
        "razon_codec": razon_compresion(len(original), len(compressed)),
        "razon_con_protocolo_app_simulado": razon_compresion(len(original), application_bytes),
        "sobrecarga_app_simulada_pct": overhead_pct(application_bytes, len(compressed)),
        "segundos_compresion_pc": t_compress,
        "segundos_descompresion_pc": t_decompress,
        "psnr_db": psnr(imagen, restored),
        "identica": bool(np.array_equal(imagen, restored)),
        "errores_bits_datos_simulados": bit_errors(compressed, received_compressed),
    }
    return restored, info
