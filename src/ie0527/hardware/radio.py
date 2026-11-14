"""Contrato a implementar al integrar la libreria RF24 en Raspberry Pi.

No se fabrica una radio ficticia: la simulacion esta en simulator.py.
Las funciones concretas dependen de la version instalada de pyRF24 y de
la configuracion SPI/CE/CSN de las placas del laboratorio.
"""
from typing import Protocol, Optional


class RadioPort(Protocol):
    def send(self, frame: bytes) -> bool:
        """Devuelve True si el radio confirma el envio. max 32 bytes."""
        ...

    def receive(self, timeout_s: Optional[float] = None) -> Optional[bytes]:
        """Devuelve una trama recibida o None al vencer el timeout."""
        ...


class Nrf24Radio:
    """Pendiente: implementar con el hardware en laboratorio.

    Tareas:
      - radio.begin(), pin CE=GPIO22, CSN=SPI CE0/GPIO8
      - configuracion canal 80, 2Mbps, CRC16, auto-ack, ARC/ARD
      - direccion de 5 bytes identica en TX/RX (asignada al grupo)
      - controlar startListening/stopListening, IRQ opcional
      - contadores de reintentos y timeout; gestionar fallos reales
    """
    def __init__(self):
        raise NotImplementedError("Falta integrar pyRF24 en las Raspberry Pi reales")
