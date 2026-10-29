from PIL import Image

from nutripae.vision import VisionAPI, VisionDemo, crear_vision


def test_parsear_json_con_persona_y_otro():
    v = VisionAPI("openai", api_key="x")
    r = v.parsear('```json\n{"persona": false, "items": [{"alimento": "otro", "nombre": "Sancocho", "gramos_estimados": 180, "bbox": [0,0,0.5,0.5], "confianza": 0.8, "apto": true, "observacion": ""}]}\n```')
    assert r.persona is False and r.detecciones[0].alimento == "otro" and r.detecciones[0].nombre == "Sancocho"


def test_parsear_persona_true():
    assert VisionAPI("openai", api_key="x").parsear('{"persona": true, "items": []}').persona is True


def test_parsear_json_invalido():
    import pytest
    with pytest.raises(ValueError):
        VisionAPI("openai", api_key="x").parsear("no es json")


def test_demo_incompleta_tiene_proteina_corta():
    r = VisionDemo("incompleta", semilla=1).analizar(Image.new("RGB", (640, 480)))
    prot = [d for d in r.detecciones if d.alimento == "pollo_guisado"]
    assert prot and prot[0].gramos < 50 and r.persona is False


def test_demo_escenarios():
    img = Image.new("RGB", (64, 48))
    assert len(VisionDemo("completa", 1).analizar(img).detecciones) == 6
    nf = VisionDemo("falta_grupo", 1).analizar(img).detecciones
    assert "ensalada_fresca" not in [d.alimento for d in nf]
    na = VisionDemo("no_apto", 1).analizar(img).detecciones
    assert [d.apto for d in na if d.alimento == "pollo_guisado"] == [False]
    assert VisionDemo("aleatorio", 3).analizar(img).persona is False


def test_crear_vision(monkeypatch):
    class S:
        proveedor = None
        modelo = None
    assert isinstance(crear_vision(S()), VisionDemo)
    S.proveedor = "openai"

    monkeypatch.setenv("OPENAI_API_KEY", "x")
    assert isinstance(crear_vision(S()), VisionAPI)


# --- tiempos de espera y apto estricto ------------------------------------------------------

import json
import sys
import types as _types

import pytest


def _item(apto):
    return json.dumps({"items": [{"alimento": "arroz_blanco", "gramos_estimados": 90, "bbox": [0, 0, 1, 1], "apto": apto}]})


@pytest.mark.parametrize("valor, esperado", [
    (True, True), (False, False), ("false", False), ("FALSE", False), ("true", True), ("True", True),
    (None, True), ("no", False), (0, False), (1, False),
])
def test_apto_estricto(valor, esperado):
    assert VisionAPI("openai", api_key="x").parsear(_item(valor)).detecciones[0].apto is esperado


def test_apto_ausente_es_apto():
    r = VisionAPI("openai", api_key="x").parsear('{"items": [{"alimento": "arroz_blanco", "bbox": [0,0,1,1]}]}')
    assert r.detecciones[0].apto is True


class _Registro:
    """Cliente falso que guarda los argumentos con que se construyó."""

    def __init__(self):
        self.kwargs = None

    def cliente(self, respuesta):
        reg = self

        class Cliente:
            def __init__(self, **kwargs):
                reg.kwargs = kwargs
                self.chat = self.messages = self.models = self

            @property
            def completions(self):
                return self

            def create(self, **kw):
                if "max_tokens" in kw:  # anthropic
                    return _types.SimpleNamespace(content=[_types.SimpleNamespace(text=respuesta)])
                return _types.SimpleNamespace(choices=[_types.SimpleNamespace(
                    message=_types.SimpleNamespace(content=respuesta))])

            def generate_content(self, **kw):
                return _types.SimpleNamespace(text=respuesta)
        return Cliente


def test_openai_con_tiempo_de_espera(monkeypatch):
    reg = _Registro()
    monkeypatch.setitem(sys.modules, "openai", _types.SimpleNamespace(OpenAI=reg.cliente('{"items": []}')))
    VisionAPI("openai", api_key="k").analizar(Image.new("RGB", (8, 8)))
    assert reg.kwargs == {"api_key": "k", "timeout": 20, "max_retries": 1}


def test_anthropic_con_tiempo_de_espera(monkeypatch):
    reg = _Registro()
    monkeypatch.setitem(sys.modules, "anthropic", _types.SimpleNamespace(Anthropic=reg.cliente('{"items": []}')))
    VisionAPI("anthropic", api_key="k").analizar(Image.new("RGB", (8, 8)))
    assert reg.kwargs == {"api_key": "k", "timeout": 20, "max_retries": 1}


def test_gemini_con_tiempo_de_espera(monkeypatch):
    reg = _Registro()
    genai = _types.ModuleType("google.genai")
    genai.Client = reg.cliente('{"items": []}')
    tipos = _types.ModuleType("google.genai.types")
    tipos.Part = _types.SimpleNamespace(from_bytes=lambda **kw: kw)
    tipos.GenerateContentConfig = lambda **kw: kw
    genai.types = tipos
    google = _types.ModuleType("google")
    google.genai = genai
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", tipos)
    VisionAPI("gemini", api_key="k").analizar(Image.new("RGB", (8, 8)))
    assert reg.kwargs == {"api_key": "k", "http_options": {"timeout": 20000}}
