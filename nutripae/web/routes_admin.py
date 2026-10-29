"""Administración: usuarios y parámetros (umbrales del plato y alimentos extra)."""
from __future__ import annotations

import copy
import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from nutripae import auth, db, foods
from nutripae.balance import UMBRALES_INICIALES

router = APIRouter()

_SLUG = re.compile(r"^[a-z0-9_]{2,40}$")
# campo del formulario -> ruta dentro del diccionario de umbrales, tipo de límite
_CAMPOS = {
    "objetivo_verdura_fruta": (("objetivo", "verdura_fruta"), "proporcion"),
    "objetivo_proteina": (("objetivo", "proteina"), "proporcion"),
    "objetivo_energetico": (("objetivo", "energetico"), "proporcion"),
    "factor_corto": (("factor_corto",), "positivo"),
    "factor_excedido": (("factor_excedido",), "positivo"),
    "plato_minimo_preescolar": (("plato_minimo_g", "preescolar"), "positivo"),
    "plato_minimo_primaria": (("plato_minimo_g", "primaria"), "positivo"),
    "plato_minimo_secundaria": (("plato_minimo_g", "secundaria"), "positivo"),
}


def _usuarios(con) -> list[dict]:
    filas = con.execute("SELECT * FROM usuarios ORDER BY activo DESC, usuario").fetchall()
    return [{"id": f["id"], "usuario": f["usuario"], "nombre": f["nombre"], "activo": f["activo"],
             "roles": sorted(auth.roles_de(con, f["id"])), "sedes": sorted(auth.sedes_de(con, f["id"]))}
            for f in filas]


def _vista_usuarios(request: Request, mensaje: str | None = None, error: str | None = None,
                    status: int = 200, previo: dict | None = None):
    con = request.app.state.con
    sedes = [f["sede"] for f in con.execute(
        "SELECT DISTINCT sede FROM estudiantes WHERE sede IS NOT NULL AND sede<>'' ORDER BY sede")]
    return request.app.state.templates.TemplateResponse(
        request, "admin_usuarios.html",
        {"usuarios": _usuarios(con), "roles": sorted(auth.ROLES), "sedes": sedes,
         "mensaje": mensaje, "error": error, "previo": previo or {}, "yo": request.state.usuario["id"]},
        status_code=status)


@router.get("/admin/usuarios")
def usuarios(request: Request, usuario=Depends(auth.requiere("admin"))):
    return _vista_usuarios(request, mensaje="Usuario desactivado." if "desactivado" in request.query_params else None)


@router.post("/admin/usuarios")
async def crear_usuario(request: Request, usuario=Depends(auth.requiere("admin"))):
    f = await request.form()
    datos = {"usuario": (f.get("usuario") or "").strip(), "nombre": (f.get("nombre") or "").strip(),
             "roles": f.getlist("roles"), "sedes": f.getlist("sedes")}
    contrasena = f.get("contrasena") or ""
    otra = (f.get("otra_sede") or "").strip()
    sedes = [s.strip() for s in datos["sedes"] if s.strip()] + ([otra] if otra else [])

    def error(msg: str):
        return _vista_usuarios(request, error=msg, status=400, previo=datos)

    if not datos["usuario"]:
        return error("Escribe el nombre de usuario.")
    if not datos["nombre"]:
        return error("Escribe el nombre de la persona.")
    if len(contrasena) < 6:
        return error("La contraseña debe tener al menos 6 caracteres.")
    if not datos["roles"]:
        return error("Elige al menos un rol.")
    try:
        auth.crear_usuario(request.app.state.con, datos["usuario"], datos["nombre"], contrasena,
                           datos["roles"], sedes)
    except ValueError as e:
        return error(str(e))
    return RedirectResponse("/admin/usuarios", status_code=302)


@router.post("/admin/usuarios/{usuario_id}/desactivar")
def desactivar(usuario_id: int, request: Request, usuario=Depends(auth.requiere("admin"))):
    if usuario_id == usuario["id"]:
        return _vista_usuarios(request, error="No puedes desactivar tu propio usuario", status=400)
    con = request.app.state.con
    con.execute("UPDATE usuarios SET activo=0 WHERE id=?", (usuario_id,))
    con.commit()
    return RedirectResponse("/admin/usuarios?desactivado=1", status_code=302)


# ---------------------------------------------------------------- parámetros

def _umbrales_actuales(con) -> dict:
    actual = db.param(con, "umbrales", None) or {}
    base = copy.deepcopy(UMBRALES_INICIALES)
    for k, v in actual.items():  # completa lo que falte con los valores iniciales
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            base[k].update(v)
        else:
            base[k] = v
    return base


