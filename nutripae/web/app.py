"""Fábrica de la aplicación web."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from starlette.middleware.sessions import SessionMiddleware

from nutripae import db
from nutripae.config import Settings
from nutripae.web import routes_auth

BASE = Path(__file__).parent


def crear_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="NutriPAE")
    app.state.settings = settings
    app.state.con = db.conectar(settings.db_path)
    app.state.templates = Jinja2Templates(directory=str(BASE / "templates"))
    app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

    app.add_middleware(SessionMiddleware, secret_key=settings.secret,
                       same_site="lax", https_only=False)
    app.include_router(routes_auth.router)

    @app.get("/salud")
    def salud() -> dict:
        return {"ok": True}

    return app
