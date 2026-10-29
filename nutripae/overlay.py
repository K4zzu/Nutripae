"""Foto anotada: cada alimento coloreado por grupo con su contorno real."""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFont

from .balance import Porcion
from .foods import GRUPO_COLOR
from .nutrition import TABLA
from .vision import Deteccion

COLOR_NO_APTO = "#B81F3C"
_ALFA_RELLENO = 115  # ~45 %


def _rgb(hexcolor: str) -> tuple[int, int, int]:
    h = hexcolor.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _fuente(tam: int):
    for nombre in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except Exception:
            continue
    return ImageFont.load_default(tam)


def reducir(imagen: Image.Image, lado_max: int = 1024) -> Image.Image:
    """Copia RGB con el lado mayor limitado a `lado_max`, conservando la proporción."""
    img = imagen.convert("RGB")
    if max(img.size) <= lado_max:
        return img.copy()
    img = img.copy()
    img.thumbnail((lado_max, lado_max), Image.LANCZOS)
    return img


def _contorno_discontinuo(draw, puntos, color, ancho, trazo=12, hueco=8):
    cerrado = puntos + [puntos[0]]
    for (x1, y1), (x2, y2) in zip(cerrado, cerrado[1:]):
        largo = math.hypot(x2 - x1, y2 - y1)
        if largo == 0:
            continue
        ux, uy = (x2 - x1) / largo, (y2 - y1) / largo
        t = 0.0
        while t < largo:
            fin = min(t + trazo, largo)
            draw.line((x1 + ux * t, y1 + uy * t, x1 + ux * fin, y1 + uy * fin), fill=color, width=ancho)
            t += trazo + hueco


def anotar(imagen: Image.Image, porciones: list[Porcion], lado_max: int = 1024) -> Image.Image:
    """Pinta cada porción con su polígono, coloreado por grupo, y una etiqueta con nombre y gramos."""
    img = reducir(imagen, lado_max)
    w, h = img.size
    draw = ImageDraw.Draw(img, "RGBA")
    font = _fuente(max(14, w // 50))
    grosor = max(3, w // 220)
    radio = max(8, w // 70)
    for p in porciones:
        if p.estado == "falta" or not p.poligono or len(p.poligono) < 3:
            continue
        no_apto = p.estado == "no_apto"
        col = _rgb(COLOR_NO_APTO if no_apto else GRUPO_COLOR.get(p.grupo, GRUPO_COLOR["otro"]))
        pts = [(x * w, y * h) for x, y in p.poligono]
        draw.polygon(pts, fill=col + (_ALFA_RELLENO,))
        if p.aproximado:
            _contorno_discontinuo(draw, pts, col + (255,), grosor)
        else:
            draw.line(pts + [pts[0]], fill=col + (255,), width=grosor, joint="curve")
        etiqueta = f"{p.nombre} · no apto" if no_apto else f"{p.nombre} · {p.gramos:.0f} g"
        ax, ay = min(pts, key=lambda q: (q[1], q[0]))
        tw, th = draw.textbbox((0, 0), etiqueta, font=font)[2:]
        x0 = max(0, min(ax, w - tw - 16))
        y0 = max(0, min(ay, h - th - 12))
        draw.rounded_rectangle((x0, y0, x0 + tw + 16, y0 + th + 12), radius=radio, fill=col + (255,))
        draw.text((x0 + 8, y0 + 5), etiqueta, fill=(255, 255, 255), font=font)
    return img


def bandeja_sintetica(detecciones: list[Deteccion], tamano=(900, 600)) -> Image.Image:
    """Imagen esquemática de bandeja para el modo demostración (sin cámara)."""
    img = Image.new("RGB", tamano, (26, 32, 29))
    draw = ImageDraw.Draw(img)
    w, h = tamano
    draw.rounded_rectangle((int(w * .02), int(h * .03), int(w * .99), int(h * .97)), radius=36,
                           outline=(58, 69, 64), width=4, fill=(43, 52, 48))
    for d in detecciones:
        x1, y1, x2, y2 = d.bbox
        col = TABLA[d.alimento].color if d.alimento in TABLA else "#999999"
        if not d.apto:
            col = "#5a3a2a"
        cx, cy = (x1 + x2) / 2 * w, (y1 + y2) / 2 * h
        rx, ry = (x2 - x1) / 2 * w * 0.8, (y2 - y1) / 2 * h * 0.8
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=col, outline=(37, 45, 41), width=3)
    return img
