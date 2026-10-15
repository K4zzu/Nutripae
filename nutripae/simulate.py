"""Genera datos sintéticos de varios días para poblar el tablero en la demo."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from .detector import DemoDetector
from .menu import MINUTAS, GRADOS
from .nutrition import sumar
from .storage import registrar_entrega, registrar_devolucion
from .verifier import verificar, consumo

SEDES = ["IE Santa Librada", "IE INEM Julián Motta Salas", "IE Técnico Superior",
         "IE Promoción Social", "IE El Limonar", "IE Ricardo Borrero Álvarez"]

# qué tanto se deja en el plato, por grupo (fracción sobrante media)
_SOBRA_MEDIA = {"proteina": 0.08, "cereal": 0.15, "tuberculo": 0.18, "verdura": 0.45, "fruta": 0.12, "bebida": 0.05}


def generar(con, dias: int = 10, raciones_por_dia: int = 60, semilla: int = 7):
    rng = random.Random(semilla)
    det = DemoDetector("aleatorio", semilla=semilla)
    hoy = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    minutas = list(MINUTAS.values())
    n = 0
    for d in range(dias, 0, -1):
        fecha = hoy - timedelta(days=d - 1)
        if fecha.weekday() >= 5:
            continue
        minuta = minutas[(dias - d) % len(minutas)]
        for i in range(raciones_por_dia):
            sede = rng.choice(SEDES)
            grado = rng.choices(list(GRADOS), weights=[0.2, 0.5, 0.3])[0]
            ts = fecha + timedelta(minutes=rng.randint(0, 90))
            dets = det.detectar(None, minuta, grado, None)
            peso = round(sum(x.gramos for x in dets) * rng.uniform(0.97, 1.03), 1)
            res = verificar(dets, minuta, grado)
            corregida = (res.semaforo != "verde") and rng.random() < 0.85
            eid = registrar_entrega(con, sede=sede, bandeja=f"B-{i+1:03d}", grado=grado, minuta=minuta.codigo,
                                    peso_g=peso, resultado=res, backend="demo", corregida=corregida, ts=ts)
            servido = res.porciones()
            sobrante = {}
            for comp in minuta.componentes:
                g = servido.get(comp.alimento, 0)
                frac = min(1.0, max(0.0, rng.gauss(_SOBRA_MEDIA[comp.grupo], 0.12)))
                sobrante[comp.alimento] = round(g * frac, 1)
            cons = consumo(servido, sobrante)
            registrar_devolucion(con, entrega_id=eid, bandeja=f"B-{i+1:03d}", peso_g=round(sum(sobrante.values()), 1),
                                 sobrante=sobrante, consumido=cons, nutrientes=sumar(cons),
                                 ts=ts + timedelta(minutes=rng.randint(15, 35)))
            n += 1
    return n
