"""Configuración de NutriPAE desde variables de entorno (y .env)."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

log = logging.getLogger("nutripae")

SECRETO_POR_DEFECTO = "cambia-esta-clave"


@dataclass
class Settings:
    secret: str
    db_path: Path
    fotos_dir: Path
    proveedor: str | None = None
    modelo: str | None = None
    muestra_entrenamiento_dia: int = 50
    segmentador: str = "fastsam"
    https: bool = False


def cargar() -> Settings:
    load_dotenv()
    secret = os.getenv("NUTRIPAE_SECRET")
    if not secret:
        log.warning("NUTRIPAE_SECRET no está definida; se usa una clave de desarrollo. "
                    "Defínela en producción.")
        secret = SECRETO_POR_DEFECTO
    return Settings(
        secret=secret,
        db_path=Path(os.getenv("NUTRIPAE_DB", "data/nutripae.db")),
        fotos_dir=Path(os.getenv("NUTRIPAE_FOTOS", "data/fotos")),
        proveedor=os.getenv("NUTRIPAE_PROVEEDOR") or None,
        modelo=os.getenv("NUTRIPAE_MODELO") or None,
        muestra_entrenamiento_dia=int(os.getenv("NUTRIPAE_MUESTRA_DIA", "50")),
        segmentador=os.getenv("NUTRIPAE_SEGMENTADOR", "fastsam"),
        https=os.getenv("NUTRIPAE_HTTPS", "").strip().lower() in ("1", "true", "si", "sí", "yes"),
    )
