# Protocolo propuesto (versión inicial)

Sigue la sección 7.6 del anteproyecto y aún no ha sido probado sobre radio real.

- Cada trama tiene longitud máxima de 32 bytes.
- Encabezado de 2 bytes big-endian: 2 bits de tipo y 14 de secuencia.
- Tipos: 0 INICIO, 1 DATOS, 2 FIN, 3 RESPUESTA.
- DATOS: secuencias 1..N, hasta 30 bytes de datos útiles.
- INICIO: 32 bytes: encabezado(2), sesion(1), grupo(1), modo+Q(1), ancho(2), alto(2), profundidad(1), longitud comprimida(4), longitud original(4), num paquetes(2), CRC32 comprimido(4), CRC32 original(4), pre_inicio_ms(4).
- Modo byte: 0=RLE sin pérdidas; 0x80|Q=DCT con pérdidas, Q entre 1 y 100.
- FIN: encabezado(2), sesion(1), CRC32 comprimido(4), reintentos contabilizados(2).
- RESPUESTA: encabezado(2), sesion(1), estado(1), hasta 14 secuencias faltantes (2 c/u).
- Los enteros se codifican en orden big-endian.
- CRC16, ACK y retransmisiones del chip no se simulan aquí.

## Puntos a definir antes de las pruebas RF

1. Qué hacer con más de 14 secuencias faltantes (respuesta por lotes).
2. Cómo manejar pérdidas de INICIO, FIN y RESPUESTA, con id de sesion.
3. Cómo sincronizar respuestas de la aplicación con auto-ACK de hardware (son diferentes).
4. Qué se considera retransmisión y qué bytes son de aplicación vs físicos.
5. Cómo transportar tiempos del TX no incluidos en los 32 bytes de INICIO y los 9 bytes de FIN; la versión inicial necesita extensión del protocolo o combinación de registros TX/RX.
6. El flujo no incluye nombre de archivo; el receptor usa un nombre generado por sesión.
7. Definir tiempos de espera y recuperación al abortar.

## Decisiones de implementación (`src/ie0527/link.py`)

Resuelven los puntos anteriores. Están probadas con el canal simulado (`tests/test_link.py`); falta validarlas con el radio real.

1. **Más de 14 faltantes:** el TX sabe qué tramas no recibieron ACK y las repite hasta 3 pasadas antes de enviar FIN. Si aun así faltan, la RESPUESTA pide las primeras 14, el TX las reenvía, repite FIN y el RX pide el siguiente lote, hasta que responde OK.
2. **Pérdida de INICIO, FIN o RESPUESTA:** INICIO y RESPUESTA tienen hasta 10 intentos de aplicación (cada uno con los 15 del chip). FIN se repite hasta 5 veces si no llega RESPUESTA en 50 ms. El RX descarta DATOS que lleguen sin INICIO y aborta si pasan 2 s sin tramas a mitad de una transferencia.
3. **ACK del chip y RESPUESTA:** conviven. El ACK confirma cada trama; la RESPUESTA confirma la transferencia completa. El RX recuerda la última sesión completada y contesta OK de nuevo si el TX repite FIN porque no vio el primer OK.
4. **Retransmisiones:** se cuentan dos tipos: las del chip (suma de ARC) y las de aplicación. FIN lleva la suma de ambas. Los bytes de aplicación incluyen encabezados y todas las retransmisiones de aplicación; los del chip (preámbulo, dirección, CRC16) se reportan aparte.
5. **Tiempos del TX:** INICIO lleva en `pre_start_ms` el tiempo desde que se pulsa el botón hasta armar INICIO (incluye lectura y compresión). El RX suma ese valor, su tiempo de transmisión y su tiempo de descompresión para el tiempo total.
6. **Nombre de archivo:** el RX guarda `data/salida/sesionNNN_modo.pgm` y reconoce la imagen original por el CRC32 de sus píxeles para calcular PSNR y BER.
7. **Tiempos de espera:** 50 ms para RESPUESTA, 2 s de inactividad en el RX, 30 tramas DATOS seguidas sin ACK declaran el enlace caído. Todos se ajustan en `ConfigEnlace`.

**Direcciones:** cada nodo escucha en su propia dirección de 5 bytes (tubería 1) y transmite a la del otro: `TXG<grupo>\xA5` y `RXG<grupo>\xA5`. La carga útil es dinámica (1 a 32 bytes) porque FIN y RESPUESTA miden menos de 32.
