"""Acceso al radio nRF24L01(+) con pyRF24 (seccion 10.1 del anteproyecto).

El resto del sistema solo usa la interfaz RadioPort (send/receive), asi el
control de enlace se puede probar en PC con RadioSimulada (simulada.py) y
correr sin cambios en la Raspberry Pi con Nrf24Radio.

Configuracion (secciones 7.2 a 7.5):
  CE = GPIO22, CSN = SPI0 CE0 (GPIO8), canal 80 (2480 MHz), 2 Mbps,
  CRC16, auto-ACK, ARC = 15 reintentos, ARD = 500 us, carga util dinamica.
Cada nodo escucha en su propia direccion (tuberia 1) y transmite a la del
otro nodo; las direcciones de 5 bytes llevan el numero de grupo.
"""
import time
from typing import Optional, Protocol

MAX_FRAME = 32


class RadioPort(Protocol):
    def send(self, frame: bytes) -> bool:
        """Devuelve True si el radio confirma el envio (ACK). Max 32 bytes."""
        ...

    def receive(self, timeout_s: Optional[float] = None) -> Optional[bytes]:
        """Devuelve una trama recibida o None al vencer el timeout."""
        ...


def direcciones(grupo: int) -> tuple[bytes, bytes]:
    """Direcciones (transmisor, receptor) de 5 bytes para un grupo 0..255."""
    if not 0 <= grupo <= 255:
        raise ValueError("Grupo fuera de rango")
    return b"TXG" + bytes([grupo]) + b"\xA5", b"RXG" + bytes([grupo]) + b"\xA5"


class Nrf24Radio:
    """Radio real. Requiere pyrf24 y el SPI habilitado (raspi-config)."""

    def __init__(self, propia: bytes, destino: bytes, *, ce_pin: int = 22, csn: int = 0,
                 canal: int = 80, tasa: str = "2M", potencia: str = "low",
                 retardo_ard: int = 1, reintentos_arc: int = 15):
        import pyrf24 as rf

        if len(propia) != 5 or len(destino) != 5:
            raise ValueError("Las direcciones deben tener 5 bytes")
        tasas = {"2M": rf.RF24_2MBPS, "1M": rf.RF24_1MBPS, "250K": rf.RF24_250KBPS}
        potencias = {"min": rf.RF24_PA_MIN, "low": rf.RF24_PA_LOW,
                     "high": rf.RF24_PA_HIGH, "max": rf.RF24_PA_MAX}
        self._r = rf.RF24(ce_pin, csn)
        if not self._r.begin():
            raise RuntimeError("El nRF24L01 no responde: revisar cableado, 3,3 V y SPI")
        self.version_plus = bool(self._r.isPVariant())
        if tasa == "250K" and not self.version_plus:
            raise ValueError("250 kbps solo existe en el nRF24L01+")
        r = self._r
        r.setChannel(canal)
        r.setDataRate(tasas[tasa])
        r.setPALevel(potencias[potencia])
        r.setCRCLength(rf.RF24_CRC_16)
        r.setAutoAck(True)
        r.enableDynamicPayloads()        # FIN y RESPUESTA miden menos de 32 bytes
        r.setRetries(retardo_ard, reintentos_arc)  # ARD = (retardo+1)*250 us
        r.openReadingPipe(1, propia)
        self._destino = destino
        r.stopListening(destino)         # modo TX con la direccion del otro nodo
        r.flush_rx()
        r.flush_tx()
        self._escuchando = False
        self.reintentos_hw = 0           # suma de ARC de todas las tramas
        self.tramas_fallidas_hw = 0      # tramas que agotaron los 15 reintentos

    def send(self, frame: bytes) -> bool:
        if not 1 <= len(frame) <= MAX_FRAME:
            raise ValueError("La trama debe tener de 1 a 32 bytes")
        if self._escuchando:
            self._r.stopListening(self._destino)
            self._escuchando = False
        ok = bool(self._r.write(frame))
        self.reintentos_hw += self._r.getARC()
        if not ok:
            self.tramas_fallidas_hw += 1
            self._r.flush_tx()
        return ok

    def receive(self, timeout_s: Optional[float] = None) -> Optional[bytes]:
        if not self._escuchando:
            self._r.startListening()
            self._escuchando = True
        limite = None if timeout_s is None else time.perf_counter() + timeout_s
        while True:
            if self._r.available():
                largo = self._r.getDynamicPayloadSize()
                if 1 <= largo <= MAX_FRAME:
                    return bytes(self._r.read(largo))
                self._r.flush_rx()       # largo invalido: trama corrupta
                continue
            if limite is not None and time.perf_counter() >= limite:
                return None
            time.sleep(0.0001)

    def vaciar(self) -> None:
        """Descarta tramas viejas que hayan quedado en la cola de recepcion."""
        self._r.flush_rx()

    def canal_ocupado(self) -> bool:
        """Escucha previa (seccion 7.4): True si hay portadora de mas de -64 dBm."""
        if not self._escuchando:
            self._r.startListening()
            self._escuchando = True
        time.sleep(0.0003)               # el detector necesita unos 170 us en RX
        return bool(self._r.testRPD())

    def close(self) -> None:
        self._r.powerDown()
