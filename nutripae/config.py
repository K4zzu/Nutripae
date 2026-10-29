"""Configuración de NutriPAE desde variables de entorno (y .env)."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

log = logging.getLogger("nutripae")

SECRETO_POR_DEFECTO = "cambia-esta-clave"

# Orden de detección del proveedor de la IA de visión y la variable de su clave.
CLAVE_PROVEEDOR = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}


def _proveedor() -> str | None:
    """El de NUTRIPAE_PROVEEDOR si tiene clave; si no, el primero con clave; None = solo práctica."""
    pedido = (os.getenv("NUTRIPAE_PROVEEDOR") or "").strip().lower() or None
    if pedido is not None:
        variable = CLAVE_PROVEEDOR.get(pedido)
        if variable and os.getenv(variable):
            return pedido
        log.warning("NUTRIPAE_PROVEEDOR=%s no tiene clave (%s); se detecta el proveedor por las claves presentes.",
                    pedido, variable or "proveedor desconocido")
    for nombre, variable in CLAVE_PROVEEDOR.items():
        if os.getenv(variable):
            return nombre
    return None


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
        proveedor=_proveedor(),
        modelo=os.getenv("NUTRIPAE_MODELO") or None,
        muestra_entrenamiento_dia=int(os.getenv("NUTRIPAE_MUESTRA_DIA", "50")),
        segmentador=os.getenv("NUTRIPAE_SEGMENTADOR", "fastsam"),
        https=os.getenv("NUTRIPAE_HTTPS", "").strip().lower() in ("1", "true", "si", "sí", "yes"),
    )
