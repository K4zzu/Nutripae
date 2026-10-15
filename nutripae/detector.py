"""Backends de visión artificial para reconocer alimentos en la bandeja.

Todos devuelven una lista de `Deteccion` (alimento, gramos estimados, caja, apto).

- DemoDetector      : sin modelo. Simula una detección coherente con la minuta y el
                      peso esperado de la minuta. Sirve para demostrar el flujo sin API ni GPU.
- VisionLLMDetector : usa un modelo multimodal (Claude, Gemini u OpenAI) con salida JSON
                      estructurada. Funciona en minutos con una API key; es el backend
                      recomendado para el piloto.
- YoloDetector      : modelo YOLO fine-tuned (ultralytics) con un dataset propio de
                      bandejas PAE. Es el objetivo para la fase de producción (edge,
                      sin internet).
"""
from __future__ import annotations

import base64
import io
import json
import os
import random
from dataclasses import dataclass, asdict

from PIL import Image, ImageDraw, ImageFont

from .menu import Minuta, meta_gramos
from .nutrition import TABLA


@dataclass
class Deteccion:
    alimento: str          # clave en nutrition.TABLA (o "desconocido")
    nombre: str            # nombre visible
    grupo: str
    gramos: float          # gramos estimados visualmente
    bbox: tuple            # (x1, y1, x2, y2) normalizado 0-1
    confianza: float = 0.9
    apto: bool = True      # False si presenta mal aspecto (quemado, descompuesto, etc.)
    observacion: str = ""

    def dict(self):
        return asdict(self)


# ---------------------------------------------------------------- base

class Detector:
    nombre = "base"

    def detectar(self, imagen: Image.Image | None, minuta: Minuta, grado: str, peso_g: float | None) -> list[Deteccion]:
        raise NotImplementedError


# ---------------------------------------------------------------- demo

# disposición típica de una bandeja de 6 compartimentos (normalizada)
_CELDAS = [
    (0.03, 0.05, 0.48, 0.48),  # proteina
    (0.52, 0.05, 0.97, 0.48),  # cereal
    (0.03, 0.52, 0.33, 0.95),  # tuberculo
    (0.36, 0.52, 0.64, 0.95),  # verdura
    (0.67, 0.52, 0.97, 0.95),  # fruta
    (0.80, 0.02, 0.98, 0.20),  # bebida
]


class DemoDetector(Detector):
    """Simulación: la porción real se desvía aleatoriamente de la meta.

    `escenario` permite forzar casos para la demo en vivo:
      - "completa"   : todo dentro de tolerancia
      - "incompleta" : falta un grupo (p. ej. verdura) y proteína baja
      - "no_apto"    : un alimento marcado con mal aspecto
      - "aleatorio"  : mezcla ponderada de los anteriores
    """
    nombre = "Demo (simulado)"

    def __init__(self, escenario: str = "aleatorio", semilla: int | None = None):
        self.escenario = escenario
        self.rng = random.Random(semilla)

    def detectar(self, imagen, minuta, grado, peso_g):
        esc = self.escenario
        if esc == "aleatorio":
            esc = self.rng.choices(["completa", "incompleta", "no_apto"], weights=[0.78, 0.17, 0.05])[0]
        metas = meta_gramos(grado, minuta)
        falta_grupo = esc == "incompleta" and self.rng.random() < 0.5
        out = []
        for i, c in enumerate(minuta.componentes):
            meta = metas[c.alimento]
            factor = self.rng.uniform(0.85, 1.15)
            apto, obs = True, ""
            if falta_grupo and c.grupo == "verdura":
                continue  # falta la verdura
            if esc == "incompleta" and c.grupo == "proteina":
                factor = self.rng.uniform(0.45, 0.7)
            if esc == "no_apto" and c.grupo == "proteina":
                apto, obs = False, "Aspecto anómalo: coloración oscura / posible descomposición"
            out.append(Deteccion(
                alimento=c.alimento, nombre=c.nombre, grupo=c.grupo,
                gramos=round(meta * factor, 1), bbox=_CELDAS[i % len(_CELDAS)],
                confianza=round(self.rng.uniform(0.82, 0.98), 2), apto=apto, observacion=obs,
            ))
        return out


# ---------------------------------------------------------------- visión LLM

