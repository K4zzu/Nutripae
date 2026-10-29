import io

from PIL import Image

from nutripae import db
from nutripae.analyze import Analizador
from nutripae.balance import UMBRALES_INICIALES
from nutripae.segment import SegmentadorElipses
from nutripae.vision import ResultadoVision
from tests.conftest import login


def foto():
    b = io.BytesIO(); Image.new("RGB", (640, 480), "gray").save(b, "JPEG"); return ("foto.jpg", b.getvalue(), "image/jpeg")


def test_verificar_demo_devuelve_veredicto(client, settings):
    login(client, settings, ["docente"])
    r = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "demo", "escenario": "completa", "grado": "primaria"})
    j = r.json()
    assert r.status_code == 200 and j["semaforo"] == "verde" and j["porciones"][0]["poligono"] and j["estudiante"] is None


def test_tarjeta_invalida_no_atribuye(client, settings):
    login(client, settings, ["docente"])
    j = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "demo", "escenario": "completa", "grado": "primaria", "tarjeta": "NOEXISTE"}).json()
    assert j["tarjeta_invalida"] is True and j["estudiante"] is None


def test_corregir_cambia_alimento(client, settings):
    login(client, settings, ["docente"])
    j = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "demo", "escenario": "falta_grupo", "grado": "primaria"}).json()
    idx = next(p["indice"] for p in j["porciones"] if p["estado"] != "falta")
    j2 = client.post(f"/api/verificaciones/{j['id']}/corregir", json={"indice": idx, "alimento": "ensalada_fresca"}).json()
    assert any(p["nombre"] == "Ensalada fresca" for p in j2["porciones"])


def test_pagina_sin_palabras_prohibidas(client, settings):
    login(client, settings, ["docente"])
    html = client.get("/verificar").text.lower()
    assert all(w not in html for w in ["modelo", "api key", "proveedor", "segmentaci", "demo"])


# --- reglas adicionales ---------------------------------------------------------------------

def _estudiante_con_tarjeta(settings, consentimiento=1):
    con = db.conectar(settings.db_path)
    cur = con.execute("INSERT INTO estudiantes(codigo, nombre, grado, grupo, sede, orden, consentimiento) "
                      "VALUES('E1', 'Juan Pérez', 'secundaria', '7A', 'Sede Norte', 1, ?)", (consentimiento,))
    con.execute("INSERT INTO tarjetas(codigo, estudiante_id, activa) VALUES('QR1', ?, 1)", (cur.lastrowid,))
    con.commit()
    return cur.lastrowid


def test_tarjeta_valida_atribuye_y_guarda_foto(client, settings):
    eid = _estudiante_con_tarjeta(settings)
    login(client, settings, ["docente"])
    j = client.post("/api/verificar", files={"foto": foto()},
                    data={"modo": "camara", "tarjeta": "QR1"}).json()
    assert j["estudiante"] == {"id": eid, "nombre": "Juan Pérez", "grado": "secundaria"}
    assert j["tarjeta_invalida"] is False and j["nombre"] == "Juan" and "Juan" in j["titulo"]
    assert j["foto_url"].startswith("/fotos/")
    r = client.get(j["foto_url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    fila = db.conectar(settings.db_path).execute("SELECT sede, grado, estudiante_id FROM verificaciones").fetchone()
    assert tuple(fila) == ("Sede Norte", "secundaria", eid)


def test_sin_foto_guardada_devuelve_imagen_en_linea(client, settings):
    login(client, settings, ["docente"])
    j = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "demo", "escenario": "no_apto"}).json()
    assert j["foto_url"].startswith("data:image/jpeg;base64,")
    p = next(p for p in j["porciones"] if p["estado"] == "no_apto")
    assert p["color"] == "#7A2348" and p["grupo_label"]


def test_corregir_invalido_da_400(client, settings):
    login(client, settings, ["docente"])
    j = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "demo", "escenario": "completa"}).json()
    r = client.post(f"/api/verificaciones/{j['id']}/corregir", json={"indice": 0, "alimento": "no_existe"})
    assert r.status_code == 400 and r.json()["error"] == "correccion"


def test_persona_da_422(client, app, settings):
    class VisionPersona:
        def analizar(self, imagen): return ResultadoVision([], persona=True)
    app.state.analizador = Analizador(VisionPersona(), SegmentadorElipses(), UMBRALES_INICIALES)
    login(client, settings, ["docente"])
    r = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "camara"})
    assert r.status_code == 422 and r.json() == {"error": "persona", "mensaje": "Repite la foto: solo la bandeja."}


def test_sin_ia_da_503_y_la_practica_sigue(client, app, settings):
    app.state.analizador = None
    login(client, settings, ["docente"])
    r = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "camara"})
    assert r.status_code == 503 and r.json()["error"] == "sin_ia"
    r = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "demo", "escenario": "completa"})
    assert r.status_code == 200


def test_falla_del_analisis_da_502(client, app, settings):
    class VisionRota:
        def analizar(self, imagen): raise RuntimeError("se cayó")
    app.state.analizador = Analizador(VisionRota(), SegmentadorElipses(), UMBRALES_INICIALES)
    login(client, settings, ["docente"])
    r = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "camara"})
    assert r.status_code == 502 and r.json()["error"] == "analisis"


def test_api_requiere_sesion(client):
    r = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "demo"}, follow_redirects=False)
    assert r.status_code in (302, 401, 403)


def test_alimentos_ordenados(client, settings):
    login(client, settings, ["docente"])
    lista = client.get("/api/alimentos").json()
    nombres = [a["nombre"] for a in lista]
    assert nombres == sorted(nombres) and {"clave", "nombre", "grupo"} <= set(lista[0])


def test_fotos_impide_salir_de_la_carpeta(client, settings):
    (settings.db_path.parent / "secreto.txt").write_text("x")
    login(client, settings, ["docente"])
    assert client.get("/fotos/../secreto.txt").status_code == 404
    assert client.get("/fotos/..%2Fsecreto.txt").status_code == 404
