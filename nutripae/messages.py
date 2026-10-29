"""Mensajes para el niño: convierte un Veredicto en (titulo, detalle)."""
import random

from nutripae.balance import UMBRALES_INICIALES, Veredicto

RAZON = {
    "verdura": "La verdura te ayuda a crecer fuerte.",
    "fruta": "La fruta te da vitaminas para no enfermarte.",
    "proteina": "La proteína construye tus músculos.",
    "energetico": "El arroz, la papa y el plátano te dan energía para jugar y estudiar.",
}

# Las mismas razones, en tercera persona, para el informe que leen las familias.
RAZON_FAMILIA = {
    "verdura": "La verdura le ayuda a crecer fuerte.",
    "fruta": "La fruta le da vitaminas para no enfermarse.",
    "proteina": "La proteína construye sus músculos.",
    "energetico": "El arroz, la papa y el plátano le dan energía para jugar y estudiar.",
}

VERDE = {
    "ninos": [
        "¡Hoy sí tienes fruta!",
        "¡Tu plato tiene de todo!",
        "¡Qué plato tan colorido!",
        "¡Con este plato vas a tener mucha energía!",
        "¡Así se come para crecer fuerte!",
        "¡Tu plato está perfecto para jugar!",
    ],
    "adolescentes": [
        "Plato completo. Bien hecho.",
        "Buena combinación de grupos.",
        "Tu plato está bien equilibrado.",
        "Así se arma un buen almuerzo.",
        "Tienes proteína, energía, verdura y fruta.",
        "Buena elección. Sigue así.",
    ],
}

# Palabras que el niño entiende para cada grupo.
_NOMBRE_GRUPO = {
    "verdura": "verdura",
    "fruta": "fruta",
    "proteina": "proteína",
    "energetico": "arroz, papa o plátano",
}
_FEMENINOS = {"verdura", "fruta", "proteina"}
_CLAVE_A_GRUPO = {"verdura_fruta": "verdura", "proteina": "proteina", "energetico": "energetico"}
_OBJETIVO = UMBRALES_INICIALES["objetivo"]


def _grupo_mas_corto(v: Veredicto) -> str:
    """Grupo (distinto del excedido) con menor proporción respecto a su objetivo."""
    excedido = v.razon_grupo
    candidatos = []
    for clave, objetivo in _OBJETIVO.items():
        grupo = _CLAVE_A_GRUPO[clave]
        if grupo == excedido or (clave == "verdura_fruta" and excedido == "fruta"):
            continue
        candidatos.append((v.proporciones.get(clave, 0.0) / objetivo, grupo))
    if not candidatos:
        return "verdura"
    razon, grupo = min(candidatos, key=lambda c: c[0])
    return grupo if razon < 1 else "verdura"


def _detalle(v: Veredicto, grado: str, semilla: int | None) -> str:
    tipo = v.razon_tipo
    grupo = v.razon_grupo
    if tipo is None:
        lista = VERDE["adolescentes" if grado == "secundaria" else "ninos"]
        return random.Random(semilla).choice(lista)
    if tipo == "falta":
        return f"Te falta {_NOMBRE_GRUPO[grupo]}. {RAZON[grupo]}"
    if tipo == "corto":
        return f"Te falta un poco más de {_NOMBRE_GRUPO[grupo]}. {RAZON[grupo]}"
    if tipo == "excedido":
        mucho = "mucha" if grupo in _FEMENINOS else "mucho"
        return f"Tienes {mucho} {_NOMBRE_GRUPO[grupo]} y poco de lo demás. {RAZON[_grupo_mas_corto(v)]}"
    if tipo == "no_apto":
        alimento = next((p.nombre for p in v.porciones if p.estado == "no_apto"), "Un alimento")
        return f"{alimento} no se ve bien. Pide que te lo cambien."
    return "Tu plato está muy pequeño. Pide un poco más de todo."


def mensaje(veredicto: Veredicto, nombre: str | None, grado: str = "primaria",
            semilla: int | None = None) -> tuple[str, str]:
    """(titulo, detalle) para el niño. El grado solo cambia el tono de las frases verdes."""
    coma = f", {nombre}" if nombre else ""
    if veredicto.semaforo == "verde":
        titulo = f"¡Listo{coma}! Tu plato está balanceado."
    elif veredicto.semaforo == "amarillo":
        titulo = f"Casi{coma}. Vuelve a la fila y completa tu plato."
    else:
        titulo = f"Espera{coma}. Hay que cambiar tu plato."
    return titulo, _detalle(veredicto, grado, semilla)
