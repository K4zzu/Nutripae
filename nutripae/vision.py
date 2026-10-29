"""IA de visión por API: reconoce los alimentos de la bandeja y detecta personas en la foto.

- VisionAPI  : modelo multimodal (OpenAI por defecto, también Anthropic y Gemini) con salida JSON.
- VisionDemo : fabrica detecciones coherentes sin red, para demostrar el flujo.
"""
from __future__ import annotations

import base64
import io
import json
import os
import random
from dataclasses import dataclass, field
from typing import Protocol

from PIL import Image

from .foods import catalogo


@dataclass
class Deteccion:
    alimento: str          # clave del catálogo, o "otro"
    nombre: str            # nombre visible
    gramos: float          # gramos estimados visualmente
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2) normalizado 0-1
    confianza: float
    apto: bool
    observacion: str


@dataclass
class ResultadoVision:
    detecciones: list[Deteccion] = field(default_factory=list)
    persona: bool = False


class Vision(Protocol):
    def analizar(self, imagen: Image.Image) -> ResultadoVision: ...


# ---------------------------------------------------------------- prompt

_PROMPT = """Eres un sistema de verificación de raciones del Programa de Alimentación Escolar (PAE) en Colombia.
Analiza la foto de la bandeja recién servida.
La bandeja es un almuerzo escolar del PAE (Colombia).

Devuelve SOLO un JSON con esta estructura (sin texto adicional):
{{
  "persona": true|false,
  "items": [
    {{"alimento": "<clave>", "nombre": "<nombre del alimento>", "gramos_estimados": <numero>,
      "bbox": [x1, y1, x2, y2], "confianza": <0-1>, "apto": true|false, "observacion": "<texto corto>"}}
  ]
}}
Reglas:
- "alimento" debe ser una de estas claves: {claves}. Si el alimento no está en la lista, usa "otro" y pon el nombre real en "nombre".
- "persona": true si en la imagen aparece una persona, un rostro o una mano que ocupe más de un cuarto de la foto.
- bbox en coordenadas normalizadas 0-1 relativas a la imagen (x1,y1 esquina superior izquierda).
- "apto": false si el alimento tiene mal aspecto (quemado, moho, color anormal, cuerpos extraños).
- Un compartimento vacío no se incluye.

Cómo estimar los gramos (NO hay báscula; tu estimación es la única medida):
1. Usa la bandeja como regla: una bandeja escolar estándar mide aprox. {bandeja_cm} y sus compartimentos
   grandes ~{comp_grande_cm}, los pequeños ~{comp_peq_cm}. Calcula el área real (cm²) que ocupa cada porción
   a partir de la fracción del compartimento que cubre.
2. Estima la altura/espesor de la porción por las sombras y el borde del compartimento (1–4 cm es lo habitual).
3. Volumen ≈ área × altura × factor de forma (0.6–0.8 para montículos). Gramos = volumen × densidad típica:
   {densidades}.
4. Contrasta con porciones de referencia: una cucharada sopera de arroz cocido ≈ 25 g; una presa de pollo pequeña ≈ 60–80 g;
   una papa mediana ≈ 90 g; un vaso de 7 oz de jugo ≈ 200 g; un banano mediano ≈ 100 g. Ajusta si tu cálculo se aleja mucho.
5. Para piezas enteras (huevo, banano, naranja, vaso) usa el peso típico de la pieza por el número de piezas.
Sé consistente: si dudas entre dos valores, elige el intermedio. Informa en "observacion" la base de la estimación (p. ej. "cubre 2/3 del compartimento, 2 cm de alto").
"""

# dimensiones de referencia de la bandeja (parametrizables según la bandeja real del comedor)
BANDEJA_CM = "32 × 25 cm"
COMP_GRANDE_CM = "14 × 10 cm"
COMP_PEQ_CM = "9 × 9 cm"
# densidad aproximada en g/cm³ de alimentos servidos (porción cocida, con aire)
DENSIDAD = {
    "arroz cocido": 0.75, "carnes guisadas / pollo": 0.95, "huevo revuelto": 0.85, "pescado": 0.9,
    "papa / yuca / plátano cocidos": 0.9, "lentejas / fríjol en caldo": 0.95, "ensalada fresca": 0.35,
    "fruta en trozos": 0.8, "jugo / leche": 1.0,
}

