"""Base de datos SQLite: conexión, esquema y parámetros."""
from __future__ import annotations

import json
import sqlite3
import threading
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
    con = sqlite3.connect(path, check_same_thread=False, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(ESQUEMA)
    con.commit()
    return con


class ConexionPorHilo:
    """Una conexión SQLite por hilo, creada al primer uso con `conectar(path)`.

    Se usa como una conexión normal: cada atributo (`execute`, `commit`, `rollback`,
    `row_factory`, `in_transaction`…) se resuelve sobre la conexión del hilo actual, así
    la transacción de una petición nunca se mezcla con la de otra.
    """

    def __init__(self, path: Path):
        object.__setattr__(self, "_path", Path(path))
        object.__setattr__(self, "_local", threading.local())
        object.__setattr__(self, "_todas", [])
        object.__setattr__(self, "_cerrojo", threading.Lock())

    def actual(self) -> sqlite3.Connection:
        con = getattr(self._local, "con", None)
        if con is None:
            con = conectar(self._path)
            self._local.con = con
            with self._cerrojo:
                self._todas.append(con)
        return con

    def __getattr__(self, nombre):
        return getattr(self.actual(), nombre)

    def __setattr__(self, nombre, valor):
        setattr(self.actual(), nombre, valor)

    def close(self) -> None:
        """Cierra las conexiones de todos los hilos."""
        with self._cerrojo:
            todas, self._todas[:] = list(self._todas), []
        for con in todas:
            try:
                con.close()
            except sqlite3.Error:
                pass
        self._local.con = None


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