def _vista_parametros(request: Request, mensaje: str | None = None, error: str | None = None,
                      status: int = 200):
    con = request.app.state.con
    u = _umbrales_actuales(con)
    valores = {campo: (u[ruta[0]][ruta[1]] if len(ruta) == 2 else u[ruta[0]])
               for campo, (ruta, _) in _CAMPOS.items()}
    ids_extra = {e["clave"] for e in foods.extras(con)}
    catalogo = [{"clave": k, "nombre": n, "grupo": foods.GRUPO_LABEL[g], "extra": k in ids_extra}
                for k, (n, g) in sorted(foods.catalogo(con).items(), key=lambda kv: kv[1][0])]
    q = request.query_params
    if mensaje is None:
        mensaje = {"guardado": "Parámetros guardados.", "restablecido": "Valores iniciales restablecidos.",
                   "agregado": "Alimento agregado.", "quitado": "Alimento quitado."}.get(
            next((k for k in q if k in ("guardado", "restablecido", "agregado", "quitado")), ""))
    return request.app.state.templates.TemplateResponse(
        request, "admin_parametros.html",
        {"v": valores, "catalogo": catalogo, "grupos": [(g, foods.GRUPO_LABEL[g]) for g in foods.GRUPOS],
         "mensaje": mensaje, "error": error}, status_code=status)


@router.get("/admin/parametros")
def parametros(request: Request, usuario=Depends(auth.requiere("admin"))):
    return _vista_parametros(request)


@router.post("/admin/parametros")
async def guardar_parametros(request: Request, usuario=Depends(auth.requiere("admin"))):
    con = request.app.state.con
    f = await request.form()
    u = _umbrales_actuales(con)
    for campo, (ruta, tipo) in _CAMPOS.items():
        crudo = f.get(campo)
        if crudo is None or str(crudo).strip() == "":
            continue
        try:
            x = float(str(crudo).replace(",", "."))
        except ValueError:
            return _vista_parametros(request, error="Escribe solo números en los parámetros.", status=400)
        if not (0 < x <= 1 if tipo == "proporcion" else x > 0) or x != x or x == float("inf"):
            msg = "Los objetivos deben estar entre 0 y 1." if tipo == "proporcion" \
                else "Los factores y los pesos mínimos deben ser mayores que 0."
            return _vista_parametros(request, error=msg, status=400)
        if len(ruta) == 2:
            u[ruta[0]][ruta[1]] = x
        else:
            u[ruta[0]] = x
    db.set_param(con, "umbrales", u)
    return RedirectResponse("/admin/parametros?guardado=1", status_code=302)


@router.post("/admin/parametros/restablecer")
def restablecer(request: Request, usuario=Depends(auth.requiere("admin"))):
    db.set_param(request.app.state.con, "umbrales", copy.deepcopy(UMBRALES_INICIALES))
    return RedirectResponse("/admin/parametros?restablecido=1", status_code=302)


@router.post("/admin/parametros/alimentos")
def agregar_alimento(request: Request, clave: str = Form(""), nombre: str = Form(""), grupo: str = Form(""),
                     usuario=Depends(auth.requiere("admin"))):
    con = request.app.state.con
    clave, nombre = clave.strip(), nombre.strip()
    if not _SLUG.match(clave):
        return _vista_parametros(request, status=400, error="El identificador usa solo letras minúsculas, "
                                 "números y guion bajo (por ejemplo: arepa_queso).")
    if not nombre:
        return _vista_parametros(request, status=400, error="Escribe el nombre del alimento.")
    if grupo not in foods.GRUPOS:
        return _vista_parametros(request, status=400, error="Elige un grupo válido.")
    if clave in foods.catalogo(con):
        return _vista_parametros(request, status=400, error="Ya existe un alimento con ese identificador.")
    lista = db.param(con, "alimentos_extra", [])
    lista.append({"clave": clave, "nombre": nombre, "grupo": grupo})
    db.set_param(con, "alimentos_extra", lista)
    return RedirectResponse("/admin/parametros?agregado=1", status_code=302)


@router.post("/admin/parametros/alimentos/{clave}/quitar")
def quitar_alimento(clave: str, request: Request, usuario=Depends(auth.requiere("admin"))):
    con = request.app.state.con
    lista = [e for e in db.param(con, "alimentos_extra", []) if e["clave"] != clave]
    db.set_param(con, "alimentos_extra", lista)
    return RedirectResponse("/admin/parametros?quitado=1", status_code=302)
