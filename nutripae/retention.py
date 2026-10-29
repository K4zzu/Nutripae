"""Retención de fotos: al cerrar el año escolar se borran las fotos y se conservan los datos (spec §10)."""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from nutripae.config import Settings


def _borrar_archivo(base: Path, ruta: str) -> None:
    """Borra un archivo solo si queda dentro de la carpeta de fotos; si ya no existe, no pasa nada."""
    archivo = (base / ruta).resolve()
    if archivo.is_relative_to(base) and archivo.is_file():
        archivo.unlink()


def borrar_fotos_antes(con: sqlite3.Connection, settings: Settings, fecha: date) -> int:
    """Borra las fotos de historial y de entrenamiento tomadas antes de `fecha`.

    Las verificaciones se conservan con `foto=NULL`; las filas de `fotos_entrenamiento` se eliminan.
    Devuelve cuántas filas se tocaron (historial + entrenamiento).
    """
    base = settings.fotos_dir.resolve()
    limite = fecha.isoformat()
    tocadas = 0
    try:
        historial = con.execute(
            "SELECT id, foto FROM verificaciones WHERE foto IS NOT NULL AND substr(ts,1,10) < ?",
            (limite,)).fetchall()
        for vid, ruta in historial:
            _borrar_archivo(base, ruta)
            con.execute("UPDATE verificaciones SET foto=NULL WHERE id=?", (vid,))
        entrenamiento = con.execute(
            "SELECT id, ruta FROM fotos_entrenamiento WHERE substr(ts,1,10) < ?", (limite,)).fetchall()
        for fid, ruta in entrenamiento:
            _borrar_archivo(base, ruta)
            con.execute("DELETE FROM fotos_entrenamiento WHERE id=?", (fid,))
        tocadas = len(historial) + len(entrenamiento)
        con.commit()
    except Exception:
        con.rollback()
        raise
    return tocadas
