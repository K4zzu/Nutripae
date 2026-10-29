"""Estudiantes: carga desde Excel, búsqueda, siguiente en lista y consentimiento."""
from __future__ import annotations

import hashlib
import io
import re
import sqlite3
import unicodedata
from datetime import date
from pathlib import Path

import openpyxl

COLUMNAS = {"codigo", "nombre", "grado", "sede"}
OPCIONALES = {"grupo", "consentimiento"}
MAX_RESULTADOS = 20
_SI = {"si", "1", "true", "x", "verdadero"}


class ColumnaFaltante(ValueError):
    def __init__(self, columna: str):
        super().__init__(f"Falta la columna «{columna}» en el archivo")
        self.columna = columna


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _norm(texto) -> str:
    return _sin_tildes(str(texto or "").strip()).lower()


def _texto(valor) -> str:
    """Celda a texto; los números enteros de Excel (1023.0) pierden el decimal."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def normalizar_grado(texto) -> str:
    t = _norm(texto)
    if any(p in t for p in ("transici", "prescolar", "preescolar", "jardin", "parvulos")):
        return "preescolar"
    m = re.search(r"\d+", t)
    if m:
        n = int(m.group())
        if n == 0:
            return "preescolar"
        if n <= 5:
            return "primaria"
        if n <= 11:
            return "secundaria"
    raise ValueError(f"Grado no reconocido: «{texto}»")


def hash_codigo(codigo: str, secret: str) -> str:
    return hashlib.sha256((secret + codigo).encode()).hexdigest()


def _filas(ruta_o_bytes):
    origen = io.BytesIO(ruta_o_bytes) if isinstance(ruta_o_bytes, (bytes, bytearray)) else Path(ruta_o_bytes)
    wb = openpyxl.load_workbook(origen, read_only=True, data_only=True)
    try:
        yield from wb.worksheets[0].iter_rows(values_only=True)
    finally:
        wb.close()


def importar_excel(con: sqlite3.Connection, ruta_o_bytes, *, hash_documento: bool = True,
                   secret: str = "") -> dict:
    filas = _filas(ruta_o_bytes)
    cabecera = next(filas, None) or ()
    idx = {_norm(c): i for i, c in enumerate(cabecera) if c is not None}
    for col in ("codigo", "nombre", "grado", "sede"):
        if col not in idx:
            raise ColumnaFaltante(col)

    def celda(fila, col):
        i = idx.get(col)
        return _texto(fila[i]) if i is not None and i < len(fila) else ""

    creados = actualizados = 0
    errores: list[str] = []
    contador: dict[tuple, int] = {}
    try:
        for n, fila in enumerate(filas, start=2):
            if not any(c not in (None, "") for c in fila):
                continue
            codigo, nombre, sede = celda(fila, "codigo"), celda(fila, "nombre"), celda(fila, "sede")
            if not codigo or not nombre:
                errores.append(f"Fila {n}: falta el código o el nombre")
                continue
            try:
                grado = normalizar_grado(celda(fila, "grado"))
            except ValueError as e:
                errores.append(f"Fila {n}: {e}")
                continue
            grupo = celda(fila, "grupo") or celda(fila, "grado")
            if hash_documento and codigo.isdigit() and len(codigo) >= 6:
                codigo = hash_codigo(codigo, secret)
            consentimiento = 1 if _norm(celda(fila, "consentimiento")) in _SI else 0
            clave = (sede, grado, grupo)
            contador[clave] = contador.get(clave, 0) + 1
            existe = con.execute("SELECT 1 FROM estudiantes WHERE codigo=?", (codigo,)).fetchone()
            con.execute(
                "INSERT INTO estudiantes(codigo, nombre, grado, grupo, sede, orden, consentimiento, activo) "
                "VALUES(?,?,?,?,?,?,?,1) ON CONFLICT(codigo) DO UPDATE SET nombre=excluded.nombre, "
                "grado=excluded.grado, grupo=excluded.grupo, sede=excluded.sede, orden=excluded.orden, "
                "consentimiento=excluded.consentimiento, activo=1",
                (codigo, nombre, grado, grupo, sede, contador[clave], consentimiento))
            if existe:
                actualizados += 1
            else:
                creados += 1
        con.execute("UPDATE tarjetas SET activa=0 WHERE activa=1 AND estudiante_id IN "
                    "(SELECT id FROM estudiantes WHERE consentimiento=0)")
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {"creados": creados, "actualizados": actualizados, "errores": errores}


def buscar(con: sqlite3.Connection, q: str, sede: str, grado: str | None) -> list[sqlite3.Row]:
    """Cada palabra de `q` debe ser prefijo de alguna palabra del nombre (sin mayúsculas ni tildes)."""
    sql, args = "SELECT * FROM estudiantes WHERE activo=1 AND sede=?", [sede]
    if grado:
        sql += " AND grado=?"
        args.append(grado)
    palabras = _norm(q).split()
    salida = []
    for fila in con.execute(sql + " ORDER BY orden, id", args):
        nombre = _norm(fila["nombre"]).split()
        if all(any(n.startswith(p) for n in nombre) for p in palabras):
            salida.append(fila)
            if len(salida) == MAX_RESULTADOS:
                break
    return salida


def siguiente(con: sqlite3.Connection, sede: str, grado: str, grupo: str | None,
              hoy: date) -> sqlite3.Row | None:
    """Primer estudiante del grupo, por orden, sin verificación con cámara hoy.

    Sin grupo se recorren los grupos del grado en el orden en que llegaron en el archivo.
    """
    grupos = [grupo] if grupo else [r[0] for r in con.execute(
        "SELECT grupo FROM estudiantes WHERE activo=1 AND sede=? AND grado=? "
        "GROUP BY grupo ORDER BY MIN(id)", (sede, grado))]
    for g in grupos:
        fila = con.execute(
            "SELECT e.* FROM estudiantes e WHERE e.activo=1 AND e.sede=? AND e.grado=? AND e.grupo IS ? "
            "AND NOT EXISTS (SELECT 1 FROM verificaciones v WHERE v.estudiante_id=e.id "
            "AND v.modo='camara' AND substr(v.ts,1,10)=?) ORDER BY e.orden, e.id LIMIT 1",
            (sede, grado, g, hoy.isoformat())).fetchone()
        if fila:
            return fila
    return None


def set_consentimiento(con: sqlite3.Connection, estudiante_id: int, valor: bool) -> None:
    con.execute("UPDATE estudiantes SET consentimiento=? WHERE id=?", (1 if valor else 0, estudiante_id))
    if not valor:
        con.execute("UPDATE tarjetas SET activa=0 WHERE estudiante_id=?", (estudiante_id,))
    con.commit()


def dar_de_baja(con: sqlite3.Connection, estudiante_id: int) -> None:
    con.execute("UPDATE estudiantes SET activo=0 WHERE id=?", (estudiante_id,))
    con.execute("UPDATE tarjetas SET activa=0 WHERE estudiante_id=?", (estudiante_id,))
    con.commit()
