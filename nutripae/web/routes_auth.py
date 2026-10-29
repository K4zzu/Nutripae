"""Rutas de inicio y cierre de sesión."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from nutripae import auth

router = APIRouter()


def _formulario(request: Request, error: str | None = None):
    return request.app.state.templates.TemplateResponse(request, "entrar.html", {"error": error})


@router.get("/entrar")
def entrar_form(request: Request):
    return _formulario(request)


@router.post("/entrar")
def entrar(request: Request, usuario: str = Form(""), contrasena: str = Form("")):
    fila = auth.verificar(request.app.state.con, usuario.strip(), contrasena)
    if fila is None:
        return _formulario(request, "Usuario o contraseña incorrectos")
    request.session.clear()
    request.session["usuario_id"] = fila["id"]
    return RedirectResponse("/verificar", status_code=302)


@router.post("/salir")
def salir(request: Request):
    request.session.clear()
    return RedirectResponse("/entrar", status_code=302)


@router.get("/")
def raiz():
    return RedirectResponse("/verificar", status_code=302)

