"""Modo «Pasar lista»: cursos disponibles, lista del curso con quién ya pasó hoy y la pantalla."""
from datetime import date

from nutripae import db, students
from tests.conftest import login
from tests.test_students import xlsx


def _sembrar(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "1°", "1A", "IE Santa Librada", "sí"),
                                       ("A2", "Luis Mora", "1°", "1A", "IE Santa Librada", "no"),
                                       ("A3", "Eva Díaz", "3°", "3A", "IE Santa Librada", "sí"),
                                       ("B1", "Ana Ruiz", "1°", "1A", "Otra Sede", "sí")]))
    return con


def test_cursos_de_una_sede_en_orden_del_archivo(settings):
    con = _sembrar(settings)
    assert students.cursos(con, ["IE Santa Librada"]) == [
        {"sede": "IE Santa Librada", "grado": "primaria", "grupo": "1A", "total": 2},
        {"sede": "IE Santa Librada", "grado": "primaria", "grupo": "3A", "total": 1},
    ]


def test_lista_curso_marca_quien_ya_paso_hoy(settings):
    con = _sembrar(settings)
    hoy = date.today()
    luis = con.execute("select id from estudiantes where codigo='A2'").fetchone()[0]
    con.execute("insert into verificaciones(ts, estudiante_id, sede, modo) values(?,?,?,?)",
                (hoy.isoformat() + "T10:00:00", luis, "IE Santa Librada", "camara"))
    lista = students.lista_curso(con, "IE Santa Librada", "1A", hoy)
    assert [(e["nombre"], e["verificado_hoy"]) for e in lista] == [("Ana Pérez", False), ("Luis Mora", True)]
    assert set(lista[0]) == {"id", "nombre", "grado", "grupo", "sede", "verificado_hoy"}


def test_lista_curso_ignora_practica_y_otros_dias(settings):
    con = _sembrar(settings)
    hoy = date.today()
    ana = con.execute("select id from estudiantes where codigo='A1'").fetchone()[0]
    con.execute("insert into verificaciones(ts, estudiante_id, sede, modo) values(?,?,?,?)",
                (hoy.isoformat() + "T10:00:00", ana, "IE Santa Librada", "demo"))
    con.execute("insert into verificaciones(ts, estudiante_id, sede, modo) values(?,?,?,?)",
                ("2020-01-01T10:00:00", ana, "IE Santa Librada", "camara"))
    assert students.lista_curso(con, "IE Santa Librada", "1A", hoy)[0]["verificado_hoy"] is False


def test_api_cursos_limitada_a_sedes(client, settings):
    _sembrar(settings)
    login(client, settings, ["docente"])
    r = client.get("/api/estudiantes/cursos")
    assert r.status_code == 200
    assert [(c["sede"], c["grupo"], c["total"]) for c in r.json()] == [
        ("IE Santa Librada", "1A", 2), ("IE Santa Librada", "3A", 1)]


def test_api_lista_curso_de_otra_sede_no_se_entrega(client, settings):
    _sembrar(settings)
    login(client, settings, ["docente"])
    ok = client.get("/api/estudiantes/lista", params={"sede": "IE Santa Librada", "grupo": "1A"})
    assert [e["nombre"] for e in ok.json()] == ["Ana Pérez", "Luis Mora"]
    assert ok.json()[0]["verificado_hoy"] is False
    otra = client.get("/api/estudiantes/lista", params={"sede": "Otra Sede", "grupo": "1A"})
    assert otra.status_code == 403


def test_pantalla_tiene_modo_pasar_lista(client, settings):
    login(client, settings, ["docente"])
    html = client.get("/verificar").text
    for ident in ('id="pase-curso"', 'id="btn-pase"', 'id="pase-banda"', 'id="btn-pase-no-esta"', 'id="btn-pase-terminar"'):
        assert ident in html
    assert "Pasar lista" in html
