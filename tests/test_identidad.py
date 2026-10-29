# tests/test_identidad.py
import re
from pathlib import Path
from nutripae.foods import GRUPO_COLOR

CSS = Path("nutripae/web/static/app.css").read_text(encoding="utf-8")
JS = Path("nutripae/web/static/verificar.js").read_text(encoding="utf-8")
PLANTILLAS = sorted(Path("nutripae/web/templates").glob("*.html"))

def test_tokens_nuevos_y_sin_restos_v1():
    for hexs in ["#4C17C1", "#23D098", "#FAC344", "#EE3B5A", "#1C3F9E", "#1F1A3D"]:
        assert hexs.lower() in CSS.lower()
    for viejo in ["#1F7A4D", "#145236", "#F6F2EA", "#FFFDF9", "#E3F0E7", "Atkinson"]:
        assert viejo.lower() not in CSS.lower()
    assert "Fredoka" in CSS and "Nunito" in CSS
    assert PLANTILLAS
    for plantilla in PLANTILLAS:
        assert "Atkinson" not in plantilla.read_text(encoding="utf-8"), plantilla.name


def _luminancia(hexcolor):
    h = hexcolor.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _contraste(a, b):
    la, lb = sorted([_luminancia(a), _luminancia(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _token(nombre):
    return re.search(rf"--{nombre}:\s*(#[0-9A-Fa-f]{{6}})", CSS).group(1)


def test_texto_sobre_fondos_claros_cumple_aa():
    for tono in ("verde", "amarillo", "rojo"):
        assert _contraste(_token(f"{tono}-texto"), _token(f"{tono}-claro")) >= 4.5, tono
    # ninguna regla pinta texto con el tono "oscuro" sobre el fondo claro de estado
    for regla in re.findall(r"\{[^}]*\}", CSS):
        for tono in ("verde", "amarillo"):
            if f"background: var(--{tono}-claro)" in regla:
                assert not re.search(rf"[ ;{{]color: var\(--{tono}-oscuro\)", regla), regla

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
    # oculta por defecto: solo el JS la muestra, y solo en modo estación
    etiqueta = re.search(r"<[^>]*\bid=\"inicio\"[^>]*>", html).group(0)
    assert re.search(r"\shidden(\s|>|=)", etiqueta), etiqueta
    assert re.search(r"if \(ESTACION\) mostrarInicio\(\);\s*else iniciarCamara\(\);", JS)


def test_estacion_oculta_la_barra_y_deja_salir_discreto(client, settings):
    from tests.conftest import login
    login(client, settings, ["docente"])
    html = client.get("/verificar").text
    # la barra sigue en el HTML (modo celular); en la estación el JS marca el body y el CSS la oculta
    assert 'class="np-nav"' in html
    assert re.search(r'document\.body\.classList\.toggle\("np-estacion", ESTACION\)', JS)
    assert re.search(r"\.np-estacion \.np-nav\s*\{[^}]*display:\s*none", CSS)
    # "Salir" discreto en la capa de la docente, visible solo en la estación
    assert re.search(r'<form[^>]*action="/salir"[^>]*class="np-v-salir"', html)
    assert re.search(r"\.np-estacion \.np-v-salir\s*\{[^}]*display:\s*flex", CSS)
    assert ".np-v-enlace" not in CSS

def test_entrar_usa_logo_nuevo(client):
    html = client.get("/entrar").text
    assert "/static/img/logo" in html and "#145236" not in html


def test_practica_visible_y_solo_en_la_sesion(client, settings):
    from tests.conftest import login
    login(client, settings, ["docente"])
    html = client.get("/verificar").text
    assert 'id="practica-banda"' in html and "Práctica: no se guarda nada" in html
    # la banda va en la capa de la docente, no en la del niño
    assert html.index('id="practica-banda"') > html.index('class="np-v-docente"')
    assert '.np-v-practica-banda' in CSS and "--amarillo-claro" in CSS
    assert 'sesion.get("np.practica"' in JS and 'sesion.set("np.situacion"' in JS
    assert 'local.set("np.practica"' not in JS and 'local.get("np.situacion"' not in JS
    assert "sessionStorage" in JS


def test_cuadro_vacio_y_sin_consentimiento_en_la_pantalla():
    assert 'j.error === "bandeja"' in JS and "AVISO_BANDEJA = 3000" in JS
    assert "Sin consentimiento: no se guardó" in JS and "j.guardado === false" in JS
