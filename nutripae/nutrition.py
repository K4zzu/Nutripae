"""Tabla de composición de alimentos (por 100 g) y cálculo de nutrientes.

Valores aproximados tomados como referencia de la Tabla de Composición de
Alimentos Colombianos (TCAC, ICBF 2018) y USDA. Para producción se reemplaza
por la TCAC completa cargada desde CSV.
"""
from dataclasses import dataclass

NUTRIENTES = ["kcal", "proteina_g", "carbohidratos_g", "grasa_g", "fibra_g", "hierro_mg", "calcio_mg"]
NUTRIENTE_LABEL = {
    "kcal": "Energía (kcal)",
    "proteina_g": "Proteína (g)",
    "carbohidratos_g": "Carbohidratos (g)",
    "grasa_g": "Grasa (g)",
    "fibra_g": "Fibra (g)",
    "hierro_mg": "Hierro (mg)",
    "calcio_mg": "Calcio (mg)",
}


@dataclass(frozen=True)
class Alimento:
    nombre: str
    grupo: str
    kcal: float
    proteina_g: float
    carbohidratos_g: float
    grasa_g: float
    fibra_g: float
    hierro_mg: float
    calcio_mg: float
    color: str  # color para la superposición visual


# clave -> Alimento (valores por 100 g, porción comestible cocida cuando aplica)
TABLA: dict[str, Alimento] = {
    "pollo_guisado":     Alimento("Pollo guisado", "proteina", 190, 25.0, 2.0, 9.0, 0.2, 1.1, 15, "#E8A33D"),
    "carne_res_guisada": Alimento("Carne de res guisada", "proteina", 200, 26.0, 1.5, 10.5, 0.1, 2.7, 12, "#B5533C"),
    "huevo":             Alimento("Huevo revuelto", "proteina", 155, 13.0, 1.1, 11.0, 0.0, 1.2, 50, "#F2C94C"),
    "pescado":           Alimento("Pescado sudado", "proteina", 150, 22.0, 1.0, 6.0, 0.0, 0.9, 30, "#9BB7D4"),
    "arroz_blanco":      Alimento("Arroz blanco cocido", "cereal", 130, 2.7, 28.0, 0.3, 0.4, 0.2, 10, "#F1EDE4"),
    "papa_cocida":       Alimento("Papa cocida", "tuberculo", 87, 1.9, 20.0, 0.1, 1.8, 0.3, 5, "#D9C27A"),
    "yuca":              Alimento("Yuca cocida", "tuberculo", 160, 1.4, 38.0, 0.3, 1.8, 0.3, 16, "#EFE3B8"),
    "platano_maduro":    Alimento("Plátano maduro cocido", "tuberculo", 120, 1.0, 31.0, 0.2, 2.3, 0.6, 3, "#E6B548"),
    "lentejas":          Alimento("Lentejas cocidas", "tuberculo", 116, 9.0, 20.0, 0.4, 7.9, 3.3, 19, "#8A6A3B"),
    "frijol":            Alimento("Fríjol cocido", "tuberculo", 130, 8.5, 23.0, 0.5, 7.0, 2.5, 30, "#6E3F2A"),
    "ensalada_fresca":   Alimento("Ensalada fresca", "verdura", 25, 1.3, 4.5, 0.2, 1.5, 0.5, 25, "#5BA85B"),
    "banano":            Alimento("Banano", "fruta", 89, 1.1, 23.0, 0.3, 2.6, 0.3, 5, "#F4D35E"),
    "mango":             Alimento("Mango", "fruta", 60, 0.8, 15.0, 0.4, 1.6, 0.2, 11, "#F28C28"),
    "naranja":           Alimento("Naranja", "fruta", 47, 0.9, 12.0, 0.1, 2.4, 0.1, 40, "#F7A541"),
    "papaya":            Alimento("Papaya", "fruta", 43, 0.5, 11.0, 0.3, 1.7, 0.3, 20, "#F2865E"),
    "jugo_natural":      Alimento("Jugo natural", "bebida", 45, 0.3, 11.0, 0.1, 0.3, 0.2, 8, "#D96C8E"),
    "leche":             Alimento("Leche entera", "bebida", 61, 3.2, 4.8, 3.3, 0.0, 0.0, 113, "#FAFAFA"),
    "pan":               Alimento("Pan", "cereal", 270, 8.0, 50.0, 3.5, 2.5, 1.5, 40, "#C9A26B"),
    "arepa":             Alimento("Arepa de maíz", "cereal", 220, 5.0, 46.0, 2.0, 3.0, 1.0, 10, "#EADCA6"),
}


def nutrientes(alimento: str, gramos: float) -> dict[str, float]:
    """Nutrientes aportados por `gramos` del alimento."""
    a = TABLA.get(alimento)
    if a is None or gramos <= 0:
        return {n: 0.0 for n in NUTRIENTES}
    f = gramos / 100.0
    return {n: round(getattr(a, n) * f, 2) for n in NUTRIENTES}


def sumar(porciones: dict[str, float]) -> dict[str, float]:
    """Suma nutrientes de un diccionario alimento -> gramos."""
    total = {n: 0.0 for n in NUTRIENTES}
    for alimento, g in porciones.items():
        for n, v in nutrientes(alimento, g).items():
            total[n] += v
    return {n: round(v, 1) for n, v in total.items()}
