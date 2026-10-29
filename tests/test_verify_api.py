import io

from PIL import Image

from nutripae import db
from nutripae.analyze import Analizador
from nutripae.balance import UMBRALES_INICIALES
from nutripae.segment import SegmentadorElipses
from nutripae.vision import ResultadoVision, VisionDemo
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

def _estudiante_con_tarjeta(settings, sede="IE Santa Librada"):
    con = db.conectar(settings.db_path)
    cur = con.execute("INSERT INTO estudiantes(codigo, nombre, grado, grupo, sede, orden, consentimiento) "
                      "VALUES('E1', 'Juan Pérez', 'secundaria', '7A', ?, 1, 1)", (sede,))
    con.execute("INSERT INTO tarjetas(codigo, estudiante_id, activa) VALUES('QR1', ?, 1)", (cur.lastrowid,))
    con.commit()
    return cur.lastrowid


def _con_camara(app):
    app.state.analizador = Analizador(VisionDemo("completa", 1), SegmentadorElipses(), UMBRALES_INICIALES)


def test_tarjeta_valida_atribuye_y_guarda_foto(client, app, settings):
    eid = _estudiante_con_tarjeta(settings)
    _con_camara(app)
    login(client, settings, ["docente"])
    j = client.post("/api/verificar", files={"foto": foto()},
                    data={"modo": "camara", "tarjeta": "QR1"}).json()
    assert j["estudiante"] == {"id": eid, "nombre": "Juan Pérez", "grado": "secundaria"}
    assert j["tarjeta_invalida"] is False and j["nombre"] == "Juan" and "Juan" in j["titulo"]
    assert j["foto_url"].startswith("/fotos/")
    r = client.get(j["foto_url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    fila = db.conectar(settings.db_path).execute("SELECT sede, grado, estudiante_id FROM verificaciones").fetchone()
    assert tuple(fila) == ("IE Santa Librada", "secundaria", eid)


def test_sin_proveedor_la_camara_no_inventa(client, settings):
    login(client, settings, ["docente"])
    r = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "camara"})
    assert r.status_code == 503 and r.json()["error"] == "sin_ia"
    assert db.conectar(settings.db_path).execute("SELECT COUNT(*) FROM verificaciones").fetchone()[0] == 0


def _filas_atribuidas(settings):
    return db.conectar(settings.db_path).execute(
        "SELECT COUNT(*) FROM verificaciones WHERE estudiante_id IS NOT NULL").fetchone()[0]


def test_estudiante_de_otra_sede_por_id_da_404(client, app, settings):
    eid = _estudiante_con_tarjeta(settings, sede="IE B")
    _con_camara(app)
    login(client, settings, ["docente"], usuario="a", sedes=("IE A",))
    r = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "camara", "estudiante_id": str(eid)})
    assert r.status_code == 404 and r.json() == {"error": "estudiante", "mensaje": "Estudiante no encontrado."}
    assert _filas_atribuidas(settings) == 0


def test_tarjeta_de_otra_sede_no_atribuye(client, app, settings):
    _estudiante_con_tarjeta(settings, sede="IE B")
    _con_camara(app)
    login(client, settings, ["docente"], usuario="a", sedes=("IE A",))
    j = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "camara", "tarjeta": "QR1"}).json()
    assert j["tarjeta_invalida"] is True and j["estudiante"] is None and j["nombre"] is None
    assert _filas_atribuidas(settings) == 0


def test_admin_atribuye_en_cualquier_sede(client, app, settings):
    eid = _estudiante_con_tarjeta(settings, sede="IE B")
    _con_camara(app)
    login(client, settings, ["admin"], usuario="ad", sedes=())
    j = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "camara", "estudiante_id": str(eid)}).json()
    assert j["estudiante"]["id"] == eid and _filas_atribuidas(settings) == 1


