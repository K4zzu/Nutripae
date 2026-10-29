import io
from datetime import date

import openpyxl
import pytest

from nutripae import db, students
from tests.conftest import login


def xlsx(filas, cab=("codigo", "nombre", "grado", "grupo", "sede", "consentimiento")):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(list(cab))
    [ws.append(list(f)) for f in filas]
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def test_importa_y_reimporta_sin_duplicar(settings):
    con = db.conectar(settings.db_path)
    r = students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE Santa Librada", "sí"),
                                           ("A2", "Luis Gómez", "Transición", "T-1", "IE Santa Librada", "no")]))
    assert (r["creados"], r["actualizados"]) == (2, 0)
    r = students.importar_excel(con, xlsx([("A1", "Ana Pérez", "4°", "4-A", "IE Santa Librada", "sí")]))
    assert (r["creados"], r["actualizados"]) == (0, 1)
    assert con.execute("select count(*) from estudiantes").fetchone()[0] == 2
    assert con.execute("select grado, grupo, consentimiento from estudiantes where codigo='A1'").fetchone()[:] == ("primaria", "4-A", 1)
    assert con.execute("select grado from estudiantes where codigo='A2'").fetchone()[0] == "preescolar"


def test_columna_faltante_da_error_claro(settings):
    con = db.conectar(settings.db_path)
    with pytest.raises(students.ColumnaFaltante) as e:
        students.importar_excel(con, xlsx([("A1", "Ana", "3°", "IE")], cab=("codigo", "nombre", "grado", "sede_x")))
    assert e.value.columna == "sede"


def test_documento_se_guarda_hasheado(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("1023456789", "Ana", "3°", "3-A", "IE", "sí")]), secret="s")
    codigo = con.execute("select codigo from estudiantes").fetchone()[0]
    assert codigo != "1023456789" and len(codigo) == 64


def test_buscar_y_siguiente(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", "sí"),
                                       ("A2", "Luis Gómez", "3°", "3-A", "IE", "sí")]))
    assert [r["nombre"] for r in students.buscar(con, "lu", "IE", "primaria")] == ["Luis Gómez"]
    assert students.siguiente(con, "IE", "primaria", "3-A", date.today())["nombre"] == "Ana Pérez"


def test_buscar_sin_tildes_y_por_cualquier_palabra(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", "sí")]))
    assert len(students.buscar(con, "PEREZ", "IE", None)) == 1
    assert students.buscar(con, "ana per", "IE", None)[0]["nombre"] == "Ana Pérez"
    assert students.buscar(con, "zz", "IE", None) == []


def test_siguiente_salta_verificados_hoy(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana", "3°", "3-A", "IE", "sí"),
                                       ("A2", "Luis", "3°", "3-A", "IE", "sí")]))
    ana = con.execute("select id from estudiantes where codigo='A1'").fetchone()[0]
    hoy = date.today()
    con.execute("insert into verificaciones(ts, estudiante_id, sede, modo) values(?,?,?,?)",
                (hoy.isoformat() + "T10:00:00", ana, "IE", "demo"))
    assert students.siguiente(con, "IE", "primaria", "3-A", hoy)["nombre"] == "Ana"
    con.execute("insert into verificaciones(ts, estudiante_id, sede, modo) values(?,?,?,?)",
                (hoy.isoformat() + "T10:01:00", ana, "IE", "camara"))
    assert students.siguiente(con, "IE", "primaria", "3-A", hoy)["nombre"] == "Luis"


def test_filas_invalidas_se_reportan(settings):
    con = db.conectar(settings.db_path)
    r = students.importar_excel(con, xlsx([("", "Sin código", "3°", "g", "IE", "sí"),
                                           ("A1", "Raro", "xyz", "g", "IE", "sí"),
                                           ("A2", "Bien", "7-B", "7-B", "IE", "si")]))
    assert r["creados"] == 1 and len(r["errores"]) == 2
    assert "2" in r["errores"][0] and "3" in r["errores"][1]


def test_consentimiento_y_baja(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana", "3°", "3-A", "IE", "no")]))
    i = con.execute("select id from estudiantes").fetchone()[0]
    students.set_consentimiento(con, i, True)
    assert con.execute("select consentimiento from estudiantes").fetchone()[0] == 1
    students.dar_de_baja(con, i)
    assert con.execute("select activo from estudiantes").fetchone()[0] == 0
    assert students.buscar(con, "", "IE", None) == []


def _cargar(client, datos):
    return client.post("/admin/estudiantes/cargar", files={"archivo": ("e.xlsx", datos)},
                       follow_redirects=False)


def test_ruta_cargar_y_listar(client, settings):
    login(client, settings, ["admin"])
    r = _cargar(client, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE Santa Librada", "sí")]))
    assert r.status_code == 303 and "creados=1" in r.headers["location"]
    p = client.get("/admin/estudiantes?creados=1&actualizados=0&errores=0")
    assert p.status_code == 200 and "Ana Pérez" in p.text and "IE Santa Librada" in p.text


def test_ruta_columna_faltante(client, settings):
    login(client, settings, ["admin"])
    r = _cargar(client, xlsx([("A1", "Ana", "3°", "IE")], cab=("codigo", "nombre", "grado", "sede_x")))
    assert r.status_code == 400 and "Falta la columna «sede» en el archivo" in r.text


def test_rutas_admin_exigen_admin(client, settings):
    login(client, settings, ["docente"])
    assert client.get("/admin/estudiantes").status_code == 403
    assert _cargar(client, xlsx([])).status_code == 403


def test_consentimiento_y_baja_por_ruta(client, settings):
    login(client, settings, ["admin"])
    _cargar(client, xlsx([("A1", "Ana", "3°", "3-A", "IE Santa Librada", "no")]))
    con = db.conectar(settings.db_path)
    i = con.execute("select id from estudiantes").fetchone()[0]
    assert client.post(f"/admin/estudiantes/{i}/consentimiento", data={"valor": "1"},
                       follow_redirects=False).status_code == 303
    assert con.execute("select consentimiento from estudiantes").fetchone()[0] == 1
    client.post(f"/admin/estudiantes/{i}/baja", follow_redirects=False)
    assert con.execute("select activo from estudiantes").fetchone()[0] == 0


def _sembrar(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE Santa Librada", "sí"),
                                       ("B1", "Ana Ruiz", "3°", "3-A", "Otra Sede", "sí")]))


def test_api_buscar_limitada_a_sedes(client, settings):
    _sembrar(settings)
    login(client, settings, ["docente"])
    r = client.get("/api/estudiantes/buscar", params={"q": "ana", "grado": "primaria"})
    assert [e["nombre"] for e in r.json()] == ["Ana Pérez"]
    assert set(r.json()[0]) == {"id", "nombre", "grado", "grupo", "sede"}


def test_api_buscar_admin_ve_todas(client, settings):
    _sembrar(settings)
    login(client, settings, ["admin"])
    assert len(client.get("/api/estudiantes/buscar", params={"q": "ana"}).json()) == 2


def test_api_siguiente(client, settings):
    _sembrar(settings)
    login(client, settings, ["docente"])
    r = client.get("/api/estudiantes/siguiente", params={"grado": "primaria", "grupo": ""})
    assert r.json()["nombre"] == "Ana Pérez"
    assert client.get("/api/estudiantes/siguiente", params={"grado": "secundaria"}).json() is None


def test_api_requiere_sesion(client):
    r = client.get("/api/estudiantes/buscar", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/entrar"
