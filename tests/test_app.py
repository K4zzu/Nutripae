def test_salud(client):
    assert client.get("/salud").json() == {"ok": True}


def test_parametros_guardan_json(settings):
    from nutripae import db
    con = db.conectar(settings.db_path)
    assert db.param(con, "umbrales", {"x": 1}) == {"x": 1}
    db.set_param(con, "umbrales", {"x": 2})
    assert db.param(con, "umbrales", None) == {"x": 2}


def test_esquema_tiene_tablas(settings):
    from nutripae import db
    con = db.conectar(settings.db_path)
    tablas = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    assert {"usuarios", "estudiantes", "tarjetas", "verificaciones", "correcciones", "parametros", "auditoria"} <= tablas