def test_otra_sede_no_ve_foto_ni_corrige(client, app, settings):
    _estudiante_con_tarjeta(settings, sede="IE B")
    _con_camara(app)
    login(client, settings, ["docente"], usuario="b", sedes=("IE B",))
    j = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "camara", "tarjeta": "QR1"}).json()
    assert client.get(j["foto_url"]).status_code == 200
    login(client, settings, ["docente"], usuario="a", sedes=("IE A",))
    assert client.get(j["foto_url"]).status_code == 404
    r = client.post(f"/api/verificaciones/{j['id']}/corregir", json={"indice": 0, "alimento": "banano"})
    assert r.status_code == 404
    login(client, settings, ["admin"], usuario="ad", sedes=())
    assert client.get(j["foto_url"]).status_code == 200


def test_sin_foto_guardada_devuelve_imagen_en_linea(client, settings):
    login(client, settings, ["docente"])
    j = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "demo", "escenario": "no_apto"}).json()
    assert j["foto_url"].startswith("data:image/jpeg;base64,")
    p = next(p for p in j["porciones"] if p["estado"] == "no_apto")
    assert p["color"] == "#B81F3C" and p["grupo_label"]


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


# --- cuadro vacío, campo "guardado" -----------------------------------------------------------

def _contar_verificaciones(settings):
    return db.conectar(settings.db_path).execute("SELECT COUNT(*) FROM verificaciones").fetchone()[0]


def test_cuadro_vacio_da_422_y_no_guarda(client, app, settings):
    class VisionVacia:
        def analizar(self, imagen): return ResultadoVision([], persona=False)
    app.state.analizador = Analizador(VisionVacia(), SegmentadorElipses(), UMBRALES_INICIALES)
    _estudiante_con_tarjeta(settings)
    login(client, settings, ["docente"])
    r = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "camara", "tarjeta": "QR1"})
    assert r.status_code == 422
    assert r.json() == {"error": "bandeja", "mensaje": "No veo la bandeja. Acércala a la cámara."}
    assert _contar_verificaciones(settings) == 0


def test_solo_bebida_da_422(client, app, settings):
    from nutripae.vision import Deteccion

    class VisionSoloJugo:
        def analizar(self, imagen):
            return ResultadoVision([Deteccion("jugo_natural", "Jugo", 200, (0.1, 0.1, 0.4, 0.4), 0.9, True, "")])
    app.state.analizador = Analizador(VisionSoloJugo(), SegmentadorElipses(), UMBRALES_INICIALES)
    login(client, settings, ["docente"])
    r = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "camara"})
    assert r.status_code == 422 and r.json()["error"] == "bandeja"
    assert _contar_verificaciones(settings) == 0


def test_guardado_verdadero_con_consentimiento(client, app, settings):
    _estudiante_con_tarjeta(settings)
    _con_camara(app)
    login(client, settings, ["docente"])
    j = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "camara", "tarjeta": "QR1"}).json()
    assert j["guardado"] is True


def test_guardado_falso_sin_consentimiento_sin_estudiante_y_en_practica(client, app, settings):
    eid = _estudiante_con_tarjeta(settings)
    con = db.conectar(settings.db_path)
    con.execute("UPDATE estudiantes SET consentimiento=0 WHERE id=?", (eid,)); con.commit()
    _con_camara(app)
    login(client, settings, ["docente"])
    sin_consentimiento = client.post("/api/verificar", files={"foto": foto()},
                                     data={"modo": "camara", "estudiante_id": str(eid)}).json()
    assert sin_consentimiento["estudiante"]["id"] == eid and sin_consentimiento["guardado"] is False
    assert client.post("/api/verificar", files={"foto": foto()}, data={"modo": "camara"}).json()["guardado"] is False
    practica = client.post("/api/verificar", files={"foto": foto()},
                           data={"modo": "demo", "escenario": "completa", "estudiante_id": str(eid)}).json()
    assert practica["guardado"] is False
