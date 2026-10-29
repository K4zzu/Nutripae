from PIL import Image

from nutripae.vision import VisionAPI, VisionDemo, crear_vision


def test_parsear_json_con_persona_y_otro():
    v = VisionAPI("openai", api_key="x")
    r = v.parsear('```json\n{"persona": false, "items": [{"alimento": "otro", "nombre": "Sancocho", "gramos_estimados": 180, "bbox": [0,0,.5,.5], "confianza": .8, "apto": true, "observacion": ""}]}\n```')
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
