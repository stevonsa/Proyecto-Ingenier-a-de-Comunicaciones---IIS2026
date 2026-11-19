"""Prueba en PC del control de enlace completo, con un canal simulado con perdidas.

  python apps/simular_enlace.py data/entrada/01_fotografica.bmp --modo dct --q 50 --perdida 0.1
Corre transmisor y receptor a la vez (el receptor en un hilo) con la misma
logica que usaran las Raspberry Pi; solo cambia el radio. Los tiempos NO son
del radio real.
"""
import argparse
import json
import threading
import time
from pathlib import Path

from ie0527.evaluacion import cargar_referencias, decodificar, metricas
from ie0527.hardware.simulada import CanalSimulado
from ie0527.link import ConfigEnlace, Receptor, enviar_imagen
from ie0527.sesion import preparar


def main():
    p = argparse.ArgumentParser(description="IE0527: enlace completo simulado (sin radio)")
    p.add_argument("imagen", type=Path)
    p.add_argument("--modo", choices=["rle", "dct"], default="rle")
    p.add_argument("--q", type=int, default=50)
    p.add_argument("--perdida", type=float, default=0.05, help="prob. de perder una trama")
    p.add_argument("--perdida-ack", type=float, default=0.01, help="prob. de perder el ACK")
    p.add_argument("--semilla", type=int, default=1)
    args = p.parse_args()

    canal = CanalSimulado(args.perdida, args.perdida_ack, args.semilla)
    resultado = {}
    receptor = Receptor(canal.rx, ConfigEnlace())
    hilo = threading.Thread(target=lambda: resultado.update(res=receptor.recibir(esperar_s=10)))
    hilo.start()

    meta, datos, t_comp = preparar(args.imagen, args.modo, args.q, 7, 1, time.perf_counter())
    stats = enviar_imagen(canal.tx, meta, datos, ConfigEnlace(), semilla=args.semilla)
    hilo.join()
    res = resultado["res"]
    imagen, t_desc = decodificar(res)
    datos_rx = metricas(res, imagen, t_desc, cargar_referencias(args.imagen.parent))
    tx = {k: v for k, v in stats.__dict__.items() if not k.startswith("_")}
    print("TX:", json.dumps(tx | {"segundos_compresion": t_comp}, default=str, indent=2))
    print("RX:", json.dumps(datos_rx, indent=2, ensure_ascii=False, default=str))
    print("NOTA: canal simulado; los tiempos no son del radio real")


if __name__ == "__main__":
    main()
