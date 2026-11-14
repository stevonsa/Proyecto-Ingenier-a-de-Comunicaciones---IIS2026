"""Protocolo de aplicacion basado en la seccion 7.6 del anteproyecto.

Tramas nRF24: 32 bytes maximo. Encabezado 2 bytes: [tipo 2 bits | seq 14 bits].
INICIO: 32 bytes exactos, DATOS: 2 + hasta 30, FIN: 9,
RESPUESTA: 4 + hasta 14 secuencias de 2 bytes.
No sustituye ACK/CRC16 fisicos que administra el chip de radio.
"""
from dataclasses import dataclass, field
import math
import struct
import zlib

MAX_FRAME = 32
DATA_SIZE = 30
MAX_SEQ = 0x3FFF
START, DATA, END, REPLY = range(4)
OK, MISSING, CRC_ERROR, DECODE_ERROR = range(4)
START_STRUCT = struct.Struct(">HBBBHHBIIHIII")
END_STRUCT = struct.Struct(">HBIH")
REPLY_STRUCT = struct.Struct(">HBB")
assert START_STRUCT.size == 32


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def _header(kind: int, seq: int = 0) -> int:
    if kind not in (START, DATA, END, REPLY) or not (0 <= seq <= MAX_SEQ):
        raise ValueError("Tipo o secuencia incorrecta")
    return (kind << 14) | seq


def frame_type(frame: bytes) -> int:
    if len(frame) < 2 or len(frame) > MAX_FRAME:
        raise ValueError("Trama invalida")
    return struct.unpack_from(">H", frame)[0] >> 14


def frame_seq(frame: bytes) -> int:
    if len(frame) < 2:
        raise ValueError("Trama incompleta")
    return struct.unpack_from(">H", frame)[0] & MAX_SEQ


@dataclass(frozen=True)
class StartFrame:
    session: int
    group: int
    mode: str  # "rle" o "dct"
    quality: int
    width: int
    height: int
    compressed_length: int
    original_length: int
    total_frames: int
    crc_compressed: int
    crc_original: int
    pre_start_ms: int = 0

    def pack(self) -> bytes:
        if not (0 <= self.session <= 255 and 0 <= self.group <= 255):
            raise ValueError("Session/grupo fuera de rango")
        if not (1 <= self.width <= 320 and 1 <= self.height <= 240):
            raise ValueError("Dimensiones invalidas")
        if self.original_length != self.width * self.height:
            raise ValueError("Tamaño original invalido")
        if self.compressed_length <= 0 or self.total_frames != math.ceil(self.compressed_length / DATA_SIZE):
            raise ValueError("Tamaño comprimido o numero de tramas invalido")
        if not (1 <= self.total_frames <= MAX_SEQ):
            raise ValueError("Demasiadas tramas")
        if self.mode == "rle" and self.quality == 0:
            mode_byte = 0
        elif self.mode == "dct" and 1 <= self.quality <= 100:
            mode_byte = 0x80 | self.quality
        else:
            raise ValueError("Modo/calidad invalidos")
        return START_STRUCT.pack(
            _header(START), self.session, self.group, mode_byte,
            self.width, self.height, 8, self.compressed_length,
            self.original_length, self.total_frames, self.crc_compressed,
            self.crc_original, self.pre_start_ms,
        )

    @classmethod
    def unpack(cls, frame: bytes) -> "StartFrame":
        if len(frame) != START_STRUCT.size:
            raise ValueError("INICIO debe ocupar 32 bytes")
        (head, session, group, mode_byte, width, height, depth,
         compressed_len, original_len, count, cc, co, wait_ms) = START_STRUCT.unpack(frame)
        if head != _header(START) or depth != 8:
            raise ValueError("Trama INICIO mal formada")
        mode = "dct" if mode_byte & 0x80 else "rle"
        q = mode_byte & 0x7F
        result = cls(session, group, mode, q, width, height, compressed_len,
                     original_len, count, cc, co, wait_ms)
        result.pack()  # Reutiliza validaciones de contenido.
        return result


def split_data(data: bytes) -> list[bytes]:
    if not data:
        raise ValueError("No hay datos comprimidos")
    count = math.ceil(len(data) / DATA_SIZE)
    if count > MAX_SEQ:
        raise ValueError("El contador de 14 bits no alcanza")
    return [struct.pack(">H", _header(DATA, i + 1)) + data[i * DATA_SIZE:(i + 1) * DATA_SIZE]
            for i in range(count)]


def pack_end(session: int, compressed_crc: int, retry_count: int = 0) -> bytes:
    return END_STRUCT.pack(_header(END), session, compressed_crc, retry_count)


def unpack_end(frame: bytes) -> tuple[int, int, int]:
    if len(frame) != END_STRUCT.size:
        raise ValueError("Longitud FIN invalida")
    head, session, crc_value, retries = END_STRUCT.unpack(frame)
    if head != _header(END):
        raise ValueError("Tipo de trama invalido")
    return session, crc_value, retries


def pack_reply(session: int, status: int, missing: list[int] | None = None) -> bytes:
    missing = missing or []
    if len(missing) > 14 or status not in (OK, MISSING, CRC_ERROR, DECODE_ERROR):
        raise ValueError("RESPUESTA invalida")
    if not all(1 <= seq <= MAX_SEQ for seq in missing):
        raise ValueError("Numero de secuencia invalido")
    return REPLY_STRUCT.pack(_header(REPLY), session, status) + b"".join(
        struct.pack(">H", seq) for seq in missing)


def unpack_reply(frame: bytes) -> tuple[int, int, list[int]]:
    if len(frame) < 4 or len(frame) > 32 or (len(frame) - 4) % 2:
        raise ValueError("Longitud RESPUESTA invalida")
    header, session, status = REPLY_STRUCT.unpack_from(frame)
    if header != _header(REPLY) or status not in (OK, MISSING, CRC_ERROR, DECODE_ERROR):
        raise ValueError("RESPUESTA mal formada")
    missing = [struct.unpack_from(">H", frame, pos)[0] for pos in range(4, len(frame), 2)]
    if not all(1 <= seq <= MAX_SEQ for seq in missing):
        raise ValueError("Secuencias faltantes invalidas")
    return session, status, missing


@dataclass
class Reassembler:
    meta: StartFrame
    packets: dict[int, bytes] = field(default_factory=dict)

    def add(self, frame: bytes) -> None:
        if frame_type(frame) != DATA or len(frame) < 3:
            raise ValueError("Se esperaba una trama DATOS")
        seq = frame_seq(frame)
        if not (1 <= seq <= self.meta.total_frames):
            raise ValueError("Secuencia DATOS fuera de rango")
        payload = frame[2:]
        expected_len = DATA_SIZE if seq < self.meta.total_frames else (
            self.meta.compressed_length - DATA_SIZE * (self.meta.total_frames - 1))
        if len(payload) != expected_len:
            raise ValueError("Longitud de fragmento invalida")
        if seq in self.packets and self.packets[seq] != payload:
            raise ValueError("Duplicado contradictorio")
        self.packets[seq] = payload

    def missing(self) -> list[int]:
        return [seq for seq in range(1, self.meta.total_frames + 1)
                if seq not in self.packets]

    def reconstruct(self) -> bytes:
        if self.missing():
            raise ValueError("Faltan fragmentos")
        result = b"".join(self.packets[seq] for seq in range(1, self.meta.total_frames + 1))
        if len(result) != self.meta.compressed_length or crc32(result) != self.meta.crc_compressed:
            raise ValueError("CRC32 de datos comprimidos incorrecto")
        return result
