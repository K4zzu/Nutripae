"""Fábrica de la aplicación web."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from starlette.middleware.sessions import SessionMiddleware

from nutripae import db, segment, vision
from nutripae.analyze import Analizador
from nutripae.balance import UMBRALES_INICIALES
from nutripae.config import Settings, log
from nutripae.web import routes_auth, routes_students, routes_verify

BASE = Path(__file__).parent


def _analizador(settings: Settings, con) -> Analizador | None:
    """Analizador compartido por todas las estaciones; None si este equipo no puede analizar fotos.

    Sin proveedor no se usa la visión de práctica: un veredicto inventado nunca se guarda como real.
    """
    if settings.proveedor is None:
        log.warning("Análisis con cámara no disponible: no hay servicio de visión configurado.")
        return None
    try:
        return Analizador(vision.crear_vision(settings), segment.crear_segmentador(settings),
                          lambda: db.param(con, "umbrales", UMBRALES_INICIALES))
    except Exception as e:
        log.warning("Análisis con cámara no disponible: %s", e)
        return None


def crear_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="NutriPAE")
    app.state.settings = settings
    app.state.con = db.conectar(settings.db_path)
    app.state.templates = Jinja2Templates(directory=str(BASE / "templates"))
    app.state.analizador = _analizador(settings, app.state.con)
    app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

    app.add_middleware(SessionMiddleware, secret_key=settings.secret,
                       same_site="lax", https_only=False)
    app.include_router(routes_auth.router)
    app.include_router(routes_verify.router)
    app.include_router(routes_students.router)

    @app.get("/salud")
    def salud() -> dict:
        return {"ok": True}

    return app
