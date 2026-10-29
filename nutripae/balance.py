"""Reglas del plato balanceado (método del plato).

Los umbrales de UMBRALES_INICIALES son valores iniciales pendientes de
validación por nutricionista.
"""
from dataclasses import dataclass

from nutripae import nutrition
from nutripae.foods import GRUPO_LABEL

ORDEN_FALTAS = ["verdura", "fruta", "proteina", "energetico"]  # grupos requeridos

UMBRALES_INICIALES = {
    "objetivo": {"verdura_fruta": 0.50, "proteina": 0.25, "energetico": 0.25},
    "factor_corto": 0.5,
    "factor_excedido": 1.8,
    # mitad del tamaño esperado 250/350/450 g
    "plato_minimo_g": {"preescolar": 125, "primaria": 175, "secundaria": 225},
}


@dataclass
class Porcion:
    alimento: str
    nombre: str
    grupo: str
    gramos: float
    apto: bool = True
    observacion: str = ""
    poligono: list[tuple[float, float]] | None = None
    bbox: tuple = (0, 0, 1, 1)
    aproximado: bool = False
    estado: str = "ok"


@dataclass
class Veredicto:
    semaforo: str
    razon_grupo: str | None
    razon_tipo: str | None
    porciones: list[Porcion]
    total_g: float
    proporciones: dict[str, float]
    nutrientes: dict[str, float]


def _clave_prop(grupo: str) -> str | None:
    if grupo in ("verdura", "fruta"):
        return "verdura_fruta"
    if grupo in ("proteina", "energetico"):
        return grupo
    return None


def evaluar(porciones: list[Porcion], grado: str, umbrales: dict = UMBRALES_INICIALES) -> Veredicto:
    objetivo = umbrales["objetivo"]
    factor_corto = umbrales["factor_corto"]
    factor_excedido = umbrales["factor_excedido"]

    total = sum(x.gramos for x in porciones if x.grupo != "bebida")
    gramos_grupo = {"verdura_fruta": 0.0, "proteina": 0.0, "energetico": 0.0}
    for x in porciones:
        k = _clave_prop(x.grupo)
        if k:
            gramos_grupo[k] += x.gramos
    props = {k: (v / total if total > 0 else 0.0) for k, v in gramos_grupo.items()}

    for x in porciones:
        k = _clave_prop(x.grupo)
        if not x.apto:
            x.estado = "no_apto"
        elif k is None:
            x.estado = "ok"
        elif props[k] < objetivo[k] * factor_corto:
            x.estado = "corto"
        elif props[k] > objetivo[k] * factor_excedido:
            x.estado = "excedido"
        else:
            x.estado = "ok"

    # un grupo con porción no apta está presente (se reporta como no_apto, no como falta)
    presentes = {x.grupo for x in porciones if x.gramos > 0}
    faltan = [g for g in ORDEN_FALTAS if g not in presentes]
    for g in faltan:
        porciones.append(Porcion(f"falta_{g}", GRUPO_LABEL[g], g, 0, estado="falta"))

    no_aptos = [x for x in porciones if x.estado == "no_apto"]
    cortos = [x for x in porciones if x.estado == "corto"]
    excedidos = [x for x in porciones if x.estado == "excedido"]

    def razon_relativa(x):
        k = _clave_prop(x.grupo)
        return props[k] / objetivo[k]

    if faltan:
        sem, rg, rt = "rojo", faltan[0], "falta"
    elif no_aptos:
        sem, rg, rt = "rojo", no_aptos[0].grupo, "no_apto"
    elif cortos:
        sem, rg, rt = "amarillo", min(cortos, key=razon_relativa).grupo, "corto"
    elif excedidos:
        sem, rg, rt = "amarillo", max(excedidos, key=razon_relativa).grupo, "excedido"
    elif total < umbrales["plato_minimo_g"][grado]:
        sem, rg, rt = "amarillo", None, "pequeno"
    else:
        sem, rg, rt = "verde", None, None

    por_alimento: dict[str, float] = {}
    for x in porciones:
        if x.apto and x.gramos > 0:
            por_alimento[x.alimento] = por_alimento.get(x.alimento, 0.0) + x.gramos
    nutr = nutrition.sumar(por_alimento)
    return Veredicto(sem, rg, rt, porciones, total, props, nutr)
