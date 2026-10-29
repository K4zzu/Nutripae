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


# --- una conexión por hilo -------------------------------------------------------------------

def test_conexion_por_hilo_aisla_transacciones(tmp_path):
    import threading
    from nutripae import db
    proxy = db.ConexionPorHilo(tmp_path / "h.db")
    principal = proxy.actual()
    listo, rollback_hecho = threading.Event(), threading.Event()
    otra = {}

    def hilo():
        otra["con"] = proxy.actual()
        listo.wait(5)
        proxy.rollback()  # no debe deshacer la inserción pendiente del otro hilo
        rollback_hecho.set()

    t = threading.Thread(target=hilo)
    t.start()
    proxy.execute("INSERT INTO parametros(clave, valor) VALUES('x', '1')")
    assert proxy.in_transaction
    listo.set()
    rollback_hecho.wait(5)
    t.join(5)
    assert otra["con"] is not principal
    proxy.commit()
    assert db.conectar(tmp_path / "h.db").execute("SELECT valor FROM parametros WHERE clave='x'").fetchone()[0] == "1"
    assert proxy.row_factory is not None
    proxy.close()


def test_app_usa_conexion_por_hilo(app):
    from nutripae import db
    assert isinstance(app.state.con, db.ConexionPorHilo)
    assert isinstance(db.conectar(app.state.settings.db_path), __import__("sqlite3").Connection)
