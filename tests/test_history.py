from datetime import date, datetime, timedelta

from nutripae import db, history
from tests.conftest import login


def insertar(con, est, ts, semaforo, modo="camara", porciones='[]', sede="IE", usuario_id=1):
    """Inserta una verificación; crea el usuario si no existe (claves foráneas activas)."""
    if con.execute("select 1 from usuarios where id=?", (usuario_id,)).fetchone() is None:
        con.execute("insert into usuarios(id,usuario,nombre,hash) values(?,?,?,?)",
                    (usuario_id, f"hist{usuario_id}", "H", "x"))
    if est is not None and con.execute("select 1 from estudiantes where id=?", (est,)).fetchone() is None:
        con.execute("insert into estudiantes(id,codigo,nombre,grado,sede,consentimiento) values(?,?,?,?,?,1)",
                    (est, f"E{est}", f"Estudiante {est}", "primaria", sede))
    con.execute("insert into verificaciones(ts,estudiante_id,sede,grado,usuario_id,modo,semaforo,razon_grupo,porciones,nutrientes,total_g) values(?,?,?,?,?,?,?,?,?,?,?)",
                (ts.isoformat(), est, sede, "primaria", usuario_id, modo, semaforo,
                 "verdura" if semaforo != "verde" else None, porciones, '{"kcal": 500}', 300))
    con.commit()


def _estudiante(con, codigo="A", sede="IE Santa Librada"):
    con.execute("insert into estudiantes(codigo,nombre,grado,grupo,sede,orden,consentimiento) values(?,?,?,?,?,?,1)",
                (codigo, "Ana " + codigo, "primaria", "3-A", sede, 1))
    con.commit()
    return con.execute("select id from estudiantes where codigo=?", (codigo,)).fetchone()[0]


def test_ultima_del_dia_cuenta_y_demo_se_excluye(settings):
    con = db.conectar(settings.db_path); hoy = datetime(2026, 10, 29, 12, 0)
    insertar(con, 1, hoy, "rojo", porciones='[{"grupo":"verdura","estado":"falta"}]'); insertar(con, 1, hoy + timedelta(minutes=5), "verde"); insertar(con, 1, hoy + timedelta(minutes=9), "rojo", modo="demo")
    dias = history.dias_estudiante(con, 1, date(2026, 10, 1), date(2026, 10, 31))
    assert len(dias) == 1 and dias[0]["intentos"] == 2 and dias[0]["ultima"]["semaforo"] == "verde"
    assert history.faltas_por_grupo(con, 1, date(2026, 10, 1), date(2026, 10, 31)) == {}


def test_faltas_por_grupo_cuenta_dias_de_la_ultima(settings):
    con = db.conectar(settings.db_path)
    falta = '[{"grupo":"fruta","estado":"falta"}]'
    for dia in (27, 28):
        insertar(con, 1, datetime(2026, 10, dia, 12, 0), "amarillo", porciones=falta)
    insertar(con, 1, datetime(2026, 10, 29, 12, 0), "verde")
    assert history.faltas_por_grupo(con, 1, date(2026, 10, 1), date(2026, 10, 31)) == {"fruta": 2}
    dias = history.dias_estudiante(con, 1, date(2026, 10, 1), date(2026, 10, 31))
    assert [d["fecha"] for d in dias] == [date(2026, 10, 29), date(2026, 10, 28), date(2026, 10, 27)]
    assert dias[1]["ultima"]["porciones"][0]["grupo"] == "fruta" and dias[0]["ultima"]["nutrientes"] == {"kcal": 500}


def test_resumen_sede(settings):
    con = db.conectar(settings.db_path); d = datetime(2026, 10, 29, 12, 0)
    insertar(con, 1, d, "verde"); insertar(con, 2, d, "rojo", porciones='[{"grupo":"verdura","estado":"falta"}]')
    r = history.resumen_sede(con, "IE", None, date(2026, 10, 29), date(2026, 10, 29))
    assert r["por_dia"][0][1] == 50.0 and r["grupo_mas_falta"] == "verdura"


def test_resumen_sede_no_aptos_demo_y_grado(settings):
    con = db.conectar(settings.db_path); d = datetime(2026, 10, 29, 12, 0)
    insertar(con, 1, d, "rojo", porciones='[{"grupo":"proteina","estado":"no_apto"}]')
    insertar(con, 2, d, "verde", modo="demo")
    insertar(con, 3, d, "verde", sede="Otra")
    r = history.resumen_sede(con, "IE", None, date(2026, 10, 29), date(2026, 10, 29))
    assert r["no_aptos"] == 1 and r["por_dia"] == [(date(2026, 10, 29), 0.0, 1)] and r["grupo_mas_falta"] is None
    assert history.resumen_sede(con, "IE", "secundaria", date(2026, 10, 29), date(2026, 10, 29))["por_dia"] == []


def test_consulta_queda_en_auditoria(client, settings):
    login(client, settings, ["nutricionista"])
    con = db.conectar(settings.db_path)
    con.execute("insert into estudiantes(codigo,nombre,grado,grupo,sede,orden,consentimiento) values('A','Ana','primaria','3-A','IE Santa Librada',1,1)"); con.commit()
    assert client.get("/estudiantes/1/historial").status_code == 200
    assert con.execute("select accion from auditoria").fetchone()[0] == "consulta_historial"


def test_historial_de_otra_sede_es_404_y_no_audita(client, settings):
    login(client, settings, ["docente"])
    con = db.conectar(settings.db_path)
    ajeno = _estudiante(con, "B", sede="Otra sede")
    assert client.get(f"/estudiantes/{ajeno}/historial").status_code == 404
    assert client.get("/estudiantes/999/historial").status_code == 404
    assert con.execute("select count(*) from auditoria").fetchone()[0] == 0


def test_historial_muestra_dias_y_enlace_pdf(client, settings):
    login(client, settings, ["docente"])
    con = db.conectar(settings.db_path)
    eid = _estudiante(con)
    insertar(con, eid, datetime.now(), "verde", sede="IE Santa Librada")
    r = client.get(f"/estudiantes/{eid}/historial")
    assert r.status_code == 200 and f"/estudiantes/{eid}/historial.pdf" in r.text and "Ana A" in r.text


def test_resumen_roles_y_sede(client, settings):
    login(client, settings, ["docente"], usuario="d")
    assert client.get("/sedes/IE Santa Librada/resumen").status_code == 403
    login(client, settings, ["nutricionista"], usuario="n")
    r = client.get("/sedes/IE Santa Librada/resumen")
    assert r.status_code == 200 and "Resumen" in r.text
    assert client.get("/sedes/Otra/resumen").status_code == 404
