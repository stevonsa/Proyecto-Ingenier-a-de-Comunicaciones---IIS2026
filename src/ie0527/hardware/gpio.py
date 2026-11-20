"""Boton, selector de modo y LEDs (Cuadro de conexiones, seccion 10.1).

  Boton de inicio  GPIO17 (pin 11)  a GND, pull-up interno
  Selector de modo GPIO27 (pin 13)  a GND (o SPDT entre 3V3 y GND), pull-up interno:
                                    abierto / arriba (alto) = sin perdidas (RLE)
                                    cerrado / abajo  (bajo) = con perdidas (DCT)
  LEDs             GPIO5, GPIO6, GPIO13, GPIO19 (pines 29, 31, 33, 35), 220 ohm
Sin --gpio se usa PanelNulo (Enter en vez de boton) para probar en la mesa.
Con --gpio, si los pines no estan disponibles el programa se detiene: en modo
autonomo no hay teclado, asi que no tiene sentido seguir sin boton.
"""
PIN_BOTON = 17
PIN_MODO = 27
PINES_LED = (5, 6, 13, 19)
ANTIRREBOTE_S = 0.05


class PanelNulo:
    def led(self, indice: int, encendido: bool) -> None:
        pass

    def parpadear(self, indice: int) -> None:
        pass

    def apagar_todo(self) -> None:
        pass

    def seguir_modo(self, indice: int) -> None:
        pass

    def esperar_boton(self) -> None:
        input("Presione Enter para transmitir...")

    def modo_con_perdidas(self) -> bool | None:
        return None


class PanelGPIO(PanelNulo):
    def __init__(self, con_boton: bool = True):
        from gpiozero import LED, Button

        self._leds = [LED(p) for p in PINES_LED]
        self._boton = Button(PIN_BOTON, pull_up=True, bounce_time=ANTIRREBOTE_S) if con_boton else None
        # is_pressed es True con el pin en bajo (selector cerrado / abajo = DCT).
        self._modo = Button(PIN_MODO, pull_up=True, bounce_time=ANTIRREBOTE_S) if con_boton else None
        self._led_modo: int | None = None

    def led(self, indice: int, encendido: bool) -> None:
        self._leds[indice].on() if encendido else self._leds[indice].off()

    def parpadear(self, indice: int) -> None:
        self._leds[indice].blink(on_time=0.2, off_time=0.2)

    def _actualizar_led_modo(self) -> None:
        if self._led_modo is not None:
            self.led(self._led_modo, bool(self._modo.is_pressed))

    def seguir_modo(self, indice: int) -> None:
        """El LED indicado muestra en todo momento la posicion del selector."""
        if self._modo is None:
            return
        self._led_modo = indice
        self._modo.when_pressed = self._actualizar_led_modo
        self._modo.when_released = self._actualizar_led_modo
        self._actualizar_led_modo()

    def apagar_todo(self) -> None:
        for i, led in enumerate(self._leds):
            if i != self._led_modo:
                led.off()
        self._actualizar_led_modo()

    def esperar_boton(self) -> None:
        if self._boton is None:
            return super().esperar_boton()
        self._boton.wait_for_release()   # si quedo presionado, no dispara otra vez
        self._boton.wait_for_press()

    def modo_con_perdidas(self) -> bool | None:
        return None if self._modo is None else bool(self._modo.is_pressed)


def crear_panel(usar_gpio: bool, con_boton: bool = True) -> PanelNulo:
    if not usar_gpio:
        return PanelNulo()
    try:
        return PanelGPIO(con_boton)
    except Exception as exc:  # sin gpiozero, sin lgpio o pines ocupados
        raise RuntimeError(f"GPIO no disponible ({exc}). Revisar gpiozero/lgpio o "
                           "si otro programa usa los pines") from exc
