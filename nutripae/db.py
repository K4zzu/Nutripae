"""Base de datos SQLite: conexión, esquema y parámetros."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE NOT NULL,
    nombre TEXT,
    hash TEXT NOT NULL,
    activo INT DEFAULT 1
);
CREATE TABLE IF NOT EXISTS usuario_roles(
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    rol TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usuario_sedes(
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    sede TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS estudiantes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT UNIQUE NOT NULL,
    nombre TEXT,
    grado TEXT,
    grupo TEXT,
    sede TEXT,
    orden INT,
    consentimiento INT DEFAULT 0,
    activo INT DEFAULT 1
);
CREATE TABLE IF NOT EXISTS tarjetas(
    codigo TEXT PRIMARY KEY,
    estudiante_id INTEGER REFERENCES estudiantes(id),
    activa INT DEFAULT 1,
    creada TEXT
);
CREATE TABLE IF NOT EXISTS verificaciones(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    estudiante_id INTEGER REFERENCES estudiantes(id),
    sede TEXT,
    grado TEXT,
    usuario_id INTEGER REFERENCES usuarios(id),
    modo TEXT,
    semaforo TEXT,
    razon_grupo TEXT,
    porciones TEXT,
    nutrientes TEXT,
    total_g REAL,
    foto TEXT,
    corregida INT DEFAULT 0
);
CREATE TABLE IF NOT EXISTS correcciones(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verificacion_id INTEGER NOT NULL REFERENCES verificaciones(id),
    indice INT,
    antes TEXT,
    despues TEXT,
    usuario_id INTEGER REFERENCES usuarios(id),
    ts TEXT
);
CREATE TABLE IF NOT EXISTS fotos_entrenamiento(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verificacion_id INTEGER REFERENCES verificaciones(id),
    ruta TEXT NOT NULL,
    ts TEXT
);
CREATE TABLE IF NOT EXISTS auditoria(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    usuario_id INTEGER REFERENCES usuarios(id),
    accion TEXT NOT NULL,
    estudiante_id INTEGER REFERENCES estudiantes(id)
);
CREATE TABLE IF NOT EXISTS parametros(
    clave TEXT PRIMARY KEY,
    valor TEXT
);
"""


def conectar(path: Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(ESQUEMA)
    con.commit()
    return con


def param(con: sqlite3.Connection, clave: str, default):
    fila = con.execute("SELECT valor FROM parametros WHERE clave=?", (clave,)).fetchone()
    return json.loads(fila["valor"]) if fila else default


def set_param(con: sqlite3.Connection, clave: str, valor) -> None:
    con.execute("INSERT INTO parametros(clave, valor) VALUES(?, ?) "
                "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
                (clave, json.dumps(valor)))
    con.commit()


def estudiante(con: sqlite3.Connection, id: int) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM estudiantes WHERE id=?", (id,)).fetchone()


def estudiante_por_tarjeta(con: sqlite3.Connection, codigo: str) -> sqlite3.Row | None:
    return con.execute(
        "SELECT e.* FROM tarjetas t JOIN estudiantes e ON e.id=t.estudiante_id "
        "WHERE t.codigo=? AND t.activa=1 AND e.activo=1", (codigo,)).fetchone()