_PROMPT = """Eres un sistema de verificación de raciones del Programa de Alimentación Escolar (PAE) en Colombia.
{contexto}
Hoy la minuta es "{minuta}" y debería contener: {esperados}.
El estudiante es de {grado}.

Devuelve SOLO un JSON con esta estructura (sin texto adicional):
{{
  "items": [
    {{"alimento": "<clave>", "gramos_estimados": <numero>, "bbox": [x1, y1, x2, y2], "confianza": <0-1>,
      "apto": true|false, "observacion": "<texto corto>"}}
  ]
}}
Reglas:
- "alimento" debe ser una de estas claves: {claves}. Si ves comida que no corresponde, usa "desconocido".
- bbox en coordenadas normalizadas 0-1 relativas a la imagen (x1,y1 esquina superior izquierda).
- "apto": false si el alimento tiene mal aspecto (quemado, moho, color anormal, cuerpos extraños).
- Si un alimento esperado NO está en la bandeja, simplemente no lo incluyas.

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


class VisionLLMDetector(Detector):
    """Modelo multimodal con salida JSON. Proveedores: 'anthropic', 'gemini' u 'openai'."""
    nombre = "Visión LLM"

    def __init__(self, proveedor: str = "anthropic", modelo: str | None = None, api_key: str | None = None,
                 modo: str = "entrega"):
        self.proveedor = proveedor
        self.modelo = modelo or os.getenv("NUTRIPAE_MODELO")
        self.api_key = api_key or os.getenv(ENV_KEY.get(proveedor, ""))
        self.modo = modo  # "entrega" | "devolucion"
        if not self.api_key:
            raise ValueError("Falta la API key del proveedor de visión (ANTHROPIC_API_KEY, GEMINI_API_KEY u OPENAI_API_KEY).")

    def _prompt(self, minuta, grado):
        from .menu import GRADOS
        esperados = ", ".join(f"{c.nombre} ({c.alimento})" for c in minuta.componentes)
        contexto = ("Analiza la foto de la bandeja RECIÉN SERVIDA en la estación de entrega."
                    if self.modo == "entrega" else
                    "Analiza la foto de la bandeja DEVUELTA después de comer: reporta únicamente lo que QUEDÓ en el plato "
                    "(sobrante) con sus gramos estimados; un compartimento vacío no se incluye.")
        return _PROMPT.format(contexto=contexto, minuta=minuta.nombre, esperados=esperados, grado=GRADOS[grado],
                              claves=", ".join(TABLA.keys()), bandeja_cm=BANDEJA_CM, comp_grande_cm=COMP_GRANDE_CM,
                              comp_peq_cm=COMP_PEQ_CM,
                              densidades="; ".join(f"{k} {v} g/cm³" for k, v in DENSIDAD.items()))

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

    def detectar(self, imagen, minuta, grado, peso_g):
        if imagen is None:
            raise ValueError("El backend de visión necesita una imagen.")
        texto = self._llamar(imagen, self._prompt(minuta, grado))
        texto = texto.strip().strip("`")
        if texto.startswith("json"):
            texto = texto[4:]
        data = json.loads(texto[texto.find("{"): texto.rfind("}") + 1])
        out = []
        for it in data.get("items", []):
            clave = it.get("alimento", "desconocido")
            comp = next((c for c in minuta.componentes if c.alimento == clave), None)
            info = TABLA.get(clave)
            out.append(Deteccion(
                alimento=clave,
                nombre=comp.nombre if comp else (info.nombre if info else "Alimento no esperado"),
                grupo=comp.grupo if comp else (info.grupo if info else "otro"),
                gramos=float(it.get("gramos_estimados", 0)),
                bbox=tuple(it.get("bbox", (0, 0, 1, 1))),
                confianza=float(it.get("confianza", 0.8)),
                apto=bool(it.get("apto", True)),
                observacion=it.get("observacion", ""),
            ))
        return out


# ---------------------------------------------------------------- YOLO

class YoloDetector(Detector):
    """Detector YOLO (ultralytics) entrenado con bandejas PAE.

    Requiere `pip install ultralytics` y un archivo de pesos. Los gramos se
    estiman a partir del área del cuadro (bandeja de tamaño conocido) y una
    densidad por alimento.
    """
    nombre = "YOLO (edge)"
    DENSIDAD_G_POR_AREA = 450  # g por unidad de área normalizada (calibrable por bandeja)

    def __init__(self, pesos: str = "modelos/nutripae_yolo.pt"):
        from ultralytics import YOLO  # noqa: WPS433
        self.modelo = YOLO(pesos)

    def detectar(self, imagen, minuta, grado, peso_g):
        res = self.modelo(imagen, verbose=False)[0]
        w, h = imagen.size
        out = []
        for box in res.boxes:
            clave = res.names[int(box.cls)]
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            bbox = (x1 / w, y1 / h, x2 / w, y2 / h)
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            comp = next((c for c in minuta.componentes if c.alimento == clave), None)
            info = TABLA.get(clave)
            out.append(Deteccion(
                alimento=clave, nombre=comp.nombre if comp else clave,
                grupo=comp.grupo if comp else (info.grupo if info else "otro"),
                gramos=round(area * self.DENSIDAD_G_POR_AREA, 1), bbox=bbox,
                confianza=float(box.conf),
            ))
        return out


# ---------------------------------------------------------------- utilidades

def corregir_con_bascula(detecciones: list[Deteccion], peso_g: float | None) -> list[Deteccion]:
    """Opcional (no usado en la estación): si algún día se añade una báscula, reescala las
    estimaciones visuales para que sumen el peso real. Sin peso devuelve las detecciones intactas."""
    if not peso_g or not detecciones:
        return detecciones
    total = sum(d.gramos for d in detecciones)
    if total <= 0:
        return detecciones
    f = peso_g / total
    for d in detecciones:
        d.gramos = round(d.gramos * f, 1)
    return detecciones


def _fuente(tam: int):
    for nombre in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except Exception:
            continue
    return ImageFont.load_default(tam)


# colores del sistema de diseño NutriPAE: estado -> (color de la caja, color del texto)
_COLOR_ESTADO = {
    "ok": ((31, 122, 77), (255, 255, 255)), "alto": ((31, 122, 77), (255, 255, 255)),
    "bajo": ((232, 163, 23), (43, 29, 0)), "falta": ((184, 50, 42), (255, 255, 255)),
    "no_apto": ((122, 35, 72), (255, 255, 255)), "sobrante": ((242, 181, 58), (43, 29, 0)),
}


def dibujar_overlay(imagen: Image.Image, detecciones: list[Deteccion], estados: dict[str, str] | None = None,
                    estado_fijo: str | None = None) -> Image.Image:
    """Dibuja cajas y etiquetas sobre la imagen. `estados`: alimento -> 'ok'|'bajo'|'alto'|'falta'|'no_apto'.
    `estado_fijo` pinta todas las cajas igual (p. ej. 'sobrante' en la estación de devolución)."""
    img = imagen.convert("RGB").copy()
    w, h = img.size
    draw = ImageDraw.Draw(img, "RGBA")
    font = _fuente(max(14, w // 50))
    grosor = max(3, w // 220)
    for d in detecciones:
        x1, y1, x2, y2 = d.bbox
        est = estado_fijo or (estados or {}).get(d.alimento, "ok" if d.apto else "no_apto")
        col, fg = _COLOR_ESTADO.get(est, _COLOR_ESTADO["ok"])
        box = (x1 * w, y1 * h, x2 * w, y2 * h)
        radio = max(8, w // 70)
        draw.rounded_rectangle(box, radius=radio, fill=col + (38,), outline=col + (255,), width=grosor)
        label = f"{d.nombre} · {d.gramos:.0f} g"
        tw, th = draw.textbbox((0, 0), label, font=font)[2:]
        draw.rounded_rectangle((box[0], box[1], box[0] + tw + 16, box[1] + th + 12), radius=radio, fill=col + (240,))
        draw.text((box[0] + 8, box[1] + 5), label, fill=fg, font=font)
    return img


def bandeja_sintetica(detecciones: list[Deteccion], tamano=(900, 600)) -> Image.Image:
    """Genera una imagen esquemática de bandeja para el modo demo (sin cámara), con el fondo
    oscuro de la vista cenital del sistema de diseño."""
    img = Image.new("RGB", tamano, (26, 32, 29))
    draw = ImageDraw.Draw(img)
    w, h = tamano
    draw.rounded_rectangle((int(w * .02), int(h * .03), int(w * .99), int(h * .97)), radius=36,
                           outline=(58, 69, 64), width=4, fill=(43, 52, 48))
    for d in detecciones:
        x1, y1, x2, y2 = d.bbox
        col = TABLA[d.alimento].color if d.alimento in TABLA else "#999999"
        if not d.apto:
            col = "#5a3a2a"
        cx, cy = (x1 + x2) / 2 * w, (y1 + y2) / 2 * h
        rx, ry = (x2 - x1) / 2 * w * 0.8, (y2 - y1) / 2 * h * 0.8
        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=col, outline=(37, 45, 41), width=3)
    return img
