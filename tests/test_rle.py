import numpy as np
import pytest
from ie0527.codecs.rle import comprimir_sin_perdidas, descomprimir_sin_perdidas


def test_rle_exacto_3_tipos():
    rng = np.random.default_rng(52)
    for image in (
        np.zeros((240, 320), dtype=np.uint8),
        np.arange(240 * 320, dtype=np.uint32).reshape(240, 320).astype(np.uint8),
        rng.integers(0, 256, (240, 320), dtype=np.uint8),
    ):
        data = comprimir_sin_perdidas(image)
        recovered = descomprimir_sin_perdidas(data, image.shape[1], image.shape[0])
        assert np.array_equal(image, recovered)


def test_run_largo_se_divide_en_255():
    image = np.full((1, 320), 7, dtype=np.uint8)
    data = comprimir_sin_perdidas(image)
    assert data == bytes([7, 255, 7, 65])


def test_rle_malformado_falla():
    with pytest.raises(ValueError):
        descomprimir_sin_perdidas(b"\x00\x02\x01", 2, 1)
    with pytest.raises(ValueError):
        descomprimir_sin_perdidas(b"\x00\x00", 1, 1)
