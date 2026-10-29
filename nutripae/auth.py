"""Usuarios, contraseñas, roles y dependencias de acceso."""
from __future__ import annotations

import sqlite3

import bcrypt
from fastapi import HTTPException, Request

ROLES = {"docente", "nutricionista", "admin"}


def crear_usuario(con: sqlite3.Connection, usuario: str, nombre: str, contrasena: str,
                  roles: list[str], sedes: list[str]) -> int:
    invalidos = set(roles) - ROLES
    if invalidos:
        raise ValueError(f"Rol no válido: {', '.join(sorted(invalidos))}")
    hash_ = bcrypt.hashpw(contrasena.encode(), bcrypt.gensalt()).decode()
    try:
        cur = con.execute("INSERT INTO usuarios(usuario, nombre, hash) VALUES (?,?,?)",
                          (usuario, nombre, hash_))
    except sqlite3.IntegrityError:
        raise ValueError("El usuario ya existe") from None
    uid = cur.lastrowid
    con.executemany("INSERT INTO usuario_roles(usuario_id, rol) VALUES (?,?)",
                    [(uid, r) for r in sorted(set(roles))])
    con.executemany("INSERT INTO usuario_sedes(usuario_id, sede) VALUES (?,?)",
                    [(uid, s) for s in sorted(set(sedes))])
    con.commit()
    return uid


def actualizar_usuario(con: sqlite3.Connection, usuario_id: int, *, roles: list[str], sedes: list[str],
                       activo: bool, contrasena: str | None = None) -> None:
    """Reemplaza roles y sedes, fija si está activo y, si se da, cambia la contraseña."""
    invalidos = set(roles) - ROLES
    if invalidos:
        raise ValueError(f"Rol no válido: {', '.join(sorted(invalidos))}")
    try:
        con.execute("UPDATE usuarios SET activo=? WHERE id=?", (1 if activo else 0, usuario_id))
        if contrasena:
            con.execute("UPDATE usuarios SET hash=? WHERE id=?",
                        (bcrypt.hashpw(contrasena.encode(), bcrypt.gensalt()).decode(), usuario_id))
        con.execute("DELETE FROM usuario_roles WHERE usuario_id=?", (usuario_id,))
        con.execute("DELETE FROM usuario_sedes WHERE usuario_id=?", (usuario_id,))
        con.executemany("INSERT INTO usuario_roles(usuario_id, rol) VALUES (?,?)",
                        [(usuario_id, r) for r in sorted(set(roles))])
        con.executemany("INSERT INTO usuario_sedes(usuario_id, sede) VALUES (?,?)",
                        [(usuario_id, s) for s in sorted(set(sedes))])
        con.commit()
    except Exception:
        con.rollback()
        raise


def verificar(con: sqlite3.Connection, usuario: str, contrasena: str) -> sqlite3.Row | None:
    fila = con.execute("SELECT * FROM usuarios WHERE usuario=?", (usuario,)).fetchone()
    if fila is None or not fila["activo"]:
        return None
    try:
        ok = bcrypt.checkpw(contrasena.encode(), fila["hash"].encode())
    except ValueError:
        return None
    return fila if ok else None


def roles_de(con: sqlite3.Connection, usuario_id: int) -> set[str]:
    return {f["rol"] for f in con.execute(
        "SELECT rol FROM usuario_roles WHERE usuario_id=?", (usuario_id,))}


def sedes_de(con: sqlite3.Connection, usuario_id: int) -> set[str]:
    return {f["sede"] for f in con.execute(
        "SELECT sede FROM usuario_sedes WHERE usuario_id=?", (usuario_id,))}


def usuario_actual(request: Request) -> sqlite3.Row:
    """Usuario de la sesión; si no hay uno activo, redirige a /entrar."""
    con = request.app.state.con
    uid = request.session.get("usuario_id")
    fila = con.execute("SELECT * FROM usuarios WHERE id=? AND activo=1", (uid,)).fetchone() \
        if uid is not None else None
    if fila is None:
        request.session.clear()
        raise HTTPException(status_code=302, headers={"Location": "/entrar"})
    request.state.usuario = fila
    request.state.roles = roles_de(con, fila["id"])
    request.state.sedes = sedes_de(con, fila["id"])
    return fila


def requiere(*roles: str):
    """Dependencia que exige al menos uno de los roles dados."""
    def dependencia(request: Request) -> sqlite3.Row:
        fila = usuario_actual(request)
        if not request.state.roles & set(roles):
            raise HTTPException(status_code=403, detail="No tienes permiso para esta sección")
        return fila
    return dependencia
