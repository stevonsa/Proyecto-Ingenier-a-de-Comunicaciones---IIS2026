"""Control de enlace de extremo a extremo (secciones 6.2, 6.3, 7.4, 7.5, 10.3, 10.4).

Nivel 1 (chip): CRC16 + ACK + 15 reintentos por trama, lo hace el nRF24.
Nivel 2 (este modulo):
  TX: escucha previa -> INICIO -> DATOS 1..N -> FIN -> espera RESPUESTA.
      Si la RESPUESTA trae faltantes, reenvia solo esas tramas y repite FIN.
      Si trae CRC_ERROR, reenvia todo. Si un tramo de tramas seguidas falla,
      declara el enlace caido.
  RX: escucha permanente; INICIO crea el reensamblador; descarta duplicados;
      en FIN responde OK, MISSING (hasta 14 secuencias) o CRC_ERROR.
      Si pasan 2 s sin tramas a mitad de transferencia, aborta y vuelve a
      escuchar. Recuerda la ultima sesion completada para contestar OK a un
      FIN repetido si el TX no recibio la primera RESPUESTA.
Solo usa la interfaz RadioPort (send/receive), asi corre igual con el radio
real (Nrf24Radio) o con el simulado (CanalSimulado).
"""
from dataclasses import dataclass, field
import random
import time
from typing import Callable, Optional

from ie0527.protocol import (
    START, DATA, END, REPLY, OK, MISSING, CRC_ERROR,
    StartFrame, Reassembler, frame_type, frame_seq, split_data,
    pack_end, unpack_end, pack_reply, unpack_reply,
)

MAX_FALTANTES_POR_RESPUESTA = 14


@dataclass
class ConfigEnlace:
    intentos_trama: int = 3            # intentos de aplicacion por trama DATOS/FIN (cada uno con 15 del chip)
    intentos_control: int = 10         # intentos para INICIO y RESPUESTA, que son criticas
    max_fallos_seguidos: int = 30      # tramas DATOS seguidas sin ACK -> enlace caido
    pasadas_extra: int = 3             # pasadas extra sobre las tramas sin ACK antes de FIN
    espera_respuesta_s: float = 0.05   # espera de RESPUESTA tras FIN (seccion 7.5)
    intentos_fin: int = 5              # veces que se repite FIN sin RESPUESTA
    max_rondas: int = 40               # rondas FIN/faltantes antes de rendirse
    inactividad_rx_s: float = 2.0      # RX aborta si no llega nada en este tiempo
    escucha_previa_intentos: int = 10  # CSMA no persistente al inicio (seccion 7.4)


class EnlaceCaido(Exception):
    """El transmisor no logra completar la transferencia."""


@dataclass
class EstadisticasTX:
    tramas_enviadas: int = 0
    bytes_enviados: int = 0          # capa de aplicacion, con encabezados y reenvios
    retransmisiones_app: int = 0     # reenvios hechos por este modulo
    tramas_reenviadas_por_faltantes: int = 0   # por falta de ACK o pedidas en RESPUESTA
    rondas_fin: int = 0
    canal_ocupado_detectado: int = 0
    reintentos_hw: int = 0           # reintentos del chip en esta transferencia
    segundos_transmision: float = 0.0
    _base_hw: int = field(default=0, repr=False)

    def actualizar_hw(self, radio) -> None:
        self.reintentos_hw = getattr(radio, "reintentos_hw", 0) - self._base_hw


@dataclass
class ResultadoRX:
    meta: StartFrame
    datos: bytes
    segundos_transmision: float      # de INICIO recibido a OK enviado
    reintentos_tx: int               # informados por el TX en FIN
    tramas_recibidas: int            # todas, incluidas duplicadas
    bytes_recibidos: int             # capa de aplicacion
    duplicadas: int
    rondas_fin: int
    errores_crc32: int = 0


def _tipo(frame: bytes) -> Optional[int]:
    try:
        return frame_type(frame)
    except ValueError:
        return None


def _enviar(radio, frame: bytes, cfg: ConfigEnlace, stats: Optional[EstadisticasTX] = None,
            intentos: Optional[int] = None) -> bool:
    for intento in range(intentos or cfg.intentos_trama):
        if stats is not None:
            stats.tramas_enviadas += 1
            stats.bytes_enviados += len(frame)
            if intento:
                stats.retransmisiones_app += 1
        if radio.send(frame):
            return True
    return False


