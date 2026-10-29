"""Segmentación de la bandeja en regiones (contornos normalizados 0–1)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from PIL import Image

AREA_MAX = 0.8
AREA_MIN = 0.005
PUNTOS_ELIPSE = 24


@dataclass
class Region:
    poligono: list[tuple[float, float]]
    bbox: tuple[float, float, float, float]
    area: float


class Segmentador(Protocol):
    def segmentar(self, imagen: Image.Image) -> list[Region]: ...


def area_poligono(puntos: list[tuple[float, float]]) -> float:
    """Área por la fórmula del cordón (shoelace)."""
    n = len(puntos)
    s = 0.0
    for i in range(n):
        x1, y1 = puntos[i]
        x2, y2 = puntos[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


class FastSAMSegmentador:
    def __init__(self, pesos: str = "FastSAM-s.pt", imgsz: int = 640):
        self.pesos = pesos
        self.imgsz = imgsz
        self._modelo = None

    def _cargar(self):
        if self._modelo is None:
            from ultralytics import FastSAM
            self._modelo = FastSAM(self.pesos)
        return self._modelo

    def segmentar(self, imagen: Image.Image) -> list[Region]:
        res = self._cargar()(imagen.convert("RGB"), imgsz=self.imgsz,
                             retina_masks=True, conf=0.4, iou=0.9, verbose=False)
        masks = res[0].masks
        if masks is None:
            return []
        regiones = []
        for xy in masks.xyn:
            poligono = [(float(x), float(y)) for x, y in xy]
            if len(poligono) < 3:
                continue
            area = area_poligono(poligono)
            if area > AREA_MAX or area < AREA_MIN:
                continue
            xs = [p[0] for p in poligono]
            ys = [p[1] for p in poligono]
            regiones.append(Region(poligono, (min(xs), min(ys), max(xs), max(ys)), area))
        regiones.sort(key=lambda r: r.area, reverse=True)
        return regiones


class SegmentadorElipses:
    """Modo demostración: una elipse inscrita en cada caja ya conocida."""

    def segmentar(self, imagen: Image.Image) -> list[Region]:
        return []

    def segmentar_desde(self, bboxes: list[tuple]) -> list[Region]:
        regiones = []
        for x0, y0, x1, y1 in bboxes:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
            # min/max evita que el error de coma flotante saque un punto del bbox
            poligono = [(min(max(cx + rx * math.cos(2 * math.pi * k / PUNTOS_ELIPSE), x0), x1),
                         min(max(cy + ry * math.sin(2 * math.pi * k / PUNTOS_ELIPSE), y0), y1))
                        for k in range(PUNTOS_ELIPSE)]
            regiones.append(Region(poligono, (x0, y0, x1, y1), area_poligono(poligono)))
        return regiones


def crear_segmentador(settings) -> Segmentador:
    if settings.segmentador == "fastsam":
        return FastSAMSegmentador()
    if settings.segmentador == "demo":
        return SegmentadorElipses()
    raise ValueError(f"Segmentador desconocido: {settings.segmentador!r}")
