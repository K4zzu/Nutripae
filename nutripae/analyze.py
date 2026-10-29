"""Pipeline de análisis: visión -> segmentación -> cruce -> veredicto -> foto anotada."""
from __future__ import annotations

import threading
from dataclasses import dataclass

from PIL import Image

from . import balance, fuse, messages, overlay
from .balance import Veredicto
from .segment import Segmentador, SegmentadorElipses
from .vision import Vision, VisionDemo


class PersonaDetectada(Exception):
    """La toma incluye a una persona: se descarta."""


class Ocupado(Exception):
    """Otro análisis está en curso y no se liberó a tiempo."""


@dataclass
class Analisis:
    veredicto: Veredicto
    titulo: str
    detalle: str
    foto_anotada: Image.Image
    original: Image.Image


class Analizador:
    def __init__(self, vision: Vision, segmentador: Segmentador, umbrales, espera_s: float = 20):
        self._vision = vision
        self._segmentador = segmentador
        self._umbrales = umbrales  # dict o función sin argumentos que lo devuelve
        self._espera_s = espera_s
        self._sem = threading.BoundedSemaphore(1)

    def analizar(self, imagen: Image.Image, grado: str, nombre: str | None) -> Analisis:
        if not self._sem.acquire(timeout=self._espera_s):
            raise Ocupado()
        try:
            resultado = self._vision.analizar(imagen)
            if resultado.persona:
                raise PersonaDetectada()
            if isinstance(self._vision, VisionDemo):
                imagen = overlay.bandeja_sintetica(resultado.detecciones)
            if isinstance(self._segmentador, SegmentadorElipses):
                regiones = self._segmentador.segmentar_desde([d.bbox for d in resultado.detecciones])
            else:
                regiones = self._segmentador.segmentar(imagen)
            porciones = fuse.cruzar(resultado.detecciones, regiones)
            umbrales = self._umbrales() if callable(self._umbrales) else self._umbrales
            veredicto = balance.evaluar(porciones, grado, umbrales)
            titulo, detalle = messages.mensaje(veredicto, nombre, grado=grado)
            foto = overlay.anotar(imagen, veredicto.porciones)
            return Analisis(veredicto, titulo, detalle, foto, imagen)
        finally:
            self._sem.release()
