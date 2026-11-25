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


# Canal bidireccional en memoria con colas, pérdida de tramas y pérdida independiente de
# ACK.
class CanalSimulado:
    # Crea dos extremos y un generador pseudoaleatorio protegido por un bloqueo.
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

    # Si no se pierde la trama, la deposita en el destino incluso cuando se pierde su ACK.
    def _transmitir(self, origen: int, frame: bytes) -> bool:
        destino = 1 - origen
        if not self.activo[destino]:
            return False
        # Protege el generador compartido por los hilos TX y RX.
        with self._lock:
            se_pierde = self._rng.random() < self.perdida
            sin_ack = self._rng.random() < self.perdida_ack
        if se_pierde:
            return False
        # El dato puede llegar aunque el transmisor no reciba confirmación.
        self._colas[destino].put(bytes(frame))
        return not sin_ack


# Adaptador de un extremo del canal que reproduce la interfaz utilizada por el enlace.
class RadioSimulada:
    # Asocia el extremo a su cola y empieza los contadores simulados en cero.
    def __init__(self, canal: CanalSimulado, lado: int):
        self._canal = canal
        self._lado = lado
        self.reintentos_hw = 0
        self.tramas_fallidas_hw = 0

    # Entrega una trama al canal y contabiliza 15 reintentos simulados cuando no se
    # confirma.
    def send(self, frame: bytes) -> bool:
        if not 1 <= len(frame) <= 32:
            raise ValueError("La trama debe tener de 1 a 32 bytes")
        ok = self._canal._transmitir(self._lado, frame)
        if not ok:
            self.reintentos_hw += 15
            self.tramas_fallidas_hw += 1
        return ok

    # Extrae una trama de la cola local o devuelve None si vence la espera.
    def receive(self, timeout_s: Optional[float] = None) -> Optional[bytes]:
        try:
            return self._canal._colas[self._lado].get(timeout=timeout_s)
        except queue.Empty:
            return None

    # Descarta todas las tramas que ya están en la cola de recepción.
    def vaciar(self) -> None:
        cola = self._canal._colas[self._lado]
        while True:
            try:
                cola.get_nowait()
            except queue.Empty:
                return

    # Devuelve False: el modelo no simula detección física de portadora.
    def canal_ocupado(self) -> bool:
        return False
