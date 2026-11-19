import threading

import numpy as np
import pytest

from ie0527.hardware.simulada import CanalSimulado
from ie0527.link import ConfigEnlace, EnlaceCaido, Receptor, enviar_imagen
from ie0527.protocol import OK, unpack_reply
from ie0527.sesion import preparar


def _imagen():
    yy, xx = np.indices((120, 160))
    return ((xx * 7 + yy * 3) % 256).astype(np.uint8)


def _transferir(canal, modo="rle", q=50, sesion=3):
    meta, datos, _ = preparar(_imagen(), modo, q, sesion, 1, 0.0)
    salida = {}
    rx = Receptor(canal.rx, ConfigEnlace())
    hilo = threading.Thread(target=lambda: salida.update(res=rx.recibir(esperar_s=10)))
    hilo.start()
    stats = enviar_imagen(canal.tx, meta, datos, ConfigEnlace(), semilla=0)
    hilo.join(timeout=30)
    return meta, datos, stats, salida["res"], rx


@pytest.mark.parametrize("modo", ["rle", "dct"])
def test_canal_perfecto(modo):
    meta, datos, stats, res, _ = _transferir(CanalSimulado(), modo)
    assert res.datos == datos
    assert res.meta == meta
    assert stats.retransmisiones_app == 0 and res.duplicadas == 0


@pytest.mark.parametrize("semilla", range(5))
def test_canal_con_perdidas_y_acks_perdidos(semilla):
    canal = CanalSimulado(perdida=0.2, perdida_ack=0.05, semilla=semilla)
    meta, datos, stats, res, _ = _transferir(canal, "rle")
    assert res.datos == datos                      # llega completo y sin errores
    assert stats.retransmisiones_app > 0           # hubo reenvios
    assert res.rondas_fin >= 1


def test_perdida_alta_se_recupera():
    canal = CanalSimulado(perdida=0.5, semilla=3)  # pierde la mitad de los intentos
    cfg = ConfigEnlace(intentos_trama=1, max_fallos_seguidos=1000)
    meta, datos, _ = preparar(_imagen(), "rle", 0, 9, 1, 0.0)
    salida = {}
    rx = Receptor(canal.rx, cfg)
    hilo = threading.Thread(target=lambda: salida.update(res=rx.recibir(esperar_s=10)))
    hilo.start()
    stats = enviar_imagen(canal.tx, meta, datos, cfg, semilla=0)
    hilo.join(timeout=30)
    assert salida["res"].datos == datos
    assert stats.tramas_reenviadas_por_faltantes > 14


class _RadioQuePierdeConAck:
    """Confirma pero no entrega las primeras 40 tramas DATOS (caso extremo)."""

    def __init__(self, radio):
        self._radio, self.descartadas = radio, set()

    def send(self, frame):
        from ie0527.protocol import DATA, frame_seq, frame_type
        if frame_type(frame) == DATA and frame_seq(frame) <= 40 and frame_seq(frame) not in self.descartadas:
            self.descartadas.add(frame_seq(frame))
            return True
        return self._radio.send(frame)

    def receive(self, timeout_s=None):
        return self._radio.receive(timeout_s)


def test_mas_de_14_faltantes_se_piden_por_lotes():
    canal = CanalSimulado()
    meta, datos, _ = preparar(_imagen(), "rle", 0, 12, 1, 0.0)
    salida = {}
    rx = Receptor(canal.rx, ConfigEnlace())
    hilo = threading.Thread(target=lambda: salida.update(res=rx.recibir(esperar_s=10)))
    hilo.start()
    stats = enviar_imagen(_RadioQuePierdeConAck(canal.tx), meta, datos, ConfigEnlace())
    hilo.join(timeout=30)
    assert salida["res"].datos == datos
    assert stats.tramas_reenviadas_por_faltantes == 40
    assert salida["res"].rondas_fin == 4               # 14 + 14 + 12 faltantes y luego OK


def test_sin_receptor_el_enlace_cae():
    canal = CanalSimulado()
    canal.activo[1] = False                        # nadie escucha
    meta, datos, _ = preparar(_imagen(), "rle", 0, 1, 1, 0.0)
    with pytest.raises(EnlaceCaido):
        enviar_imagen(canal.tx, meta, datos, ConfigEnlace())


def test_fin_repetido_tras_exito_recibe_ok_otra_vez():
    canal = CanalSimulado()
    meta, datos, _, res, rx = _transferir(canal, "rle", sesion=11)
    canal.tx.vaciar()
    from ie0527.protocol import pack_end
    canal.tx.send(pack_end(meta.session, meta.crc_compressed, 0))  # el TX no vio el OK
    hilo = threading.Thread(target=lambda: rx.recibir(esperar_s=0.5))
    hilo.start()
    respuesta = canal.tx.receive(2)
    hilo.join()
    assert respuesta is not None and unpack_reply(respuesta)[1] == OK