# variable de entorno con la API key de cada proveedor
ENV_KEY = {"anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}


def _prompt(cat: dict | None = None) -> str:
    return _PROMPT.format(
        claves=", ".join((cat or catalogo()).keys()), bandeja_cm=BANDEJA_CM, comp_grande_cm=COMP_GRANDE_CM,
        comp_peq_cm=COMP_PEQ_CM, densidades="; ".join(f"{k} {v} g/cm³" for k, v in DENSIDAD.items()))


# ---------------------------------------------------------------- API

class VisionAPI:
    """Modelo multimodal con salida JSON. Proveedores: 'openai', 'anthropic' o 'gemini'."""

    def __init__(self, proveedor: str, modelo: str | None = None, api_key: str | None = None,
                 catalogo_fn=None):
        self._catalogo_fn = catalogo_fn  # catálogo vigente (con alimentos extra); None = el propio
        self.proveedor = proveedor
        self.modelo = modelo or os.getenv("NUTRIPAE_MODELO")
        self.api_key = api_key or os.getenv(ENV_KEY.get(proveedor, ""))
        if not self.api_key:
            raise ValueError("Falta la clave del servicio de visión (OPENAI_API_KEY, ANTHROPIC_API_KEY o GEMINI_API_KEY).")

    def _llamar(self, imagen: Image.Image, prompt: str) -> str:
        buf = io.BytesIO()
        imagen.convert("RGB").save(buf, format="JPEG", quality=85)
        datos = buf.getvalue()
        if self.proveedor == "anthropic":
            import anthropic
            cliente = anthropic.Anthropic(api_key=self.api_key)
            r = cliente.messages.create(
                model=self.modelo or "claude-sonnet-5-5", max_tokens=1500,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                 "data": base64.b64encode(datos).decode()}},
                    {"type": "text", "text": prompt},
                ]}],
            )
            return r.content[0].text
        if self.proveedor == "gemini":
            from google import genai
            from google.genai import types
            cliente = genai.Client(api_key=self.api_key)
            r = cliente.models.generate_content(
                model=self.modelo or "gemini-2.5-flash",
                contents=[types.Part.from_bytes(data=datos, mime_type="image/jpeg"), prompt],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return r.text
        if self.proveedor == "openai":
            from openai import OpenAI
            cliente = OpenAI(api_key=self.api_key)
            r = cliente.chat.completions.create(
                model=self.modelo or "gpt-4.1-mini",
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {
                        "url": "data:image/jpeg;base64," + base64.b64encode(datos).decode()}},
                    {"type": "text", "text": prompt},
                ]}],
            )
            return r.choices[0].message.content
        raise ValueError(f"Proveedor no soportado: {self.proveedor}")

    def analizar(self, imagen: Image.Image) -> ResultadoVision:
        return self.parsear(self._llamar(imagen, _prompt(self._catalogo_fn() if self._catalogo_fn else None)))

    def parsear(self, texto: str) -> ResultadoVision:
        """Convierte la respuesta de la IA en un ResultadoVision (sin red)."""
        texto = (texto or "").strip().strip("`")
        if texto.startswith("json"):
            texto = texto[4:]
        try:
            cuerpo = texto[texto.find("{"): texto.rfind("}") + 1]
            data = json.loads(cuerpo)
            if not isinstance(data, dict):
                raise ValueError
            cat = self._catalogo_fn() if self._catalogo_fn else catalogo()
            out = []
            for it in data.get("items") or []:
                clave = it.get("alimento", "otro")
                nombre = it.get("nombre") or (cat[clave][0] if clave in cat else clave)
                bbox = tuple(float(v) for v in it.get("bbox", (0, 0, 1, 1)))
                if len(bbox) != 4:
                    raise ValueError
                out.append(Deteccion(
                    alimento=clave, nombre=nombre, gramos=float(it.get("gramos_estimados", 0)),
                    bbox=bbox, confianza=float(it.get("confianza", 0.8)),
                    apto=bool(it.get("apto", True)), observacion=it.get("observacion", "")))
            return ResultadoVision(out, bool(data.get("persona", False)))
        except (ValueError, TypeError, AttributeError, KeyError):
            raise ValueError("La respuesta de la IA no se pudo leer") from None


# ---------------------------------------------------------------- demostración

# disposición típica de una bandeja de 6 compartimentos (normalizada)
_CELDAS = [
    (0.03, 0.05, 0.48, 0.48),  # proteína
    (0.52, 0.05, 0.97, 0.48),  # cereal
    (0.03, 0.52, 0.33, 0.95),  # tubérculo
    (0.36, 0.52, 0.64, 0.95),  # verdura
    (0.67, 0.52, 0.97, 0.95),  # fruta
    (0.80, 0.02, 0.98, 0.20),  # bebida
]
_PLATO = [("pollo_guisado", 90), ("arroz_blanco", 90), ("papa_cocida", 60),
          ("ensalada_fresca", 100), ("banano", 80), ("jugo_natural", 200)]
_ESCENARIOS = ("completa", "incompleta", "no_apto", "falta_grupo")


class VisionDemo:
    """Fabrica detecciones sin red. Escenarios: completa, incompleta, no_apto, falta_grupo, aleatorio."""

    def __init__(self, escenario: str = "aleatorio", semilla: int | None = None):
        if escenario != "aleatorio" and escenario not in _ESCENARIOS:
            raise ValueError(f"Escenario no soportado: {escenario}")
        self.escenario = escenario
        self.rng = random.Random(semilla)

    def analizar(self, imagen: Image.Image) -> ResultadoVision:
        esc = self.escenario
        if esc == "aleatorio":
            esc = self.rng.choices(_ESCENARIOS, weights=[0.6, 0.2, 0.1, 0.1])[0]
        cat = catalogo()
        out = []
        for celda, (clave, meta) in zip(_CELDAS, _PLATO):
            gramos, apto, obs = meta * self.rng.uniform(0.9, 1.1), True, ""
            if esc == "falta_grupo" and clave == "ensalada_fresca":
                continue
            if clave == "pollo_guisado":
                if esc == "incompleta":
                    gramos = self.rng.uniform(20, 40)
                elif esc == "no_apto":
                    apto, obs = False, "Aspecto anómalo: coloración oscura"
            out.append(Deteccion(
                alimento=clave, nombre=cat[clave][0] if clave in cat else clave, gramos=round(gramos, 1),
                bbox=celda, confianza=round(self.rng.uniform(0.82, 0.98), 2), apto=apto, observacion=obs))
        return ResultadoVision(out, False)


def crear_vision(settings, catalogo_fn=None) -> Vision:
    """Demostración si no hay proveedor configurado; si no, la IA por API."""
    if settings.proveedor is None:
        return VisionDemo()
    return VisionAPI(settings.proveedor, settings.modelo, catalogo_fn=catalogo_fn)
