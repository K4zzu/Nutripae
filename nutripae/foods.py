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
    "proteina": "#EE3B5A",
    "energetico": "#FAC344",
    "verdura": "#23D098",
    "fruta": "#4C17C1",
    "bebida": "#1C3F9E",
    "otro": "#9A96B3",
}

_GRUPO_TABLA = {"cereal": "energetico", "tuberculo": "energetico"}


def _grupo_tabla(clave: str) -> str:
    a = nutrition.TABLA.get(clave)
    if a is None:
        return "otro"
    g = _GRUPO_TABLA.get(a.grupo, a.grupo)
    return g if g in GRUPOS else "otro"


def extras(con) -> list[dict]:
    """Alimentos que el administrador añadió (sin datos de nutrientes); nunca pisan los propios."""
    from nutripae import db
    return [e for e in db.param(con, "alimentos_extra", [])
            if e["clave"] not in nutrition.TABLA and e["grupo"] in GRUPOS]


def grupo_de(clave: str, con=None) -> str:
    """Grupo del plato de un alimento; clave desconocida -> 'otro'. Con `con` incluye los extras."""
    if clave not in nutrition.TABLA and con is not None:
        for e in extras(con):
            if e["clave"] == clave:
                return e["grupo"]
    return _grupo_tabla(clave)


def catalogo(con=None) -> dict[str, tuple[str, str]]:
    """clave -> (nombre, grupo). Con `con` se fusionan los alimentos extra."""
    cat = {k: (a.nombre, _grupo_tabla(k)) for k, a in nutrition.TABLA.items()}
    if con is not None:
        for e in extras(con):
            cat[e["clave"]] = (e["nombre"], e["grupo"])
    return cat
