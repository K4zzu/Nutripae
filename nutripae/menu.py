"""Minutas (menús) del PAE y metas de porción por grupo de edad.

Los valores son de REFERENCIA para el prototipo. En producción se cargan desde la
minuta patrón vigente del operador (Resolución 335 de 2021 del MEN - Lineamientos
Técnicos Administrativos del PAE) y se parametrizan por sede.
"""
from dataclasses import dataclass, field

# Grupos de alimentos que debe tener un almuerzo PAE completo
GRUPOS = ["proteina", "cereal", "tuberculo", "verdura", "fruta", "bebida"]

GRUPO_LABEL = {
    "proteina": "Proteína",
    "cereal": "Cereal",
    "tuberculo": "Tubérculo / plátano",
    "verdura": "Verdura",
    "fruta": "Fruta",
    "bebida": "Bebida",
}

# Grupos de edad / grado (clave -> etiqueta)
GRADOS = {
    "preescolar": "Preescolar (3-5 años)",
    "primaria": "Primaria (6-11 años)",
    "secundaria": "Secundaria (12-17 años)",
}

# Gramos objetivo por grupo de alimento según grado (porción servida)
PORCION_G = {
    "preescolar": {"proteina": 50, "cereal": 80, "tuberculo": 50, "verdura": 30, "fruta": 60, "bebida": 150},
    "primaria":   {"proteina": 70, "cereal": 100, "tuberculo": 70, "verdura": 40, "fruta": 80, "bebida": 200},
    "secundaria": {"proteina": 100, "cereal": 120, "tuberculo": 90, "verdura": 60, "fruta": 100, "bebida": 200},
}

# Meta energética del almuerzo (≈30 % del requerimiento diario) por grado
KCAL_META = {"preescolar": 450, "primaria": 550, "secundaria": 700}

TOLERANCIA = 0.20   # ±20 % sobre la porción objetivo se considera "cumple"
UMBRAL_BAJO = 0.80  # <80 % de la porción = "incompleta"


@dataclass
class Componente:
    alimento: str      # clave en nutrition.TABLA
    grupo: str
    nombre: str        # cómo se muestra


@dataclass
class Minuta:
    codigo: str
    nombre: str
    componentes: list[Componente] = field(default_factory=list)

    def componente_por_grupo(self, grupo: str) -> Componente | None:
        return next((c for c in self.componentes if c.grupo == grupo), None)

    def alimentos(self) -> list[str]:
        return [c.alimento for c in self.componentes]


MINUTAS: dict[str, Minuta] = {
    "M1": Minuta("M1", "Pollo guisado con arroz y papa", [
        Componente("pollo_guisado", "proteina", "Pollo guisado"),
        Componente("arroz_blanco", "cereal", "Arroz blanco"),
        Componente("papa_cocida", "tuberculo", "Papa cocida"),
        Componente("ensalada_fresca", "verdura", "Ensalada de tomate y lechuga"),
        Componente("banano", "fruta", "Banano"),
        Componente("jugo_natural", "bebida", "Jugo de guayaba"),
    ]),
    "M2": Minuta("M2", "Carne molida con lentejas", [
        Componente("carne_res_guisada", "proteina", "Carne molida guisada"),
        Componente("arroz_blanco", "cereal", "Arroz blanco"),
        Componente("lentejas", "tuberculo", "Lentejas"),
        Componente("ensalada_fresca", "verdura", "Ensalada de zanahoria"),
        Componente("mango", "fruta", "Mango"),
        Componente("leche", "bebida", "Leche"),
    ]),
    "M3": Minuta("M3", "Huevo con arroz y plátano", [
        Componente("huevo", "proteina", "Huevo revuelto"),
        Componente("arroz_blanco", "cereal", "Arroz blanco"),
        Componente("platano_maduro", "tuberculo", "Plátano maduro"),
        Componente("ensalada_fresca", "verdura", "Ensalada de pepino"),
        Componente("naranja", "fruta", "Naranja"),
        Componente("jugo_natural", "bebida", "Jugo de mora"),
    ]),
    "M4": Minuta("M4", "Pescado con yuca", [
        Componente("pescado", "proteina", "Pescado sudado"),
        Componente("arroz_blanco", "cereal", "Arroz con coco"),
        Componente("yuca", "tuberculo", "Yuca cocida"),
        Componente("ensalada_fresca", "verdura", "Ensalada de repollo"),
        Componente("papaya", "fruta", "Papaya"),
        Componente("jugo_natural", "bebida", "Limonada"),
    ]),
}


def meta_gramos(grado: str, minuta: Minuta) -> dict[str, float]:
    """Gramos objetivo por alimento para un grado y una minuta."""
    return {c.alimento: PORCION_G[grado][c.grupo] for c in minuta.componentes}
