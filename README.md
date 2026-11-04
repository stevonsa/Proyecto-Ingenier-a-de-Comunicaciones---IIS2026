# IE0527 – Transmisión Inalámbrica de Imágenes

**Universidad de Costa Rica**  
Escuela de Ingeniería Eléctrica  
IE0527 – Ingeniería de Comunicaciones  
II Semestre 2026

## Descripción

Desarrollo de un sistema portátil capaz de transmitir imágenes digitales en escala de grises mediante un enlace inalámbrico, utilizando técnicas de codificación de fuente.

El sistema incorporará dos modalidades:

- **Codificación sin pérdidas:** recuperación idéntica de la imagen original.
- **Codificación con pérdidas:** reducción del volumen de información mediante degradación controlada.

## Objetivos

1. Diseñar e implementar un transmisor y un receptor inalámbricos.
2. Implementar algoritmos de compresión y descompresión de imágenes.
3. Desarrollar un protocolo de comunicación para el intercambio de datos.
4. Evaluar los tiempos de transmisión, las razones de compresión y la calidad de las imágenes reconstruidas.
5. Comparar el desempeño de los distintos esquemas de codificación.

## Requisitos principales

- Imágenes BMP o PGM en escala de grises, de hasta 320 × 240 píxeles.
- Comunicación inalámbrica mediante módulos de bajo nivel.
- Modos de compresión con pérdidas y sin pérdidas.
- Operación autónoma del transmisor y del receptor.
- Reconstrucción y visualización de imágenes recibidas.
- Evaluación experimental a 30 metros con línea de vista.

## Tecnologías

- Lenguaje de programación: Python.
- Plataforma de hardware: por definir.
- Módulo de comunicación: por definir.
- Algoritmos de compresión: por definir.

## Organización

El repositorio se divide en módulos de transmisión, recepción, codificación de fuente, comunicación inalámbrica y evaluación de desempeño.

La documentación académica se almacena en `docs/`.

## Integrantes

| Integrante | Responsabilidad |
|---|---|
| Integrante 1 | Liderazgo |
| Integrante 2 | Supervisión técnica |
| Integrante 3 | Supervisión de comunicación |
| Otros integrantes | Desarrollo y documentación |

## Estado

Proyecto en desarrollo.

## Referencias

Escenario hipotético: *Proyecto Integrador – Transmisión inalámbrica de imágenes con codificación de fuente*, IE0527, Universidad de Costa Rica.