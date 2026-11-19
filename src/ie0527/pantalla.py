"""Despliegue en el monitor HDMI con pygame (opcional, seccion 10.4).

En Raspberry Pi OS Lite no hay escritorio: pygame dibuja directo en la
pantalla con el controlador kmsdrm. Instalar con: sudo apt install python3-pygame
"""
import os

import numpy as np

LINEAS = [
    ("Modo", "modo"), ("Q", "calidad_Q"), ("Razon (enunciado)", "razon_compresion_enunciado"),
    ("Razon (codec)", "razon_compresion_codec"), ("Tiempo total [s]", "t_total_s"),
    ("Transmision [s]", "t_transmision_s"), ("Descompresion [s]", "t_descompresion_s"),
    ("PSNR [dB]", "psnr_db"), ("BER residual", "ber_residual"),
    ("BER canal (estim.)", "ber_canal_estimada"), ("Reintentos TX", "reintentos_tx"),
]


class Pantalla:
    def __init__(self):
        os.environ.setdefault("SDL_VIDEODRIVER", "kmsdrm")
        import pygame
        self.pg = pygame
        pygame.display.init()
        pygame.font.init()
        info = pygame.display.Info()
        self.sup = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        self.fuente = pygame.font.SysFont(None, 34)
        self.mensaje("Esperando imagen...")

    def mensaje(self, texto: str) -> None:
        self.sup.fill((0, 0, 0))
        self.sup.blit(self.fuente.render(texto, True, (255, 255, 255)), (40, 40))
        self.pg.display.flip()

    def mostrar(self, imagen: np.ndarray, datos: dict) -> None:
        pg = self.pg
        self.sup.fill((0, 0, 0))
        rgb = np.repeat(imagen.T[:, :, None], 3, axis=2)       # pygame usa (ancho, alto)
        img = pg.surfarray.make_surface(rgb)
        ancho, alto = self.sup.get_size()
        escala = max(1, min((ancho // 2) // imagen.shape[1], (alto - 80) // imagen.shape[0]))
        img = pg.transform.scale(img, (imagen.shape[1] * escala, imagen.shape[0] * escala))
        self.sup.blit(img, (40, 40))
        x, y = 80 + img.get_width(), 40
        for etiqueta, clave in LINEAS:
            valor = datos.get(clave)
            if isinstance(valor, float):
                valor = f"{valor:.3g}"
            self.sup.blit(self.fuente.render(f"{etiqueta}: {valor}", True, (230, 230, 230)), (x, y))
            y += 40
        pg.display.flip()
        pg.event.pump()
