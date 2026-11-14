import math
import numpy as np
from ie0527.simulator import simular


def test_simulacion_rle_y_dct():
    yy, xx = np.indices((32, 32))
    image = ((xx * 5 + yy * 3) % 256).astype(np.uint8)
    recon_rle, rle = simular(image, "rle")
    assert np.array_equal(image, recon_rle)
    assert math.isinf(rle["psnr_db"])
    assert rle["errores_bits_datos_simulados"] == 0
    recon_dct, dct = simular(image, "dct", 50)
    assert recon_dct.shape == image.shape
    assert dct["psnr_db"] > 0
