"""Boton, selector y LEDs con los pines simulados de gpiozero (MockFactory)."""
import threading
import time

import pytest

gpiozero = pytest.importorskip("gpiozero")
from gpiozero import Device
from gpiozero.pins.mock import MockFactory

from ie0527.hardware.gpio import PIN_BOTON, PIN_MODO, PINES_LED, PanelGPIO


@pytest.fixture
def panel():
    Device.pin_factory = MockFactory()
    p = PanelGPIO()
    yield p
    Device.pin_factory.reset()


def _pin(numero):
    return Device.pin_factory.pin(numero)


# Verifica la correspondencia entre nivel del selector y modo de compresión.
def test_selector_decide_el_modo(panel):
    _pin(PIN_MODO).drive_high()                    # abierto / arriba
    assert panel.modo_con_perdidas() is False      # RLE
    _pin(PIN_MODO).drive_low()                     # cerrado / abajo
    assert panel.modo_con_perdidas() is True       # DCT


# Verifica la actualización del LED asociado al modo.
def test_led_de_modo_sigue_al_selector(panel):
    _pin(PIN_MODO).drive_high()
    panel.seguir_modo(0)
    assert _pin(PINES_LED[0]).state == 0
    _pin(PIN_MODO).drive_low()
    time.sleep(0.1)                                # antirrebote
    assert _pin(PINES_LED[0]).state == 1
    panel.led(2, True)
    panel.apagar_todo()                            # apaga todo menos el de modo
    assert _pin(PINES_LED[2]).state == 0 and _pin(PINES_LED[0]).state == 1


# Comprueba que un botón sostenido no desencadena una segunda transferencia.
def test_boton_inicia_y_no_repite_si_queda_presionado(panel):
    boton = _pin(PIN_BOTON)
    boton.drive_high()
    listo = threading.Event()
    hilo = threading.Thread(target=lambda: (panel.esperar_boton(), listo.set()))
    hilo.start()
    time.sleep(0.1)
    assert not listo.is_set()
    boton.drive_low()                              # pulsacion
    assert listo.wait(1)
    # Sigue presionado: la siguiente espera no debe dispararse hasta soltar y pulsar
    listo.clear()
    hilo = threading.Thread(target=lambda: (panel.esperar_boton(), listo.set()))
    hilo.start()
    time.sleep(0.2)
    assert not listo.is_set()
    boton.drive_high(); time.sleep(0.1); boton.drive_low()
    assert listo.wait(1)
