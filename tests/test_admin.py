from tests.conftest import login
from tests.test_verify_api import foto
from nutripae import auth, db, foods


def test_admin_crea_usuario_y_docente_no_puede(client, settings):
    login(client, settings, ["admin"])
    r = client.post("/admin/usuarios", data={"usuario": "nut", "nombre": "N", "contrasena": "x12345", "roles": ["nutricionista"], "sedes": ["IE"]}, follow_redirects=False)
    assert r.status_code == 302
    client.post("/salir"); login(client, settings, ["docente"], usuario="doc2")
    assert client.post("/admin/usuarios", data={}).status_code == 403


def test_parametros_cambian_el_veredicto(client, settings):
    login(client, settings, ["admin"])
    client.post("/admin/parametros", data={"factor_corto": "0.95", "factor_excedido": "1.8"})
    j = client.post("/api/verificar", files={"foto": foto()}, data={"modo": "demo", "escenario": "completa", "grado": "primaria"}).json()
    assert j["semaforo"] in ("amarillo", "verde")  # el valor se lee de la BD sin reiniciar
    assert db.param(db.conectar(settings.db_path), "umbrales", {})["factor_corto"] == 0.95


def test_usuario_nuevo_queda_con_roles_y_sedes_y_aparece_en_la_lista(client, settings):
    login(client, settings, ["admin"])
    client.post("/admin/usuarios", data={"usuario": "nut", "nombre": "Ana", "contrasena": "x12345",
                                         "roles": ["nutricionista"], "sedes": ["IE"], "otra_sede": "Sede Norte"})
    con = db.conectar(settings.db_path)
    u = con.execute("SELECT * FROM usuarios WHERE usuario='nut'").fetchone()
    assert auth.roles_de(con, u["id"]) == {"nutricionista"}
    assert auth.sedes_de(con, u["id"]) == {"IE", "Sede Norte"}
    assert "Ana" in client.get("/admin/usuarios").text


def test_usuario_duplicado_y_validaciones(client, settings):
    login(client, settings, ["admin"])
    base = {"usuario": "nut", "nombre": "N", "contrasena": "x12345", "roles": ["docente"]}
    assert client.post("/admin/usuarios", data=base, follow_redirects=False).status_code == 302
    r = client.post("/admin/usuarios", data=base)
    assert r.status_code == 400 and "El usuario ya existe" in r.text
    r = client.post("/admin/usuarios", data={**base, "usuario": "otro", "contrasena": "123"})
    assert r.status_code == 400 and "al menos 6" in r.text
    r = client.post("/admin/usuarios", data={"usuario": "otro", "nombre": "N", "contrasena": "x12345"})
    assert r.status_code == 400 and "rol" in r.text


def test_desactivar_usuario_y_no_a_si_mismo(client, settings):
    login(client, settings, ["admin"], usuario="adm")
    client.post("/admin/usuarios", data={"usuario": "doc", "nombre": "D", "contrasena": "x12345", "roles": ["docente"]})
    con = db.conectar(settings.db_path)
    uid = con.execute("SELECT id FROM usuarios WHERE usuario='doc'").fetchone()["id"]
    yo = con.execute("SELECT id FROM usuarios WHERE usuario='adm'").fetchone()["id"]
    r = client.post(f"/admin/usuarios/{yo}/desactivar")
    assert r.status_code == 400 and "No puedes desactivar tu propio usuario" in r.text
    assert client.post(f"/admin/usuarios/{uid}/desactivar", follow_redirects=False).status_code == 302
    assert con.execute("SELECT activo FROM usuarios WHERE id=?", (uid,)).fetchone()["activo"] == 0


def test_parametros_validan_y_conservan_lo_no_enviado(client, settings):
    login(client, settings, ["admin"])
    assert client.post("/admin/parametros", data={"objetivo_proteina": "1.5"}).status_code == 400
    assert client.post("/admin/parametros", data={"factor_corto": "0"}).status_code == 400
    assert client.post("/admin/parametros", data={"factor_corto": "abc"}).status_code == 400
    r = client.post("/admin/parametros", data={"plato_minimo_primaria": "200", "objetivo_proteina": "0.3"}, follow_redirects=False)
    assert r.status_code == 302
    u = db.param(db.conectar(settings.db_path), "umbrales", {})
    assert u["plato_minimo_g"] == {"preescolar": 125, "primaria": 200, "secundaria": 225}
    assert u["objetivo"]["proteina"] == 0.3 and u["objetivo"]["verdura_fruta"] == 0.5
    assert u["factor_excedido"] == 1.8
    assert client.post("/admin/parametros/restablecer", follow_redirects=False).status_code == 302
    assert db.param(db.conectar(settings.db_path), "umbrales", {})["plato_minimo_g"]["primaria"] == 175


def test_alimento_extra_aparece_en_api_y_se_quita(client, settings):
    login(client, settings, ["admin"])
    r = client.post("/admin/parametros/alimentos", data={"clave": "sancocho_x", "nombre": "Sancocho", "grupo": "proteina"}, follow_redirects=False)
    assert r.status_code == 302
    lista = {a["clave"]: a for a in client.get("/api/alimentos").json()}
    assert lista["sancocho_x"]["grupo"] == "proteina" and lista["sancocho_x"]["nombre"] == "Sancocho"
    assert "Sancocho" in client.get("/admin/parametros").text
    assert client.post("/admin/parametros/alimentos", data={"clave": "arroz_blanco", "nombre": "X", "grupo": "fruta"}).status_code == 400
    assert client.post("/admin/parametros/alimentos", data={"clave": "nuevo", "nombre": "X", "grupo": "nada"}).status_code == 400
    assert client.post("/admin/parametros/alimentos", data={"clave": "Mal Slug", "nombre": "X", "grupo": "fruta"}).status_code == 400
    client.post("/admin/parametros/alimentos/sancocho_x/quitar")
    assert "sancocho_x" not in {a["clave"] for a in client.get("/api/alimentos").json()}


def test_catalogo_fusiona_extras_sin_pisar_los_propios(settings):
    con = db.conectar(settings.db_path)
    db.set_param(con, "alimentos_extra", [{"clave": "arroz_blanco", "nombre": "Falso", "grupo": "fruta"},
                                          {"clave": "mazamorra", "nombre": "Mazamorra", "grupo": "bebida"}])
    cat = foods.catalogo(con)
    assert cat["arroz_blanco"][0] != "Falso" and cat["mazamorra"] == ("Mazamorra", "bebida")
    assert foods.grupo_de("mazamorra", con) == "bebida" and foods.grupo_de("mazamorra") == "otro"


def test_admin_requiere_rol_y_menu(client, settings):
    login(client, settings, ["docente"])
    assert client.get("/admin/usuarios").status_code == 403
    assert client.get("/admin/parametros").status_code == 403
    client.post("/salir"); login(client, settings, ["admin"], usuario="adm")
    t = client.get("/admin/usuarios").text
    assert "Administración" in t and "/admin/parametros" in t
