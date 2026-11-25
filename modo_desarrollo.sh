# Prueba a 30 m en modo autónomo

Lista de pasos para la prueba de evaluación: sin computadora, sin internet ni Bluetooth, manejada solo con el botón y el selector.

## 1. Antes de salir (en la mesa, con WiFi)

1. Actualizar el código en las dos Raspberry: `cd ~/proyecto && git pull`.
2. **Probar potencia máxima en la mesa** (radios a 2–3 m): en la RX `~/venv/bin/python apps/receptor.py --referencias data/entrada --gpio --potencia max`; en la TX `~/venv/bin/python apps/transmisor.py data/entrada --gpio --bucle --potencia max`. Enviar las 3 imágenes en los dos modos. Si aparecen `tramas seguidas sin ACK` o el radio deja de responder solo con `max`, la alimentación desde el pin 1 no alcanza: pasar al regulador de 3,3 V desde el pin 2.
3. Copiar las 3 imágenes de prueba a la memoria USB (raíz, formato FAT32 o exFAT).
4. Instalar el modo autónomo:
   - En la TX: `sudo bash scripts/instalar_servicio.sh tx`
   - En la RX: `sudo bash scripts/instalar_servicio.sh rx`
5. `sudo reboot` en las dos. Desde aquí ya no hay WiFi ni SSH.
6. Verificar en la mesa que todo arranca solo: LED de espera en la RX, pantalla con "Esperando imagen...", LED de modo de la TX siguiendo al selector, y una transmisión con el botón.

## 2. En el sitio

| Elemento | Condición |
| --- | --- |
| Distancia | 30 m medidos con cinta entre antenas |
| Línea vista | sin obstáculos entre las antenas |
| Altura de antenas | 1 m o más (zona de Fresnel de 0,97 m) |
| Orientación | antenas verticales y paralelas |
| Alimentación | powerbank cargada en cada Raspberry; monitor de la RX a la corriente |

1. Encender primero la RX y esperar el LED de espera (unos 40 s).
2. Encender la TX con la memoria USB conectada.
3. Selector arriba (sin pérdidas): pulsar el botón una vez por imagen (3 pulsaciones).
4. Selector abajo (con pérdidas): repetir las 3 pulsaciones.
5. Si una transmisión falla (LED de error parpadeando), esperar 5 min y volver a pulsar: el transmisor repite **la misma imagen**. Máximo 3 intentos por imagen; anotar todos.

LEDs de la TX: 1 = modo con pérdidas · 2 = transmitiendo · 3 = fin correcto · 4 = error.
LEDs de la RX: 1 = esperando · 2 = recibiendo · 3 = fin correcto · 4 = error.

## 3. Registro

Por cada intento: fecha y hora, imagen, modo, resultado (LED de fin o error) y una foto del monitor de la RX con las métricas. La RX guarda además la imagen y una fila en `data/salida/metricas.csv`.

Sin internet el reloj de la Raspberry no se sincroniza: la columna `fecha_hora` del CSV puede estar corrida; usar la hora anotada a mano.

## 4. Al terminar

Con teclado y monitor en cada Raspberry: `sudo bash ~/proyecto/scripts/modo_desarrollo.sh`. Esto detiene el modo autónomo y enciende el WiFi. Después, desde la laptop:

```
scp comu2@<IP de la RX>:~/proyecto/data/salida/metricas.csv .
```
