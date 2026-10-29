"""Informe en PDF del historial de un niño, escrito para su familia."""
from __future__ import annotations

import io
import sqlite3
from datetime import date

from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

from nutripae import foods, history, messages
from nutripae.cards import LOGO, MORADO, PAGINA_H, PAGINA_W, TINTA
from nutripae.config import Settings

MARGEN = 15 * mm
FILAS_POR_PAGINA = 25
ALTO_FILA = 8 * mm
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

# (texto, color, ícono) por semáforo; el ícono se dibuja con trazos porque Helvetica no trae ✓ ni ✕.
SEMAFORO = {
    "verde": ("Balanceado", (0x1B / 255, 0x8F / 255, 0x68 / 255), "ok"),
    "amarillo": ("Casi", (0xB9 / 255, 0x82 / 255, 0x0A / 255), "alto"),
    "rojo": ("Cambiado", (0xE0 / 255, 0x2E / 255, 0x4D / 255), "no"),
    "no_apto": ("No apto", (0xB8 / 255, 0x1F / 255, 0x3C / 255), "guion"),
}


def periodo_texto(desde: date, hasta: date) -> str:
    return f"del {desde.day} de {MESES[desde.month - 1]} al {hasta.day} de {MESES[hasta.month - 1]} de {hasta.year}"


def _fecha_corta(f: date) -> str:
    return f"{f.day} {MESES[f.month - 1][:3]}"


def parrafo_padres(con: sqlite3.Connection, estudiante_id: int, nombre: str, desde: date, hasta: date) -> str:
    dias = history.dias_estudiante(con, estudiante_id, desde, hasta)
    n = len(dias)
    if n == 0:
        return "En este periodo no hay verificaciones registradas."
    primero = nombre.split()[0] if nombre.split() else nombre
    buenos = sum(d["ultima"]["semaforo"] == "verde" for d in dias)
    inicio = "En este día" if n == 1 else f"En estos {n} días"
    texto = f"{inicio}, a {primero} le sirvieron un plato balanceado {buenos} de {n} veces."
    faltas = history.faltas_por_grupo(con, estudiante_id, desde, hasta)
    if not faltas:
        return texto + " No le faltó ningún grupo de alimentos. ¡Muy bien!"
    grupo = max(faltas, key=lambda g: (faltas[g], g))
    etiqueta = foods.GRUPO_LABEL.get(grupo, grupo).lower()
    razon = messages.RAZON.get(grupo, "")
    return f"{texto} Lo que más le faltó fue {etiqueta}: {razon}" if razon else f"{texto} Lo que más le faltó fue {etiqueta}."


def _icono(c: canvas.Canvas, x: float, y: float, tipo: str, color) -> None:
    """Ícono de 4 mm centrado en (x, y)."""
    c.setStrokeColorRGB(*color)
    c.setFillColorRGB(*color)
    c.setLineWidth(1.2)
    c.circle(x, y, 2 * mm, stroke=1, fill=0)
    c.setLineCap(1)
    if tipo == "ok":
        p = c.beginPath()
        p.moveTo(x - 0.9 * mm, y)
        p.lineTo(x - 0.2 * mm, y - 0.8 * mm)
        p.lineTo(x + 1 * mm, y + 0.9 * mm)
        c.drawPath(p, stroke=1, fill=0)
    elif tipo == "no":
        c.line(x - 0.8 * mm, y - 0.8 * mm, x + 0.8 * mm, y + 0.8 * mm)
        c.line(x - 0.8 * mm, y + 0.8 * mm, x + 0.8 * mm, y - 0.8 * mm)
    elif tipo == "alto":
        c.line(x, y - 0.1 * mm, x, y + 1 * mm)
        c.circle(x, y - 0.95 * mm, 0.2 * mm, stroke=0, fill=1)
    else:
        c.line(x - 0.8 * mm, y, x + 0.8 * mm, y)
    c.setLineCap(0)


def _encabezado(c: canvas.Canvas, est, desde: date, hasta: date) -> float:
    """Dibuja el encabezado completo y devuelve la y donde sigue el contenido."""
    y = PAGINA_H - MARGEN
    if LOGO.exists():
        c.drawImage(str(LOGO), MARGEN, y - 14 * mm, width=42 * mm, height=14 * mm,
                    preserveAspectRatio=True, anchor="nw", mask="auto")
    c.setFillColorRGB(*MORADO)
    c.setFont("Helvetica-Bold", 20)
    c.drawRightString(PAGINA_W - MARGEN, y - 8 * mm, "Informe para la familia")
    y -= 22 * mm
    c.setFillColorRGB(*TINTA)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(MARGEN, y, est["nombre"])
    y -= 6 * mm
    c.setFont("Helvetica", 10.5)
    c.drawString(MARGEN, y, " · ".join(p for p in (est["grado"], est["grupo"], est["sede"]) if p))
    y -= 5 * mm
    c.drawString(MARGEN, y, periodo_texto(desde, hasta))
    return y - 8 * mm


def _pie(c: canvas.Canvas, pagina: int) -> None:
    hoy = date.today()
    c.setStrokeColorRGB(*MORADO)
    c.setLineWidth(0.6)
    c.line(MARGEN, MARGEN + 6 * mm, PAGINA_W - MARGEN, MARGEN + 6 * mm)
    c.setFillColorRGB(*TINTA)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(MARGEN, MARGEN, "Este informe muestra lo que se sirvió, no lo que comió.")
    c.setFont("Helvetica", 8)
    c.drawRightString(PAGINA_W - MARGEN, MARGEN,
                      f"Generado el {hoy.day} de {MESES[hoy.month - 1]} de {hoy.year} · página {pagina}")


