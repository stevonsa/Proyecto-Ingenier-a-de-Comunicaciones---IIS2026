"""Verifica Nrf24Radio contra un pyrf24 falso (solo nombres y orden de llamadas)."""
import sys
import types

import pytest


class _RF24Falso:
    def __init__(self, ce, csn):
        self.llamadas, self.rx, self.escuchando = [("init", ce, csn)], [], False

    def __getattr__(self, nombre):           # setChannel, setDataRate, etc.
        return lambda *a: self.llamadas.append((nombre, *a))

    def begin(self): return True
    def isPVariant(self): return True
    def write(self, buf): self.llamadas.append(("write", bytes(buf))); return True
    def getARC(self): return 2
    def startListening(self): self.escuchando = True
    def stopListening(self, addr=None): self.escuchando = False; self.llamadas.append(("stop", addr))
    def available(self): return bool(self.rx)
    def getDynamicPayloadSize(self): return len(self.rx[0])
    def read(self, n): return bytearray(self.rx.pop(0)[:n])
    def testRPD(self): return False


@pytest.fixture
def radio(monkeypatch):
    mod = types.ModuleType("pyrf24")
    mod.RF24 = _RF24Falso
    for nombre in ["RF24_2MBPS", "RF24_1MBPS", "RF24_250KBPS", "RF24_PA_MIN", "RF24_PA_LOW",
                   "RF24_PA_HIGH", "RF24_PA_MAX", "RF24_CRC_16"]:
        setattr(mod, nombre, nombre)
    monkeypatch.setitem(sys.modules, "pyrf24", mod)
    from ie0527.hardware.radio import Nrf24Radio, direcciones
    tx, rx = direcciones(1)
    return Nrf24Radio(tx, rx)


def test_configuracion_del_anteproyecto(radio):
    hechas = {c[0]: c[1:] for c in radio._r.llamadas}
    assert hechas["init"] == (22, 0)
    assert hechas["setChannel"] == (80,)
    assert hechas["setDataRate"] == ("RF24_2MBPS",)
    assert hechas["setRetries"] == (1, 15)
    assert hechas["setCRCLength"] == ("RF24_CRC_16",)
    assert "enableDynamicPayloads" in hechas


def test_enviar_y_recibir(radio):
    assert radio.send(b"hola")
    assert radio.reintentos_hw == 2
    radio._r.rx.append(b"\xC0\x00\x01\x00")
    assert radio.receive(0.1) == b"\xC0\x00\x01\x00"
    assert radio._r.escuchando
    assert radio.receive(0.01) is None
    radio.send(b"x")
    assert not radio._r.escuchando           # volvio a modo TX


def test_trama_demasiado_larga(radio):
    with pytest.raises(ValueError):
        radio.send(bytes(33))
