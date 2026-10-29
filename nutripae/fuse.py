"""Cruce entre alimentos nombrados por la IA y contornos segmentados."""
from __future__ import annotations

from nutripae import foods
from nutripae.balance import Porcion
from nutripae.segment import Region
from nutripae.vision import Deteccion


def _centroide(poligono):
    n = len(poligono)
    return sum(p[0] for p in poligono) / n, sum(p[1] for p in poligono) / n


def _dentro(punto, bbox):
    x, y = punto
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def _iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def cruzar(detecciones: list[Deteccion], regiones: list[Region]) -> list[Porcion]:
    catalogo = foods.catalogo()
    usadas: set[int] = set()
    porciones = []
    for d in detecciones:
        candidatas = [i for i, r in enumerate(regiones)
                      if i not in usadas and _dentro(_centroide(r.poligono), d.bbox)]
        mejor = max(candidatas, key=lambda i: (_iou(regiones[i].bbox, d.bbox), regiones[i].area),
                    default=None)
        x1, y1, x2, y2 = d.bbox
        if mejor is None:
            poligono, aproximado = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)], True
        else:
            usadas.add(mejor)
            poligono, aproximado = [tuple(p) for p in regiones[mejor].poligono], False
        if d.alimento == "otro" or d.alimento not in catalogo:
            nombre = d.nombre
        else:
            nombre = catalogo[d.alimento][0]
        porciones.append(Porcion(d.alimento, nombre, foods.grupo_de(d.alimento), d.gramos,
                                 apto=d.apto, observacion=d.observacion, poligono=poligono,
                                 bbox=tuple(float(v) for v in d.bbox), aproximado=aproximado))
    return porciones
