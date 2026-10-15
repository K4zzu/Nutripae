"""Persistencia local en SQLite (una base por estación; se sincroniza al tablero central)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "nutripae.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entregas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    sede TEXT NOT NULL,
    bandeja TEXT NOT NULL,
    grado TEXT NOT NULL,
    minuta TEXT NOT NULL,
    peso_g REAL,
    semaforo TEXT NOT NULL,
    aprobada INTEGER NOT NULL,
    corregida INTEGER DEFAULT 0,
    alertas TEXT,
    porciones TEXT,        -- json alimento -> gramos servidos
    nutrientes TEXT,       -- json
    backend TEXT
);
CREATE TABLE IF NOT EXISTS devoluciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    entrega_id INTEGER,
    bandeja TEXT NOT NULL,
    peso_g REAL,
    sobrante TEXT,         -- json alimento -> gramos sobrantes
    consumido TEXT,        -- json alimento -> gramos consumidos
    nutrientes TEXT,       -- json nutrientes consumidos
    FOREIGN KEY(entrega_id) REFERENCES entregas(id)
);
"""


def conectar(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, check_same_thread=False)
    con.executescript(_SCHEMA)
    return con


def registrar_entrega(con, *, sede, bandeja, grado, minuta, peso_g, resultado, backend, corregida=False, ts=None) -> int:
    cur = con.execute(
        "INSERT INTO entregas (ts,sede,bandeja,grado,minuta,peso_g,semaforo,aprobada,corregida,alertas,porciones,nutrientes,backend)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ((ts or datetime.now()).isoformat(timespec="seconds"), sede, bandeja, grado, minuta, peso_g,
         resultado.semaforo, int(resultado.aprobada), int(corregida), json.dumps(resultado.alertas, ensure_ascii=False),
         json.dumps(resultado.porciones()), json.dumps(resultado.nutrientes), backend),
    )
    con.commit()
    return cur.lastrowid


def registrar_devolucion(con, *, entrega_id, bandeja, peso_g, sobrante, consumido, nutrientes, ts=None) -> int:
    cur = con.execute(
        "INSERT INTO devoluciones (ts,entrega_id,bandeja,peso_g,sobrante,consumido,nutrientes) VALUES (?,?,?,?,?,?,?)",
        ((ts or datetime.now()).isoformat(timespec="seconds"), entrega_id, bandeja, peso_g,
         json.dumps(sobrante), json.dumps(consumido), json.dumps(nutrientes)),
    )
    con.commit()
    return cur.lastrowid


def ultima_entrega_pendiente(con, bandeja: str):
    """Entrega más reciente de esa bandeja sin devolución registrada."""
    row = con.execute(
        "SELECT e.id, e.grado, e.minuta, e.porciones FROM entregas e LEFT JOIN devoluciones d ON d.entrega_id = e.id"
        " WHERE e.bandeja = ? AND d.id IS NULL ORDER BY e.id DESC LIMIT 1", (bandeja,)).fetchone()
    if not row:
        return None
    return {"id": row[0], "grado": row[1], "minuta": row[2], "porciones": json.loads(row[3])}


def cargar_entregas(con) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM entregas ORDER BY ts", con)
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"])
    df["porciones"] = df["porciones"].apply(json.loads)
    df["nutrientes"] = df["nutrientes"].apply(json.loads)
    df["alertas"] = df["alertas"].apply(json.loads)
    df["kcal"] = df["nutrientes"].apply(lambda n: n.get("kcal", 0))
    df["fecha"] = df["ts"].dt.date
    return df


def cargar_devoluciones(con) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM devoluciones ORDER BY ts", con)
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"])
    for c in ("sobrante", "consumido", "nutrientes"):
        df[c] = df[c].apply(json.loads)
    df["kcal_consumidas"] = df["nutrientes"].apply(lambda n: n.get("kcal", 0))
    df["fecha"] = df["ts"].dt.date
    return df


def vaciar(con):
    con.executescript("DELETE FROM devoluciones; DELETE FROM entregas;")
    con.commit()
