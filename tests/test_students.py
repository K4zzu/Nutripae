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


# --- recarga del listado sin columna de consentimiento y códigos reutilizados -------------------

def _tarjeta(con, estudiante_id, codigo="QR1"):
    con.execute("INSERT INTO tarjetas(codigo, estudiante_id, activa) VALUES(?,?,1)", (codigo, estudiante_id))
    con.commit()


def test_recarga_sin_columna_conserva_consentimiento_y_tarjeta(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", "sí")]))
    i = con.execute("select id from estudiantes where codigo='A1'").fetchone()[0]
    _tarjeta(con, i)
    r = students.importar_excel(con, xlsx([("A1", "Ana Pérez", "4°", "4-A", "IE"), ("A9", "Nuevo Niño", "3°", "3-A", "IE")],
                                          cab=("codigo", "nombre", "grado", "grupo", "sede")))
    assert (r["creados"], r["actualizados"]) == (1, 1)
    assert con.execute("select consentimiento, grupo from estudiantes where codigo='A1'").fetchone()[:] == (1, "4-A")
    assert con.execute("select consentimiento from estudiantes where codigo='A9'").fetchone()[0] == 0
    assert con.execute("select activa from tarjetas where codigo='QR1'").fetchone()[0] == 1


def test_recarga_con_consentimiento_no_cancela_tarjeta(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", "sí")]))
    i = con.execute("select id from estudiantes").fetchone()[0]
    _tarjeta(con, i)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", "no")]))
    assert con.execute("select consentimiento from estudiantes").fetchone()[0] == 0
    assert con.execute("select activa from tarjetas where codigo='QR1'").fetchone()[0] == 0


def test_codigo_reutilizado_con_otro_nombre_no_renombra(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", "sí")]))
    r = students.importar_excel(con, xlsx([("A1", "Carlos Ruiz", "5°", "5-A", "IE", "no")]))
    assert r["actualizados"] == 0
    assert r["errores"] == ["Fila 2: el código ya pertenece a otro estudiante (posible código reutilizado)"]
    assert con.execute("select nombre, grupo, consentimiento from estudiantes").fetchone()[:] == ("Ana Pérez", "3-A", 1)


def test_mismo_nombre_normalizado_si_actualiza(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", "sí")]))
    r = students.importar_excel(con, xlsx([("A1", "  ANA   perez ", "4°", "4-B", "IE Nueva", "no")]))
    assert r["errores"] == [] and r["actualizados"] == 1
    assert con.execute("select grupo, sede, consentimiento from estudiantes").fetchone()[:] == ("4-B", "IE Nueva", 0)


# --- celda de consentimiento vacía y orden de filas rechazadas -----------------------------------

def test_recarga_con_celda_vacia_conserva_consentimiento_y_tarjeta(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", "sí")]))
    _tarjeta(con, con.execute("select id from estudiantes").fetchone()[0])
    r = students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", None)]))
    assert r["actualizados"] == 1
    assert con.execute("select consentimiento from estudiantes").fetchone()[0] == 1
    assert con.execute("select activa from tarjetas where codigo='QR1'").fetchone()[0] == 1


@pytest.mark.parametrize("valor", ["no", "NO", "0", "false", "n"])
def test_no_explicito_quita_consentimiento_y_cancela_tarjeta(settings, valor):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", "sí")]))
    _tarjeta(con, con.execute("select id from estudiantes").fetchone()[0])
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", valor)]))
    assert con.execute("select consentimiento from estudiantes").fetchone()[0] == 0
    assert con.execute("select activa from tarjetas where codigo='QR1'").fetchone()[0] == 0


def test_nuevo_con_celda_vacia_queda_sin_consentimiento(settings):
    con = db.conectar(settings.db_path)
    r = students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", "")]))
    assert r["creados"] == 1
    assert con.execute("select consentimiento from estudiantes").fetchone()[0] == 0


def test_codigo_reutilizado_no_gasta_puesto_en_la_lista(settings):
    con = db.conectar(settings.db_path)
    students.importar_excel(con, xlsx([("A1", "Ana Pérez", "3°", "3-A", "IE", "sí")]))
    students.importar_excel(con, xlsx([("A1", "Carlos Ruiz", "3°", "3-A", "IE", "sí"),
                                       ("A2", "Luis Gómez", "3°", "3-A", "IE", "sí")]))
    assert con.execute("select orden from estudiantes where codigo='A2'").fetchone()[0] == 1


def test_carga_tiene_zona_de_arrastre(client, settings):
    login(client, settings, ["admin"])
    html = client.get("/admin/estudiantes").text
    assert 'id="zona-arrastre"' in html and "Arrastra" in html
    assert "/static/admin_estudiantes.js" in html
