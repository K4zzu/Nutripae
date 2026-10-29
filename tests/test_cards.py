import pytest

from nutripae import cards, db, students
from tests.conftest import login
from tests.test_students import xlsx


def test_tarjeta_solo_con_consentimiento_y_qr_sin_nombre(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", "sí"),
                                       ("A2", "Luis", "3°", "3-A", "IE", "no")]))
    cod = cards.asignar_tarjeta(con, 1)
    assert len(cod) >= 8 and not any(c in cod for c in "0O1I")
    with pytest.raises(ValueError):
        cards.asignar_tarjeta(con, 2)
    pdf = cards.pdf_curso(con, "IE", "primaria", "3-A")
    assert pdf[:4] == b"%PDF" and b"Luis" not in pdf


def test_anular_invalida_la_tarjeta(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana", "3°", "3-A", "IE", "sí")]))
    cod = cards.asignar_tarjeta(con, 1)
    cards.anular_tarjeta(con, cod)
    assert db.estudiante_por_tarjeta(con, cod) is None and cards.tarjeta_activa(con, 1) is None


def test_una_sola_tarjeta_activa_por_estudiante(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana", "3°", "3-A", "IE", "sí")]))
    a = cards.asignar_tarjeta(con, 1)
    b = cards.asignar_tarjeta(con, 1)
    assert a != b and cards.tarjeta_activa(con, 1) == b
    assert db.estudiante_por_tarjeta(con, a) is None
    cards.anular_tarjeta(con, "NOEXISTE")


def test_pdf_asigna_tarjeta_sin_reasignar_y_omite_sin_consentimiento(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana", "3°", "3-A", "IE", "sí"),
                                       ("A2", "Luis", "3°", "3-A", "IE", "no")]))
    cards.pdf_curso(con, "IE", "primaria", "3-A")
    cod = cards.tarjeta_activa(con, 1)
    assert cod and cards.tarjeta_activa(con, 2) is None
    cards.pdf_curso(con, "IE", "primaria", "3-A")
    assert cards.tarjeta_activa(con, 1) == cod


def test_pdf_curso_vacio_y_varias_hojas(settings):
    con = db.conectar(settings.db_path)
    assert cards.pdf_curso(con, "IE", "primaria", "9-Z")[:4] == b"%PDF"
    students.importar_excel(con, xlsx([(f"A{i}", f"Est {i}", "3°", "3-A", "IE", "sí") for i in range(9)]))
    pdf = cards.pdf_curso(con, "IE", "primaria", "3-A")
    assert b"/Count 2" in pdf


def test_rutas_pdf_y_anular(client, settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana", "3°", "3-A", "IE Santa Librada", "sí")]))
    login(client, settings, ["admin"])
    r = client.get("/admin/tarjetas.pdf", params={"sede": "IE Santa Librada", "grado": "primaria", "grupo": "3-A"})
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == 'attachment; filename="tarjetas_IE_Santa_Librada_primaria_3-A.pdf"'
    cod = cards.tarjeta_activa(con, 1)
    assert cod in client.get("/admin/estudiantes").text
    r = client.post(f"/admin/tarjetas/{cod}/anular", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/admin/estudiantes"
    assert cards.tarjeta_activa(con, 1) is None


def test_rutas_tarjetas_exigen_admin(client, settings):
    login(client, settings, ["docente"])
    assert client.get("/admin/tarjetas.pdf?sede=a&grado=b&grupo=c").status_code in (302, 303, 401, 403)
    assert client.post("/admin/tarjetas/X/anular", follow_redirects=False).status_code in (302, 303, 401, 403)


def test_quitar_consentimiento_o_dar_de_baja_anula_la_tarjeta(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana", "3°", "3-A", "IE", "sí"),
                                       ("A2", "Luis", "3°", "3-A", "IE", "sí")]))
    a, b = cards.asignar_tarjeta(con, 1), cards.asignar_tarjeta(con, 2)
    students.set_consentimiento(con, 1, False)
    assert cards.tarjeta_activa(con, 1) is None and db.estudiante_por_tarjeta(con, a) is None
    students.dar_de_baja(con, 2)
    assert cards.tarjeta_activa(con, 2) is None and db.estudiante_por_tarjeta(con, b) is None


def test_reimportar_sin_consentimiento_anula_la_tarjeta(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana", "3°", "3-A", "IE", "sí")]))
    cards.asignar_tarjeta(con, 1)
    students.importar_excel(con, xlsx([("A1", "Ana", "3°", "3-A", "IE", "no")]))
    assert cards.tarjeta_activa(con, 1) is None
