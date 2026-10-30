"""Enlace «Informes» para admin y nutricionista, nombre al leer la tarjeta y aviso sin lista de estudiantes."""
from nutripae import db, students
from tests.conftest import login
from tests.test_students import xlsx


def _sembrar(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "1°", "1A", "IE Santa Librada", "sí"),
                                       ("B1", "Ana Ruiz", "1°", "1A", "Otra Sede", "sí")]))
    for codigo, cod_est in (("QR1", "A1"), ("QR2", "B1")):
        eid = con.execute("select id from estudiantes where codigo=?", (cod_est,)).fetchone()[0]
        con.execute("INSERT INTO tarjetas(codigo, estudiante_id, activa) VALUES(?, ?, 1)", (codigo, eid))
    con.commit()
    return con


# --- Informes -----------------------------------------------------------------------------------

def test_admin_ve_informes_aunque_no_haya_estudiantes(client, settings):
    login(client, settings, ["admin"], sedes=())
    html = client.get("/verificar").text
    assert 'href="/informes"' in html and "Informes" in html


def test_docente_no_ve_informes(client, settings):
    login(client, settings, ["docente"])
    assert 'href="/informes"' not in client.get("/verificar").text
    assert client.get("/informes").status_code == 403


def test_informes_lleva_al_resumen_de_la_primera_sede(client, settings):
    _sembrar(settings)
    login(client, settings, ["nutricionista"])
    r = client.get("/informes", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/sedes/IE%20Santa%20Librada/resumen"


def test_informes_sin_estudiantes_explica_y_ofrece_cargar(client, settings):
    login(client, settings, ["admin"], sedes=())
    r = client.get("/informes")
    assert r.status_code == 200 and "No hay estudiantes" in r.text and 'href="/admin/estudiantes"' in r.text


def test_informes_sin_estudiantes_nutricionista_no_ve_enlace_de_carga(client, settings):
    login(client, settings, ["nutricionista"], sedes=())
    r = client.get("/informes")
    assert r.status_code == 200 and "No hay estudiantes" in r.text and 'href="/admin/estudiantes"' not in r.text


# --- Nombre al leer la tarjeta ------------------------------------------------------------------

def test_api_tarjeta_devuelve_el_estudiante(client, settings):
    _sembrar(settings)
    login(client, settings, ["docente"])
    r = client.get("/api/tarjetas/QR1")
    assert r.status_code == 200
    assert r.json() == {"id": r.json()["id"], "nombre": "Ana Pérez", "grado": "primaria", "grupo": "1A",
                        "sede": "IE Santa Librada"}


def test_api_tarjeta_desconocida_o_de_otra_sede_da_404(client, settings):
    _sembrar(settings)
    login(client, settings, ["docente"])
    assert client.get("/api/tarjetas/NOEXISTE").status_code == 404
    assert client.get("/api/tarjetas/QR2").status_code == 404
    login(client, settings, ["admin"], usuario="a")
    assert client.get("/api/tarjetas/QR2").json()["nombre"] == "Ana Ruiz"


def test_api_tarjeta_requiere_sesion(client):
    r = client.get("/api/tarjetas/QR1", follow_redirects=False)
    assert r.status_code == 302


# --- Aviso sin lista cargada ---------------------------------------------------------------------

def test_verificar_avisa_al_admin_que_no_hay_lista(client, settings):
    login(client, settings, ["admin"], sedes=())
    html = client.get("/verificar").text
    assert "No hay lista de estudiantes" in html and 'href="/admin/estudiantes"' in html


def test_verificar_avisa_a_la_docente_sin_enlace(client, settings):
    login(client, settings, ["docente"])
    html = client.get("/verificar").text
    assert "No hay lista de estudiantes" in html and "administrador" in html and 'href="/admin/estudiantes"' not in html


def test_verificar_no_avisa_cuando_hay_lista(client, settings):
    _sembrar(settings)
    login(client, settings, ["docente"])
    assert "No hay lista de estudiantes" not in client.get("/verificar").text
