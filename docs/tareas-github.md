# Issues iniciales sugeridas

## Sprint 1 — software sin radio

- [ ] `feat: lector y validador BMP/PGM` — aceptar solo L (gris 8-bit), max 320x240, errores claros.
- [ ] `feat: codec RLE` — recuperacion exacta para 3 imagenes y runs >255.
- [ ] `feat: codec DCT` — bloques 8x8, Q=90/50/25/10, reconstruccion, graficas preliminares.
- [ ] `feat: formato de tramas` — INICIO 32 bytes, DATOS <=32, FIN y RESPUESTA, prueba de CRC32.
- [ ] `test: transferencia offline` — simulacion completa y tests de casos malformados.

## Sprint 2 — hardware e integracion

- [ ] `feat: controlador pyRF24` — 2 Raspberry Pi Zero, SPI, CE22/CSN8, canal 80, tasa 2 Mbps.
- [ ] `feat: transmision de tramas` — reintentos, ACK, timeout, cuenta bytes y reintentos.
- [ ] `feat: receptor asincrono` — escucha permanente, duplicados, faltantes, CRC32.
- [ ] `feat: GPIO` — boton inicio 17, modo 27, LEDs 5,6,13,19.
- [ ] `feat: salida HDMI y registro CSV` — guardar/reconstruir, mostrar y persistir metricas.
- [ ] `test: enlace 30m` — 3 imagenes, 3 intentos permitidos, <=60 s, PSNR>25.
- [ ] `docs: curva tasa-distorsion y bitacora` — mediciones reales (no simulacion).

## Propuesta para repartir (segun seccion 10.5 del anteproyecto)

- Integrante 4: RLE y verificacion de integridad.
- Integrante 5: DCT + Q + zigzag y pruebas de calidad.
- Integrante 6: protocolo/enlace con apoyo de supervision tecnica.
- Supervision tecnica: fijar formatos e integracion hardware.
- Supervision de comunicacion: README, bitacora, pruebas documentadas,
  CSV y evidencias de demostracion, sin excluir participacion tecnica.
