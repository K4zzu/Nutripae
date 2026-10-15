"""Reglas de verificación de la ración: completitud, porción por grado, aptitud."""
from __future__ import annotations

from dataclasses import dataclass, field

from .detector import Deteccion
from .menu import Minuta, meta_gramos, TOLERANCIA, UMBRAL_BAJO, KCAL_META, GRUPO_LABEL
from .nutrition import sumar


@dataclass
class ItemResultado:
    alimento: str
    nombre: str
    grupo: str
    meta_g: float
    servido_g: float
    estado: str        # ok | bajo | alto | falta | no_apto
    mensaje: str


@dataclass
class Resultado:
    aprobada: bool
    semaforo: str                       # verde | amarillo | rojo
    items: list[ItemResultado] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)
    nutrientes: dict = field(default_factory=dict)
    kcal_meta: float = 0
    cumplimiento_kcal: float = 0        # % de la meta energética

    def estados(self) -> dict[str, str]:
        return {i.alimento: i.estado for i in self.items}

    def porciones(self) -> dict[str, float]:
        return {i.alimento: i.servido_g for i in self.items if i.servido_g > 0}


def verificar(detecciones: list[Deteccion], minuta: Minuta, grado: str) -> Resultado:
    metas = meta_gramos(grado, minuta)
    por_alimento = {d.alimento: d for d in detecciones}
    items, alertas = [], []

    for comp in minuta.componentes:
        meta = metas[comp.alimento]
        d = por_alimento.get(comp.alimento)
        if d is None:
            items.append(ItemResultado(comp.alimento, comp.nombre, comp.grupo, meta, 0, "falta",
                                       f"Falta {GRUPO_LABEL[comp.grupo].lower()}: {comp.nombre}"))
            alertas.append(f"❌ Falta {comp.nombre} ({GRUPO_LABEL[comp.grupo]})")
            continue
        if not d.apto:
            items.append(ItemResultado(comp.alimento, comp.nombre, comp.grupo, meta, d.gramos, "no_apto",
                                       d.observacion or "Alimento con mal aspecto"))
            alertas.append(f"⛔ {comp.nombre} NO APTO — {d.observacion or 'mal aspecto'}")
            continue
        ratio = d.gramos / meta if meta else 1
        if ratio < UMBRAL_BAJO:
            est, msg = "bajo", f"Porción incompleta: {d.gramos:.0f} g de {meta:.0f} g ({ratio:.0%})"
            alertas.append(f"⚠️ {comp.nombre}: {msg}")
        elif ratio > 1 + TOLERANCIA:
            est, msg = "alto", f"Porción mayor a la meta: {d.gramos:.0f} g de {meta:.0f} g"
        else:
            est, msg = "ok", f"{d.gramos:.0f} g (meta {meta:.0f} g)"
        items.append(ItemResultado(comp.alimento, comp.nombre, comp.grupo, meta, d.gramos, est, msg))

    # alimentos no esperados
    for d in detecciones:
        if d.alimento not in metas:
            alertas.append(f"ℹ️ Alimento no previsto en la minuta: {d.nombre}")

    nutr = sumar({i.alimento: i.servido_g for i in items if i.estado != "no_apto"})
    kcal_meta = KCAL_META[grado]
    cumpl = round(100 * nutr["kcal"] / kcal_meta, 1) if kcal_meta else 0

    hay_rojo = any(i.estado in ("falta", "no_apto") for i in items)
    hay_amarillo = any(i.estado == "bajo" for i in items)
    semaforo = "rojo" if hay_rojo else ("amarillo" if hay_amarillo else "verde")
    return Resultado(aprobada=(semaforo == "verde"), semaforo=semaforo, items=items, alertas=alertas,
                     nutrientes=nutr, kcal_meta=kcal_meta, cumplimiento_kcal=cumpl)


def consumo(servido: dict[str, float], sobrante: dict[str, float]) -> dict[str, float]:
    """Gramos consumidos por alimento = servido - sobrante (nunca negativo)."""
    return {a: round(max(0.0, g - sobrante.get(a, 0.0)), 1) for a, g in servido.items()}