def _cabecera_tabla(c: canvas.Canvas, y: float) -> float:
    c.setFillColorRGB(*MORADO)
    c.roundRect(MARGEN, y - ALTO_FILA + 2 * mm, PAGINA_W - 2 * MARGEN, ALTO_FILA, 2 * mm, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 9.5)
    base = y - 3.2 * mm
    c.drawString(MARGEN + 3 * mm, base, "Día")
    c.drawString(MARGEN + 25 * mm, base, "Plato")
    c.drawString(MARGEN + 60 * mm, base, "Grupos que tenía")
    c.drawRightString(PAGINA_W - MARGEN - 3 * mm, base, "Calorías")
    return y - ALTO_FILA


def _fila(c: canvas.Canvas, y: float, d: dict, par: bool) -> None:
    u = d["ultima"]
    if par:
        c.setFillColorRGB(0.955, 0.945, 0.985)
        c.rect(MARGEN, y - ALTO_FILA + 2 * mm, PAGINA_W - 2 * MARGEN, ALTO_FILA, stroke=0, fill=1)
    base = y - 3.2 * mm
    c.setFillColorRGB(*TINTA)
    c.setFont("Helvetica", 9.5)
    c.drawString(MARGEN + 3 * mm, base, _fecha_corta(d["fecha"]))
    texto, color, tipo = SEMAFORO.get(u["semaforo"], (u["semaforo"], TINTA, "alto"))
    _icono(c, MARGEN + 28 * mm, base + 1.1 * mm, tipo, color)
    c.setFillColorRGB(*color)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(MARGEN + 33 * mm, base, texto)
    faltan = {p["grupo"] for p in u["porciones"] if p.get("estado") == "falta" and p.get("grupo")}
    hay = list(dict.fromkeys(p["grupo"] for p in u["porciones"] if p.get("grupo") and p["grupo"] not in faltan))
    grupos = ", ".join(foods.GRUPO_LABEL.get(g, g) for g in hay) or "—"
    c.setFillColorRGB(*TINTA)
    c.setFont("Helvetica", 9)
    c.drawString(MARGEN + 60 * mm, base, simpleSplit(grupos, "Helvetica", 9, 100 * mm)[0])
    c.drawRightString(PAGINA_W - MARGEN - 3 * mm, base, f"{round(u['nutrientes'].get('kcal', 0))} kcal")


def _fotos(dias: list[dict], settings: Settings) -> list[tuple[date, ImageReader]]:
    """La primera y la última con foto, en orden cronológico; salta archivos que no existen."""
    base = settings.fotos_dir.resolve()
    halladas = []
    for d in dias:
        ruta = d["ultima"]["foto"]
        if not ruta:
            continue
        archivo = (base / ruta).resolve()
        if archivo.is_relative_to(base) and archivo.is_file():
            try:
                halladas.append((d["fecha"], ImageReader(str(archivo))))
            except Exception:
                continue
    return [halladas[0], halladas[-1]] if len(halladas) > 2 else halladas


def pdf_historial(con: sqlite3.Connection, settings: Settings, estudiante_id: int,
                  desde: date, hasta: date) -> bytes:
    est = con.execute("SELECT * FROM estudiantes WHERE id=?", (estudiante_id,)).fetchone()
    if est is None:
        raise ValueError("estudiante inexistente")
    dias = sorted(history.dias_estudiante(con, estudiante_id, desde, hasta), key=lambda d: d["fecha"])
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGINA_W, PAGINA_H))
    c.setTitle(f"Informe para la familia - {est['nombre']}")
    pagina = 1

    y = _encabezado(c, est, desde, hasta)
    c.setFillColorRGB(*TINTA)
    c.setFont("Helvetica", 11.5)
    for linea in simpleSplit(parrafo_padres(con, estudiante_id, est["nombre"], desde, hasta),
                             "Helvetica", 11.5, PAGINA_W - 2 * MARGEN):
        c.drawString(MARGEN, y, linea)
        y -= 6 * mm
    y -= 4 * mm

    if dias:
        y = _cabecera_tabla(c, y)
        for i, d in enumerate(dias):
            if i and i % FILAS_POR_PAGINA == 0:
                _pie(c, pagina)
                c.showPage()
                pagina += 1
                y = _cabecera_tabla(c, PAGINA_H - MARGEN)
            _fila(c, y, d, i % 2 == 1)
            y -= ALTO_FILA

    fotos = _fotos(dias, settings)
    if fotos:
        ancho, alto_max = 70 * mm, 62 * mm
        if y - alto_max - 20 * mm < MARGEN + 10 * mm:
            _pie(c, pagina)
            c.showPage()
            pagina += 1
            y = PAGINA_H - MARGEN
        y -= 8 * mm
        c.setFillColorRGB(*MORADO)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(MARGEN, y, "Fotos del plato" if len(fotos) > 1 else "Foto del plato")
        y -= 4 * mm
        for k, (fecha, img) in enumerate(fotos):
            iw, ih = img.getSize()
            esc = min(ancho / iw, alto_max / ih)
            x = MARGEN + k * (ancho + 10 * mm)
            c.drawImage(img, x, y - ih * esc, width=iw * esc, height=ih * esc)
            c.setFillColorRGB(*TINTA)
            c.setFont("Helvetica", 8.5)
            c.drawString(x, y - ih * esc - 4 * mm, _fecha_corta(fecha))
    _pie(c, pagina)
    c.showPage()
    c.save()
    return buf.getvalue()
