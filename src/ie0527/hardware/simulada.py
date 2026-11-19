"""Par de radios en memoria para probar el control de enlace sin hardware.

Modela lo que el control de enlace ve del nRF24 despues de sus reintentos:
  - perdida:     la trama no llega aunque el chip reintente (send -> False)
  - perdida_ack: la trama llega pero el ACK se pierde (send -> False y el
                 receptor la tiene: provoca duplicados)
Los tiempos no son reales; solo sirve para validar la logica.
"""
import queue
import random
import threading
from typing import Optional


class CanalSimulado:
    def __init__(self, perdida: float = 0.0, perdida_ack: float = 0.0, semilla: int = 0):
        if not (0 <= perdida < 1 and 0 <= perdida_ack < 1):
            raise ValueError("Probabilidades fuera de rango")
        self.perdida = perdida
        self.perdida_ack = perdida_ack
        self._rng = random.Random(semilla)
        self._lock = threading.Lock()
        self._colas = (queue.Queue(), queue.Queue())
        self.activo = [True, True]
        self.tx = RadioSimulada(self, 0)
        self.rx = RadioSimulada(self, 1)

    def _transmitir(self, origen: int, frame: bytes) -> bool:
        destino = 1 - origen
        if not self.activo[destino]:
            return False
        with self._lock:
            se_pierde = self._rng.random() < self.perdida
            sin_ack = self._rng.random() < self.perdida_ack
        if se_pierde:
            return False
        self._colas[destino].put(bytes(frame))
        return not sin_ack


class RadioSimulada:
    def __init__(self, canal: CanalSimulado, lado: int):
        self._canal = canal
        self._lado = lado
        self.reintentos_hw = 0
        self.tramas_fallidas_hw = 0

    def send(self, frame: bytes) -> bool:
        if not 1 <= len(frame) <= 32:
            raise ValueError("La trama debe tener de 1 a 32 bytes")
        ok = self._canal._transmitir(self._lado, frame)
        if not ok:
            self.reintentos_hw += 15
            self.tramas_fallidas_hw += 1
        return ok

    def receive(self, timeout_s: Optional[float] = None) -> Optional[bytes]:
        try:
            return self._canal._colas[self._lado].get(timeout=timeout_s)
        except queue.Empty:
            return None

    def vaciar(self) -> None:
        cola = self._canal._colas[self._lado]
        while True:
            try:
                cola.get_nowait()
            except queue.Empty:
                return

    def canal_ocupado(self) -> bool:
        return False
