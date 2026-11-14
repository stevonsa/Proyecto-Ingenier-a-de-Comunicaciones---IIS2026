import numpy as np
from ie0527.codecs.rle import comprimir_sin_perdidas
from ie0527.protocol import (
    StartFrame, Reassembler, split_data, crc32, pack_end, unpack_end,
    pack_reply, unpack_reply, OK, MISSING,
)


def test_roundtrip_protocolo_y_datos():
    pixels = np.tile(np.arange(30, dtype=np.uint8), (7, 1))
    raw = pixels.tobytes()
    encoded = comprimir_sin_perdidas(pixels)
    packets = split_data(encoded)
    meta = StartFrame(
        session=5, group=2, mode="rle", quality=0, width=30, height=7,
        compressed_length=len(encoded), original_length=len(raw), total_frames=len(packets),
        crc_compressed=crc32(encoded), crc_original=crc32(raw),
    )
    start_frame = meta.pack()
    assert len(start_frame) == 32
    assert all(len(p) <= 32 for p in packets)
    rx = Reassembler(StartFrame.unpack(start_frame))
    for packet in reversed(packets):
        rx.add(packet)
    rx.add(packets[0])  # Duplicado identico
    assert rx.missing() == []
    assert rx.reconstruct() == encoded
    assert unpack_end(pack_end(5, crc32(encoded), 0)) == (5, crc32(encoded), 0)
    assert unpack_reply(pack_reply(5, OK)) == (5, OK, [])
    missing = list(range(1, 15))
    assert len(pack_reply(5, MISSING, missing)) == 32
    assert unpack_reply(pack_reply(5, MISSING, missing)) == (5, MISSING, missing)
