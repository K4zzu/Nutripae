"""Historial por niño, resumen por sede y auditoría de consultas.

Solo cuentan las verificaciones con cámara; el modo de práctica nunca entra aquí.
Por día cuenta la última verificación (la de mayor hora); las anteriores son intentos.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta


def periodo(desde: str | None, hasta: str | None, dias: int = 30) -> tuple[date, date]:
    """Convierte los parámetros de la URL en fechas; por defecto, los últimos `dias` días."""
    def leer(texto):
        try:
            return date.fromisoformat(texto) if texto else None
        except ValueError:
            return None
    fin = leer(hasta) or date.today()
    ini = leer(desde) or fin - timedelta(days=dias)
    return (ini, fin) if ini <= fin else (fin, ini)


def _json(texto, defecto):
    try:
        return json.loads(texto) if texto else defecto
    except ValueError:
        return defecto


def _ultimas(filas) -> dict[date, list]:
    """Agrupa filas (ordenadas por ts) por fecha."""
    por_dia: dict[date, list] = {}
    for f in filas:
        por_dia.setdefault(datetime.fromisoformat(f["ts"]).date(), []).append(f)
    return por_dia


def _filas_estudiante(con, estudiante_id, desde, hasta):
    return con.execute(
        "SELECT * FROM verificaciones WHERE estudiante_id=? AND modo='camara' "
        "AND substr(ts,1,10) BETWEEN ? AND ? ORDER BY ts, id",
        (estudiante_id, desde.isoformat(), hasta.isoformat())).fetchall()


def dias_estudiante(con: sqlite3.Connection, estudiante_id: int, desde: date, hasta: date) -> list[dict]:
    salida = []
    for fecha, filas in _ultimas(_filas_estudiante(con, estudiante_id, desde, hasta)).items():
        u = filas[-1]
        salida.append({
            "fecha": fecha, "intentos": len(filas),
            "ultima": {
                "id": u["id"], "semaforo": u["semaforo"], "razon_grupo": u["razon_grupo"],
                "porciones": _json(u["porciones"], []), "nutrientes": _json(u["nutrientes"], {}),
                "total_g": u["total_g"], "foto": u["foto"], "ts": u["ts"],
            }})
    return sorted(salida, key=lambda d: d["fecha"], reverse=True)


def faltas_por_grupo(con: sqlite3.Connection, estudiante_id: int, desde: date, hasta: date) -> dict[str, int]:
    """Días cuya última verificación tuvo ese grupo en falta."""
    cuenta: Counter = Counter()
    for d in dias_estudiante(con, estudiante_id, desde, hasta):
        grupos = {p.get("grupo") for p in d["ultima"]["porciones"] if p.get("estado") == "falta"}
        cuenta.update(g for g in grupos if g)
    return dict(cuenta)


def resumen_sede(con: sqlite3.Connection, sede: str, grado: str | None, desde: date, hasta: date) -> dict:
    sql = ("SELECT * FROM verificaciones WHERE sede=? AND modo='camara' "
           "AND substr(ts,1,10) BETWEEN ? AND ?")
    args = [sede, desde.isoformat(), hasta.isoformat()]
    if grado:
        sql += " AND grado=?"
        args.append(grado)
    filas = con.execute(sql + " ORDER BY ts, id", args).fetchall()

    # La última verificación de cada niño por día; las filas sin niño (tarjeta inválida) cuentan sueltas.
    ultimas: dict[tuple, sqlite3.Row] = {}
    for f in filas:
        clave = (f["ts"][:10], f["estudiante_id"] if f["estudiante_id"] is not None else ("anonimo", f["id"]))
        ultimas[clave] = f

    por_fecha: dict[date, list] = {}
    for (dia, _), f in ultimas.items():
        por_fecha.setdefault(date.fromisoformat(dia), []).append(f)
    por_dia = [(fecha, round(100 * sum(f["semaforo"] == "verde" for f in lista) / len(lista), 1), len(lista))
               for fecha, lista in sorted(por_fecha.items())]

    faltas: Counter = Counter()
    no_aptos = 0
    for f in ultimas.values():
        for p in _json(f["porciones"], []):
            if p.get("estado") == "falta" and p.get("grupo"):
                faltas[p["grupo"]] += 1
    for f in filas:
        if any(p.get("estado") == "no_apto" for p in _json(f["porciones"], [])):
            no_aptos += 1
    return {"por_dia": por_dia,
            "grupo_mas_falta": faltas.most_common(1)[0][0] if faltas else None,
            "no_aptos": no_aptos}


def auditar(con: sqlite3.Connection, usuario_id: int, accion: str, estudiante_id: int | None = None) -> None:
    con.execute("INSERT INTO auditoria(ts, usuario_id, accion, estudiante_id) VALUES(?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), usuario_id, accion, estudiante_id))
    con.commit()
