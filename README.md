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

- Lenguaje de programación: Python 3.
- Plataforma de hardware: Raspberry Pi Zero 2 W con Raspberry Pi OS Lite 64 bits (Trixie).
- Módulo de comunicación: nRF24L01 con antena externa por SPI (pyRF24), canal 80, 2 Mbps.
- Algoritmos de compresión: RLE (sin pérdidas) y DCT 8×8 con factor de calidad Q (con pérdidas).

## Uso

### En la PC (sin radio)

```bash
pip install -e ".[dev]"
pytest                                                  # todas las pruebas
python apps/simular.py data/entrada/01_fotografica.bmp --modo dct --q 50
python apps/simular_enlace.py data/entrada/01_fotografica.bmp --modo rle --perdida 0.1
```

`simular_enlace.py` corre el transmisor y el receptor completos con un canal simulado con pérdidas.

### En las Raspberry Pi

Una vez por Raspberry (con el SPI habilitado):

```bash
sudo apt install -y python3-numpy python3-pil python3-gpiozero python3-lgpio python3-venv git
python3 -m venv --system-site-packages ~/venv
git clone https://github.com/stevonsa/Proyecto-Ingenier-a-de-Comunicaciones---IIS2026.git proyecto
cd proyecto
~/venv/bin/pip install -e ".[rpi,dev]"
~/venv/bin/python -m pytest -q
```

El venv **debe** crearse con `--system-site-packages`: gpiozero y su controlador `lgpio` vienen del sistema (apt). Si gpiozero muestra avisos *"Falling back from lgpio"* o falla al leer el botón, revisar que `~/venv/pyvenv.cfg` diga `include-system-site-packages = true` y quitar la copia de pip con `~/venv/bin/pip uninstall -y gpiozero`.

Receptor (primero):

```bash
~/venv/bin/python apps/receptor.py --referencias data/entrada --gpio
```

Transmisor:

```bash
~/venv/bin/python apps/transmisor.py data/entrada/01_fotografica.bmp --modo rle
~/venv/bin/python apps/transmisor.py data/entrada/01_fotografica.bmp --modo dct --q 50
```

- `--gpio` usa botón, selector y LEDs; sin él, se transmite con Enter.
- `--potencia low` (por defecto) para pruebas en la mesa a 1–2 m; `--potencia max` para la prueba de 30 m.
- `--mostrar` en el receptor despliega la imagen y las métricas en el monitor HDMI: dibuja directo en el framebuffer (`/dev/fb0`), sin paquetes extra.
- El receptor guarda cada imagen y agrega una fila a `data/salida/metricas.csv`.

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