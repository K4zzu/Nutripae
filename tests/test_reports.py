import re
from datetime import date, datetime

from nutripae import db, history, reports
from tests.conftest import login
from tests.test_history import insertar


def _ana(con, sede="IE"):
    con.execute("insert into estudiantes(codigo,nombre,grado,grupo,sede,orden,consentimiento) "
                "values('A','Ana Pérez','primaria','3-A',?,1,1)", (sede,))
    con.commit()


def test_pdf_historial_contiene_nombre_y_frase(settings):
    con = db.conectar(settings.db_path)
    _ana(con)
    insertar(con, 1, datetime(2026, 10, 29, 12), "verde")
    pdf = reports.pdf_historial(con, settings, 1, date(2026, 10, 1), date(2026, 10, 31))
    assert pdf[:4] == b"%PDF" and len(pdf) > 1500


def test_parrafo_para_padres(settings):
    con = db.conectar(settings.db_path)
    _ana(con)
    falta = '[{"grupo":"verdura","estado":"falta"}]'
    insertar(con, 1, datetime(2026, 10, 28, 12), "amarillo", porciones=falta)
    insertar(con, 1, datetime(2026, 10, 29, 12), "verde")
    texto = reports.parrafo_padres(con, 1, "Ana Pérez", date(2026, 10, 1), date(2026, 10, 31))
    assert texto.startswith("En estos 2 días, a Ana le sirvieron un plato balanceado 1 de 2 veces.")
    assert "Lo que más le faltó fue verdura: La verdura te ayuda a crecer fuerte." in texto
    insertar(con, 1, datetime(2026, 10, 30, 12), "verde")
    sin = reports.parrafo_padres(con, 1, "Ana Pérez", date(2026, 10, 29), date(2026, 10, 31))
    assert "No le faltó ningún grupo de alimentos. ¡Muy bien!" in sin


def test_periodo_en_espanol():
    assert reports.periodo_texto(date(2026, 10, 1), date(2026, 10, 31)) == "del 1 de octubre al 31 de octubre de 2026"
    assert reports.periodo_texto(date(2026, 9, 15), date(2026, 10, 3)) == "del 15 de septiembre al 3 de octubre de 2026"


def test_varias_paginas(settings):
    con = db.conectar(settings.db_path)
    _ana(con)
    for d in range(1, 29):
        insertar(con, 1, datetime(2026, 10, d, 12), "verde")
    pdf = reports.pdf_historial(con, settings, 1, date(2026, 10, 1), date(2026, 10, 31))
    assert len(re.findall(rb"/Type\s*/Page\b", pdf)) >= 2


def test_ruta_pdf(client, settings):
    login(client, settings, ["docente"], sedes=("IE",))
    con = db.conectar(settings.db_path)
    _ana(con)
    insertar(con, 1, datetime(2026, 10, 29, 12), "verde")
    r = client.get("/estudiantes/1/historial.pdf?desde=2026-10-01&hasta=2026-10-31")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"
    assert 'filename="historial_Perez_2026-10-01_2026-10-31.pdf"' in r.headers["content-disposition"]
    assert con.execute("select count(*) from auditoria where accion='pdf_historial' and estudiante_id=1").fetchone()[0] == 1


def test_ruta_pdf_otra_sede_404(client, settings):
    login(client, settings, ["docente"], sedes=("IE",))
    con = db.conectar(settings.db_path)
    _ana(con, sede="Otra")
    assert client.get("/estudiantes/1/historial.pdf").status_code == 404
    assert con.execute("select count(*) from auditoria where accion='pdf_historial'").fetchone()[0] == 0
