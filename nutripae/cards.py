"""Tarjetas QR por estudiante: el QR contiene solo el código de la tarjeta."""
from __future__ import annotations

import io
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

import qrcode
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O/1/I
LARGO = 10

LOGO = Path(__file__).resolve().parent / "web" / "static" / "img" / "logo-impresion.png"

MORADO = (0x4C / 255, 0x17 / 255, 0xC1 / 255)
TINTA = (0x1F / 255, 0x1A / 255, 0x3D / 255)

PAGINA_W, PAGINA_H = 215.9 * mm, 279.4 * mm  # carta
TARJ_W, TARJ_H = 85 * mm, 55 * mm
MARGEN = 10 * mm
COLUMNAS, FILAS = 2, 4
POR_HOJA = COLUMNAS * FILAS


def _codigo_nuevo() -> str:
    return "".join(secrets.choice(ALFABETO) for _ in range(LARGO))


def asignar_tarjeta(con: sqlite3.Connection, estudiante_id: int) -> str:
    e = con.execute("SELECT consentimiento FROM estudiantes WHERE id=?", (estudiante_id,)).fetchone()
    if e is None or not e["consentimiento"]:
        raise ValueError("sin consentimiento")
    codigo = _codigo_nuevo()
    while con.execute("SELECT 1 FROM tarjetas WHERE codigo=?", (codigo,)).fetchone():
        codigo = _codigo_nuevo()
    con.execute("UPDATE tarjetas SET activa=0 WHERE estudiante_id=? AND activa=1", (estudiante_id,))
    con.execute("INSERT INTO tarjetas(codigo, estudiante_id, activa, creada) VALUES(?,?,1,?)",
                (codigo, estudiante_id, datetime.now().isoformat(timespec="seconds")))
    con.commit()
    return codigo


def anular_tarjeta(con: sqlite3.Connection, codigo: str) -> None:
    con.execute("UPDATE tarjetas SET activa=0 WHERE codigo=?", (codigo,))
    con.commit()


def tarjeta_activa(con: sqlite3.Connection, estudiante_id: int) -> str | None:
    r = con.execute("SELECT codigo FROM tarjetas WHERE estudiante_id=? AND activa=1 "
                    "ORDER BY creada DESC, rowid DESC LIMIT 1", (estudiante_id,)).fetchone()
    return r[0] if r else None


def _qr(codigo: str) -> ImageReader:
    buf = io.BytesIO()
    qrcode.make(codigo).save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _tarjeta(c: canvas.Canvas, x: float, y: float, nombre: str, grado: str, grupo: str,
             sede: str, codigo: str) -> None:
    """Dibuja una tarjeta con su esquina inferior izquierda en (x, y)."""
    c.setStrokeColorRGB(*MORADO)
    c.setLineWidth(1.2)
    c.roundRect(x, y, TARJ_W, TARJ_H, 4 * mm)

    if LOGO.exists():
        c.drawImage(str(LOGO), x + 4 * mm, y + TARJ_H - 14 * mm, width=30 * mm, height=10 * mm,
                    preserveAspectRatio=True, anchor="nw", mask="auto")

    qr = 32 * mm
    qx, qy = x + TARJ_W - qr - 4 * mm, y + TARJ_H - qr - 6 * mm
    c.drawImage(_qr(codigo), qx, qy, width=qr, height=qr)
    c.setFillColorRGB(*TINTA)
    c.setFont("Helvetica", 6)
    c.drawCentredString(qx + qr / 2, qy - 2.5 * mm, codigo)

    ancho_texto = qx - (x + 4 * mm) - 2 * mm
    c.setFillColorRGB(*MORADO)
    c.setFont("Helvetica-Bold", 11)
    lineas = simpleSplit(nombre, "Helvetica-Bold", 11, ancho_texto)[:2]
    ty = y + TARJ_H - 22 * mm
    for ln in lineas:
        c.drawString(x + 4 * mm, ty, ln)
        ty -= 5 * mm
    c.setFillColorRGB(*TINTA)
    c.setFont("Helvetica", 8)
    c.drawString(x + 4 * mm, y + 14 * mm, f"{grado} · {grupo}"[:40])
    for i, ln in enumerate(simpleSplit(sede, "Helvetica", 8, ancho_texto)[:2]):
        c.drawString(x + 4 * mm, y + 9.5 * mm - i * 3.5 * mm, ln)


def pdf_curso(con: sqlite3.Connection, sede: str, grado: str, grupo: str) -> bytes:
    filas = con.execute(
        "SELECT * FROM estudiantes WHERE activo=1 AND consentimiento=1 AND sede=? AND grado=? AND grupo=? "
        "ORDER BY orden, id", (sede, grado, grupo)).fetchall()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGINA_W, PAGINA_H))
    c.setTitle(f"Tarjetas {sede} {grado} {grupo}")
    if not filas:
        c.setFont("Helvetica", 12)
        c.drawString(MARGEN, PAGINA_H - MARGEN - 12, "No hay estudiantes con consentimiento en este curso.")
        c.showPage()
        c.save()
        return buf.getvalue()

    for i, e in enumerate(filas):
        pos = i % POR_HOJA
        if i and pos == 0:
            c.showPage()
        col, fila = pos % COLUMNAS, pos // COLUMNAS
        x = MARGEN + col * TARJ_W
        y = PAGINA_H - MARGEN - (fila + 1) * TARJ_H
        codigo = tarjeta_activa(con, e["id"]) or asignar_tarjeta(con, e["id"])
        _tarjeta(c, x, y, e["nombre"], e["grado"], e["grupo"], e["sede"], codigo)
    c.showPage()
    c.save()
    return buf.getvalue()
