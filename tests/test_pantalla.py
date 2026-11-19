import numpy as np
import pytest

from ie0527.pantalla import Pantalla


def _fb_falso(tmp_path, ancho, alto, bpp, stride=None):
    sysfs = tmp_path / "fb0"
    sysfs.mkdir()
    (sysfs / "virtual_size").write_text(f"{ancho},{alto}\n")
    (sysfs / "bits_per_pixel").write_text(f"{bpp}\n")
    stride = stride or ancho * bpp // 8
    (sysfs / "stride").write_text(f"{stride}\n")
    dev = tmp_path / "fb"
    dev.write_bytes(bytes(stride * alto))
    return str(dev), str(sysfs), stride


@pytest.mark.parametrize("bpp,relleno", [(32, 0), (16, 0), (16, 64)])
def test_mostrar_escribe_el_framebuffer(tmp_path, bpp, relleno):
    ancho, alto = 800, 480
    dev, sysfs, stride = _fb_falso(tmp_path, ancho, alto, bpp, ancho * bpp // 8 + relleno)
    p = Pantalla(dev, sysfs)
    img = np.full((240, 320), 200, dtype=np.uint8)
    p.mostrar(img, {"modo": "rle", "psnr_db": "inf", "t_total_s": 0.177})
    datos = open(dev, "rb").read()
    assert len(datos) == stride * alto
    assert any(datos)                       # se dibujo algo
