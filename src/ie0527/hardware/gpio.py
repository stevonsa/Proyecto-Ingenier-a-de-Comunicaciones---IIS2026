"""Boton, selector de modo y LEDs (Cuadro de conexiones, seccion 10.1).

  Boton de inicio  GPIO17 (pin 11)  a GND, pull-up interno
  Selector de modo GPIO27 (pin 13)  SPDT entre 3V3 y GND:
                                    arriba (alto) = sin perdidas (RLE)
                                    abajo (bajo)  = con perdidas (DCT)
  LEDs             GPIO5, GPIO6, GPIO13, GPIO19 (pines 29, 31, 33, 35), 220 ohm
Si gpiozero no esta disponible (por ejemplo en una PC) o no se pide GPIO,
se usa PanelNulo, que no hace nada, y el programa funciona igual.
"""
PIN_BOTON = 17
PIN_MODO = 27
PINES_LED = (5, 6, 13, 19)


class PanelNulo:
    def led(self, indice: int, encendido: bool) -> None:
        pass

    def parpadear(self, indice: int) -> None:
        pass

    def apagar_todo(self) -> None:
        pass

    def esperar_boton(self) -> None:
        input("Presione Enter para transmitir...")

    def modo_con_perdidas(self) -> bool | None:
        return None


class PanelGPIO(PanelNulo):
    def __init__(self, con_boton: bool = True):
        from gpiozero import LED, Button

        self._leds = [LED(p) for p in PINES_LED]
        self._boton = Button(PIN_BOTON, pull_up=True) if con_boton else None
        # is_pressed es True con el pin en bajo (posicion "abajo" = DCT). El pull-up
        # solo mantiene un nivel definido durante el cambio de posicion del SPDT.
        self._modo = Button(PIN_MODO, pull_up=True) if con_boton else None

    def led(self, indice: int, encendido: bool) -> None:
        self._leds[indice].on() if encendido else self._leds[indice].off()

    def parpadear(self, indice: int) -> None:
        self._leds[indice].blink(on_time=0.2, off_time=0.2)

    def apagar_todo(self) -> None:
        for led in self._leds:
            led.off()

    def esperar_boton(self) -> None:
        if self._boton is None:
            return super().esperar_boton()
        self._boton.wait_for_press()

    def modo_con_perdidas(self) -> bool | None:
        return None if self._modo is None else self._modo.is_pressed


def crear_panel(usar_gpio: bool, con_boton: bool = True) -> PanelNulo:
    if not usar_gpio:
        return PanelNulo()
    try:
        return PanelGPIO(con_boton)
    except Exception as exc:  # sin gpiozero o sin permisos
        print(f"Aviso: GPIO no disponible ({exc}); se sigue sin LEDs ni boton")
        return PanelNulo()
