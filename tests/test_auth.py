import pytest

from nutripae import auth, db


def test_login_y_roles(client, settings):
    con = db.conectar(settings.db_path)
    auth.crear_usuario(con, "doc", "Docente", "s3creta", ["docente"], ["IE Santa Librada"])
    assert client.post("/entrar", data={"usuario": "doc", "contrasena": "mala"}).status_code == 200
    r = client.post("/entrar", data={"usuario": "doc", "contrasena": "s3creta"}, follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/verificar"
    assert client.get("/admin/estudiantes").status_code == 403


def test_sin_sesion_redirige(client):
    r = client.get("/verificar", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"].startswith("/entrar")


def test_verificar_roles_y_sedes(settings):
    con = db.conectar(settings.db_path)
    uid = auth.crear_usuario(con, "n", "Nutri", "pw", ["nutricionista", "admin"], ["A", "B"])
    assert auth.roles_de(con, uid) == {"nutricionista", "admin"}
    assert auth.sedes_de(con, uid) == {"A", "B"}
    assert auth.verificar(con, "n", "pw")["id"] == uid
    assert auth.verificar(con, "n", "otra") is None
    assert auth.verificar(con, "nadie", "pw") is None
    con.execute("UPDATE usuarios SET activo=0 WHERE id=?", (uid,))
    assert auth.verificar(con, "n", "pw") is None


def test_rol_invalido_y_duplicado(settings):
    con = db.conectar(settings.db_path)
    with pytest.raises(ValueError):
        auth.crear_usuario(con, "x", "X", "pw", ["jefe"], [])
    auth.crear_usuario(con, "x", "X", "pw", ["admin"], [])
    with pytest.raises(ValueError, match="El usuario ya existe"):
        auth.crear_usuario(con, "x", "X", "pw", ["admin"], [])


def test_admin_entra_salir_y_raiz(client, settings):
    con = db.conectar(settings.db_path)
    auth.crear_usuario(con, "ad", "Admin", "pw", ["admin"], [])
    assert "Contraseña" in client.get("/entrar").text
    assert "Usuario o contraseña incorrectos" in client.post(
        "/entrar", data={"usuario": "ad", "contrasena": "no"}).text
    client.post("/entrar", data={"usuario": "ad", "contrasena": "pw"})
    assert client.get("/admin/estudiantes").json() == {"ok": True}
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/verificar"
    r = client.post("/salir", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/entrar"
    assert client.get("/verificar", follow_redirects=False).status_code == 302
