from datetime import date, datetime

from nutripae import db, retention
from tests.test_history import insertar


def test_borra_fotos_antiguas_y_conserva_datos(settings):
    con = db.conectar(settings.db_path)
    settings.fotos_dir.mkdir(parents=True); (settings.fotos_dir / "v.jpg").write_bytes(b"x")
    insertar(con, 1, datetime(2025, 3, 1, 12), "verde"); con.execute("update verificaciones set foto='v.jpg'")
    assert retention.borrar_fotos_antes(con, settings, date(2026, 1, 1)) == 1
    assert not (settings.fotos_dir / "v.jpg").exists() and con.execute("select count(*) from verificaciones").fetchone()[0] == 1


def test_conserva_fotos_recientes_y_borra_entrenamiento(settings):
    con = db.conectar(settings.db_path)
    (settings.fotos_dir / "e").mkdir(parents=True)
    for n in ("vieja.jpg", "nueva.jpg", "e/orig.jpg"):
        (settings.fotos_dir / n).write_bytes(b"x")
    insertar(con, 1, datetime(2025, 12, 31, 23, 59), "verde")
    insertar(con, 1, datetime(2026, 1, 1, 0, 1), "verde")
    con.execute("update verificaciones set foto='vieja.jpg' where id=1")
    con.execute("update verificaciones set foto='nueva.jpg' where id=2")
    con.execute("insert into fotos_entrenamiento(verificacion_id, ruta, ts) values(1, 'e/orig.jpg', ?)",
                (datetime(2025, 12, 31, 23, 59).isoformat(),))
    con.execute("insert into fotos_entrenamiento(verificacion_id, ruta, ts) values(1, 'falta.jpg', ?)",
                (datetime(2025, 6, 1).isoformat(),))
    con.commit()
    assert retention.borrar_fotos_antes(con, settings, date(2026, 1, 1)) == 3
    assert (settings.fotos_dir / "nueva.jpg").exists()
    assert not (settings.fotos_dir / "e" / "orig.jpg").exists()
    assert [r[0] for r in con.execute("select foto from verificaciones order by id")] == [None, "nueva.jpg"]
    assert con.execute("select count(*) from fotos_entrenamiento").fetchone()[0] == 0


def test_no_borra_fuera_de_la_carpeta_de_fotos(settings, tmp_path):
    con = db.conectar(settings.db_path)
    settings.fotos_dir.mkdir(parents=True)
    afuera = tmp_path / "afuera.txt"; afuera.write_bytes(b"x")
    insertar(con, 1, datetime(2025, 3, 1, 12), "verde")
    con.execute("update verificaciones set foto='../afuera.txt'"); con.commit()
    assert retention.borrar_fotos_antes(con, settings, date(2026, 1, 1)) == 1
    assert afuera.exists()


def test_comando_borrar_fotos_antiguas(settings, monkeypatch, capsys):
    from nutripae import cli
    con = db.conectar(settings.db_path)
    settings.fotos_dir.mkdir(parents=True); (settings.fotos_dir / "v.jpg").write_bytes(b"x")
    insertar(con, 1, datetime(2025, 3, 1, 12), "verde"); con.execute("update verificaciones set foto='v.jpg'")
    con.commit(); con.close()
    monkeypatch.setattr(cli.config, "cargar", lambda: settings)
    assert cli.main(["borrar-fotos-antiguas", "--antes", "2026-01-01"]) == 0
    assert "Fotos eliminadas: 1" in capsys.readouterr().out
    assert not (settings.fotos_dir / "v.jpg").exists()


def test_cookie_segura_con_https(settings):
    from fastapi.testclient import TestClient
    from nutripae.web.app import crear_app
    from tests.conftest import login
    settings.https = True
    c = TestClient(crear_app(settings), base_url="https://testserver")
    r = login(c, settings, ["docente"])
    assert "secure" in r.headers["set-cookie"].lower()


def test_https_desde_entorno(monkeypatch):
    from nutripae import config
    monkeypatch.setenv("NUTRIPAE_HTTPS", "1")
    assert config.cargar().https is True
    monkeypatch.setenv("NUTRIPAE_HTTPS", "0")
    assert config.cargar().https is False