def _escucha_previa(radio, cfg: ConfigEnlace, stats: EstadisticasTX, rng: random.Random) -> None:
    ocupado = getattr(radio, "canal_ocupado", None)
    if ocupado is None:
        return
    for _ in range(cfg.escucha_previa_intentos):
        if not ocupado():
            return
        stats.canal_ocupado_detectado += 1
        time.sleep(rng.uniform(0.005, 0.05))  # retardo aleatorio (no persistente)
    # Si sigue ocupado se transmite igual: el ARQ se encarga de las perdidas.


def _cerrar(radio, meta: StartFrame, cfg: ConfigEnlace, stats: EstadisticasTX):
    """Envia FIN y espera la RESPUESTA. Devuelve (estado, faltantes) o None."""
    vaciar = getattr(radio, "vaciar", None)
    for _ in range(cfg.intentos_fin):
        if vaciar:
            vaciar()                      # descarta RESPUESTAS viejas o duplicadas
        stats.actualizar_hw(radio)
        reintentos = stats.retransmisiones_app + stats.reintentos_hw
        fin = pack_end(meta.session, meta.crc_compressed, min(reintentos, 0xFFFF))
        stats.rondas_fin += 1
        if not _enviar(radio, fin, cfg, stats):
            continue
        limite = time.perf_counter() + cfg.espera_respuesta_s
        while (resto := limite - time.perf_counter()) > 0:
            frame = radio.receive(resto)
            if frame is None or _tipo(frame) != REPLY:
                continue
            try:
                sesion, estado, faltantes = unpack_reply(frame)
            except ValueError:
                continue
            if sesion == meta.session:
                return estado, faltantes
    return None


def enviar_imagen(radio, meta: StartFrame, datos: bytes,
                  cfg: Optional[ConfigEnlace] = None, semilla: Optional[int] = None) -> EstadisticasTX:
    """Transmite los datos comprimidos. Lanza EnlaceCaido si no lo logra."""
    cfg = cfg or ConfigEnlace()
    tramas = split_data(datos)
    if len(tramas) != meta.total_frames or len(datos) != meta.compressed_length:
        raise ValueError("Los metadatos no coinciden con los datos")
    stats = EstadisticasTX(_base_hw=getattr(radio, "reintentos_hw", 0))
    inicio = time.perf_counter()
    _escucha_previa(radio, cfg, stats, random.Random(semilla))

    if not _enviar(radio, meta.pack(), cfg, stats, cfg.intentos_control):
        raise EnlaceCaido("No se pudo entregar INICIO: el receptor no responde")

    pendientes = list(range(1, len(tramas) + 1))
    primera = True
    for _ in range(cfg.max_rondas):
        # El TX sabe que tramas no recibieron ACK: las repite antes de FIN, asi la
        # RESPUESTA solo tiene que cubrir lo raro (limite de 14 por RESPUESTA).
        for pasada in range(1 + cfg.pasadas_extra):
            fallidas, fallos_seguidos = [], 0
            for seq in pendientes:
                if not primera or pasada:
                    stats.tramas_reenviadas_por_faltantes += 1
                if _enviar(radio, tramas[seq - 1], cfg, stats):
                    fallos_seguidos = 0
                else:
                    fallidas.append(seq)
                    fallos_seguidos += 1
                    if fallos_seguidos >= cfg.max_fallos_seguidos:
                        raise EnlaceCaido(f"{fallos_seguidos} tramas seguidas sin ACK")
            if not fallidas:
                break
            pendientes = fallidas
        primera = False
        respuesta = _cerrar(radio, meta, cfg, stats)
        if respuesta is None:
            raise EnlaceCaido("Sin RESPUESTA del receptor tras FIN")
        estado, faltantes = respuesta
        if estado == OK:
            stats.segundos_transmision = time.perf_counter() - inicio
            stats.actualizar_hw(radio)
            return stats
        if estado == MISSING and faltantes:
            pendientes = faltantes
        elif estado == CRC_ERROR:
            pendientes = list(range(1, len(tramas) + 1))
        else:
            raise EnlaceCaido(f"RESPUESTA con estado inesperado {estado}")
    raise EnlaceCaido("Se agotaron las rondas de reenvio")


