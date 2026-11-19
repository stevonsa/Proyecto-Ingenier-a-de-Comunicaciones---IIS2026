"""Despliegue en el monitor HDMI escribiendo directo al framebuffer (seccion 10.4).

En Raspberry Pi OS Lite no hay escritorio ni aceleracion grafica para pygame,
asi que se dibuja con Pillow y se copia la imagen a /dev/fb0. No necesita
paquetes extra; el usuario debe pertenecer al grupo "video" (el usuario
creado con Raspberry Pi Imager ya pertenece).
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

LINEAS = [
    ("Modo", "modo"), ("Q", "calidad_Q"), ("Razon (enunciado)", "razon_compresion_enunciado"),
    ("Razon (codec)", "razon_compresion_codec"), ("Tiempo total [s]", "t_total_s"),
    ("Transmision [s]", "t_transmision_s"), ("Descompresion [s]", "t_descompresion_s"),
    ("PSNR [dB]", "psnr_db"), ("BER residual", "ber_residual"),
    ("BER canal (estim.)", "ber_canal_estimada"), ("Reintentos TX", "reintentos_tx"),
]


def _leer(ruta: Path) -> str:
    return ruta.read_text().strip()


class Pantalla:
    def __init__(self, dispositivo: str = "/dev/fb0", sysfs: str = "/sys/class/graphics/fb0"):
        info = Path(sysfs)
        self.ancho, self.alto = (int(v) for v in _leer(info / "virtual_size").split(","))
        self.bpp = int(_leer(info / "bits_per_pixel"))
        if self.bpp not in (16, 32):
            raise RuntimeError(f"Framebuffer de {self.bpp} bits no soportado")
        stride = info / "stride"
        self.stride = int(_leer(stride)) if stride.exists() else self.ancho * self.bpp // 8
        self._fb = open(dispositivo, "r+b")
        tam = max(16, self.alto // 30)
        try:
            self.fuente = ImageFont.load_default(size=tam)
        except TypeError:                # Pillow < 10.1
            self.fuente = ImageFont.load_default()
        self.interlineado = int(tam * 1.4)
        self.mensaje("Esperando imagen...")

    def _volcar(self, lienzo: Image.Image) -> None:
        rgb = np.asarray(lienzo.convert("RGB"), dtype=np.uint8)
        if self.bpp == 32:               # XRGB8888 en memoria: B, G, R, X
            pix = np.empty((self.alto, self.ancho, 4), dtype=np.uint8)
            pix[..., 0], pix[..., 1], pix[..., 2], pix[..., 3] = rgb[..., 2], rgb[..., 1], rgb[..., 0], 255
        else:                            # RGB565
            r, g, b = (rgb[..., i].astype(np.uint16) for i in range(3))
            pix = (((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)).astype("<u2")
        filas = pix.reshape(self.alto, -1).view(np.uint8)
        if filas.shape[1] < self.stride:   # relleno al final de cada fila
            filas = np.pad(filas, ((0, 0), (0, self.stride - filas.shape[1])))
        self._fb.seek(0)
        self._fb.write(filas.tobytes())
        self._fb.flush()

    def mensaje(self, texto: str) -> None:
        lienzo = Image.new("RGB", (self.ancho, self.alto), "black")
        ImageDraw.Draw(lienzo).text((40, 40), texto, fill="white", font=self.fuente)
        self._volcar(lienzo)

    def mostrar(self, imagen: np.ndarray, datos: dict) -> None:
        lienzo = Image.new("RGB", (self.ancho, self.alto), "black")
        alto_img, ancho_img = imagen.shape
        escala = max(1, min((self.ancho * 3 // 5) // ancho_img, (self.alto - 80) // alto_img))
        img = Image.fromarray(imagen, mode="L").resize(
            (ancho_img * escala, alto_img * escala), Image.NEAREST)
        lienzo.paste(img.convert("RGB"), (40, 40))
        dibujo = ImageDraw.Draw(lienzo)
        x, y = 80 + img.width, 40
        for etiqueta, clave in LINEAS:
            valor = datos.get(clave)
            if isinstance(valor, float):
                valor = f"{valor:.3g}"
            dibujo.text((x, y), f"{etiqueta}: {valor}", fill=(230, 230, 230), font=self.fuente)
            y += self.interlineado
        self._volcar(lienzo)
