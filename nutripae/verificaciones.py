"""Guardado y corrección de verificaciones."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime

from . import balance, db, foods
from .analyze import Analisis
from .balance import Porcion, Veredicto
from .overlay import reducir


class CorreccionInvalida(ValueError):
    """La corrección pedida no se puede aplicar."""


def _porcion_dict(p: Porcion) -> dict:
    d = asdict(p)
    return d


def _porcion_desde(d: dict) -> Porcion:
    d = dict(d)
    if d.get("poligono") is not None:
        d["poligono"] = [tuple(pt) for pt in d["poligono"]]
    d["bbox"] = tuple(d.get("bbox", (0, 0, 1, 1)))
    return Porcion(**d)


def guardar(con: sqlite3.Connection, settings, analisis: Analisis, *, estudiante,
            sede: str, grado: str, usuario_id: int, modo: str) -> int:
    escritos: list = []
    try:
        consiente = modo != "demo" and estudiante is not None and estudiante["consentimiento"] == 1
        ahora = datetime.now()
        v = analisis.veredicto
        cur = con.execute(
            "INSERT INTO verificaciones(ts, estudiante_id, sede, grado, usuario_id, modo, semaforo, "
            "razon_grupo, porciones, nutrientes, total_g, foto, corregida) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,0)",
            (ahora.isoformat(timespec="seconds"), estudiante["id"] if consiente else None, sede, grado,
             usuario_id, modo, v.semaforo, v.razon_grupo,
             json.dumps([_porcion_dict(p) for p in v.porciones]),
             json.dumps(v.nutrientes), v.total_g))
        vid = cur.lastrowid
        if consiente:
            rel = f"{ahora:%Y}/{ahora:%m}/{vid}.jpg"
            destino = settings.fotos_dir / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            escritos.append(destino)
            analisis.foto_anotada.convert("RGB").save(destino, "JPEG", quality=85)
            con.execute("UPDATE verificaciones SET foto=? WHERE id=?", (rel, vid))
            hoy = ahora.strftime("%Y-%m-%d")
            n = con.execute(
                "SELECT COUNT(*) FROM fotos_entrenamiento f JOIN verificaciones v ON v.id=f.verificacion_id "
                "WHERE v.sede=? AND substr(v.ts,1,10)=?", (sede, hoy)).fetchone()[0]
            if n < settings.muestra_entrenamiento_dia:
                ruta = f"entrenamiento/{vid}.jpg"
                destino = settings.fotos_dir / ruta
                destino.parent.mkdir(parents=True, exist_ok=True)
                escritos.append(destino)
                reducir(analisis.original, 1280).convert("RGB").save(destino, "JPEG", quality=90)
                con.execute("INSERT INTO fotos_entrenamiento(verificacion_id, ruta, ts) VALUES(?,?,?)",
                            (vid, ruta, ahora.isoformat(timespec="seconds")))
        con.commit()
    except BaseException:
        con.rollback()
        for f in escritos:
            f.unlink(missing_ok=True)
        raise
    return vid


def corregir(con: sqlite3.Connection, verificacion_id: int, indice: int,
             alimento_nuevo: str, usuario_id: int) -> Veredicto:
    fila = con.execute("SELECT * FROM verificaciones WHERE id=?", (verificacion_id,)).fetchone()
    if fila is None:
        raise CorreccionInvalida("No encontramos esa verificación.")
    cat = foods.catalogo(con)
    if alimento_nuevo not in cat:
        raise CorreccionInvalida("Ese alimento no está en el catálogo.")
    porciones = [_porcion_desde(d) for d in json.loads(fila["porciones"])]
    if not 0 <= indice < len(porciones):
        raise CorreccionInvalida("Esa porción no existe.")
    if porciones[indice].estado == "falta" or porciones[indice].alimento.startswith("falta_"):
        raise CorreccionInvalida("Un grupo que falta no se puede corregir.")
    antes = porciones[indice].alimento
    p = porciones[indice]
    p.alimento = alimento_nuevo
    p.nombre = cat[alimento_nuevo][0]
    p.grupo = cat[alimento_nuevo][1]
    porciones = [x for x in porciones if not x.alimento.startswith("falta_")]
    umbrales = db.param(con, "umbrales", balance.UMBRALES_INICIALES)
    v = balance.evaluar(porciones, fila["grado"], umbrales)
    con.execute(
        "UPDATE verificaciones SET porciones=?, semaforo=?, razon_grupo=?, nutrientes=?, total_g=?, "
        "corregida=1 WHERE id=?",
        (json.dumps([_porcion_dict(x) for x in v.porciones]), v.semaforo, v.razon_grupo,
         json.dumps(v.nutrientes), v.total_g, verificacion_id))
    con.execute(
        "INSERT INTO correcciones(verificacion_id, indice, antes, despues, usuario_id, ts) VALUES(?,?,?,?,?,?)",
        (verificacion_id, indice, antes, alimento_nuevo, usuario_id,
         datetime.now().isoformat(timespec="seconds")))
    con.commit()
    return v
