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
