"""Fábrica de la aplicación web."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from nutripae import db
from nutripae.config import Settings

BASE = Path(__file__).parent


def crear_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="NutriPAE")
    app.state.settings = settings
    app.state.con = db.conectar(settings.db_path)
    app.state.templates = Jinja2Templates(directory=str(BASE / "templates"))
    app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

    @app.get("/salud")
    def salud() -> dict:
        return {"ok": True}

    return app
