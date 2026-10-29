# tests/test_identidad.py
import re
from pathlib import Path
from nutripae.foods import GRUPO_COLOR

CSS = Path("nutripae/web/static/app.css").read_text(encoding="utf-8")

def test_tokens_nuevos_y_sin_restos_v1():
    for hexs in ["#4C17C1", "#23D098", "#FAC344", "#EE3B5A", "#1C3F9E", "#1F1A3D"]:
        assert hexs.lower() in CSS.lower()
    for viejo in ["#1F7A4D", "#145236", "#F6F2EA", "#FFFDF9", "#E3F0E7", "Atkinson"]:
        assert viejo.lower() not in CSS.lower()
    assert "Fredoka" in CSS and "Nunito" in CSS

def test_grupo_color_nuevo():
    assert GRUPO_COLOR == {"proteina": "#EE3B5A", "energetico": "#FAC344", "verdura": "#23D098",
                           "fruta": "#4C17C1", "bebida": "#1C3F9E", "otro": "#9A96B3"}

def test_base_carga_fuentes_logo_y_favicon(client, settings):
    from tests.conftest import login
    login(client, settings, ["docente"])
    html = client.get("/verificar").text
    assert "fonts.googleapis.com" in html and "Fredoka" in html and "Nunito" in html
    assert "/static/img/favicon.png" in html and "/static/img/logo" in html
    assert "Atkinson" not in html

def test_estacion_tiene_pantalla_de_inicio(client, settings):
    from tests.conftest import login
    login(client, settings, ["docente"])
    html = client.get("/verificar?estacion=1").text
    assert "Toca para comenzar" in html

def test_entrar_usa_logo_nuevo(client):
    html = client.get("/entrar").text
    assert "/static/img/logo" in html and "#145236" not in html