class TransferenciaAbortada(Exception):
    """El receptor dejo de recibir tramas a mitad de una transferencia."""


@dataclass
class Receptor:
    radio: object
    cfg: ConfigEnlace = field(default_factory=ConfigEnlace)
    al_iniciar: Optional[Callable[[StartFrame], None]] = None
    _ultima: Optional[tuple[int, int]] = None   # (sesion, crc) completada

    def _responder(self, sesion: int, estado: int, faltantes: Optional[list[int]] = None) -> None:
        _enviar(self.radio, pack_reply(sesion, estado, faltantes), self.cfg,
                intentos=self.cfg.intentos_control)

    def _esperar_inicio(self, esperar_s: Optional[float]) -> Optional[StartFrame]:
        limite = None if esperar_s is None else time.perf_counter() + esperar_s
        while True:
            resto = None if limite is None else limite - time.perf_counter()
            if resto is not None and resto <= 0:
                return None
            frame = self.radio.receive(resto)
            if frame is None:
                continue
            tipo = _tipo(frame)
            if tipo == START:
                try:
                    meta = StartFrame.unpack(frame)
                except ValueError:
                    continue
                if self._ultima and (meta.session, meta.crc_compressed) == self._ultima:
                    continue              # INICIO repetido de una sesion ya completada
                return meta
            if tipo == END and self._ultima:
                try:
                    sesion, crc, _ = unpack_end(frame)
                except ValueError:
                    continue
                if (sesion, crc) == self._ultima:
                    self._responder(sesion, OK)   # el TX no recibio el primer OK

    def recibir(self, esperar_s: Optional[float] = None) -> Optional[ResultadoRX]:
        """Espera una transferencia completa. None si vence esperar_s sin INICIO.

        Lanza TransferenciaAbortada si la transferencia se interrumpe.
        """
        meta = self._esperar_inicio(esperar_s)
        if meta is None:
            return None
        if self.al_iniciar:
            self.al_iniciar(meta)
        t0 = time.perf_counter()
        rx = Reassembler(meta)
        recibidas, bytes_rx, duplicadas, rondas, errores_crc = 1, 32, 0, 0, 0
        while True:
            frame = self.radio.receive(self.cfg.inactividad_rx_s)
            if frame is None:
                raise TransferenciaAbortada(
                    f"Sin tramas por {self.cfg.inactividad_rx_s} s; faltaban {len(rx.missing())}")
            recibidas += 1
            bytes_rx += len(frame)
            tipo = _tipo(frame)
            if tipo == DATA:
                if frame_seq(frame) in rx.packets:
                    duplicadas += 1
                try:
                    rx.add(frame)
                except ValueError:
                    pass                  # fuera de rango o contradictoria: se ignora
            elif tipo == START:
                try:
                    nueva = StartFrame.unpack(frame)
                except ValueError:
                    continue
                if nueva == meta:
                    duplicadas += 1
                    continue
                meta, rx, t0 = nueva, Reassembler(nueva), time.perf_counter()  # sesion nueva
                recibidas, bytes_rx, duplicadas, rondas, errores_crc = 1, len(frame), 0, 0, 0
                if self.al_iniciar:
                    self.al_iniciar(meta)
            elif tipo == END:
                try:
                    sesion, crc, reintentos = unpack_end(frame)
                except ValueError:
                    continue
                if sesion != meta.session or crc != meta.crc_compressed:
                    continue
                rondas += 1
                faltantes = rx.missing()
                if faltantes:
                    self._responder(sesion, MISSING, faltantes[:MAX_FALTANTES_POR_RESPUESTA])
                    continue
                try:
                    datos = rx.reconstruct()
                except ValueError:
                    errores_crc += 1
                    rx.packets.clear()
                    self._responder(sesion, CRC_ERROR)
                    continue
                self._responder(sesion, OK)
                self._ultima = (sesion, crc)
                return ResultadoRX(meta, datos, time.perf_counter() - t0, reintentos,
                                   recibidas, bytes_rx, duplicadas, rondas, errores_crc)
