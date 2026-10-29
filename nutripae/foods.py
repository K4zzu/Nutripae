"""Catálogo de alimentos agrupado para el método del plato."""
from nutripae import nutrition

GRUPOS = ["proteina", "energetico", "verdura", "fruta", "bebida", "otro"]
GRUPO_LABEL = {
    "proteina": "Proteína",
    "energetico": "Energéticos",
    "verdura": "Verdura",
    "fruta": "Fruta",
    "bebida": "Bebida",
    "otro": "Otro",
}
GRUPO_COLOR = {
    "proteina": "#A6572E",
    "energetico": "#E8A317",
    "verdura": "#1F7A4D",
    "fruta": "#D96C8E",
    "bebida": "#4A7FB5",
    "otro": "#8A8577",
}

_GRUPO_TABLA = {"cereal": "energetico", "tuberculo": "energetico"}


def grupo_de(clave: str) -> str:
    """Grupo del plato de un alimento; clave desconocida -> 'otro'."""
    a = nutrition.TABLA.get(clave)
    if a is None:
        return "otro"
    g = _GRUPO_TABLA.get(a.grupo, a.grupo)
    return g if g in GRUPOS else "otro"


def catalogo() -> dict[str, tuple[str, str]]:
    """clave -> (nombre, grupo)."""
    return {k: (a.nombre, grupo_de(k)) for k, a in nutrition.TABLA.items()}
