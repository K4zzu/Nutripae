import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from nutripae.config import Settings
from nutripae.web.app import crear_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(secret="test", db_path=tmp_path / "t.db", fotos_dir=tmp_path / "fotos",
                    proveedor=None, modelo=None, segmentador="demo")


@pytest.fixture
def app(settings):
    return crear_app(settings)


@pytest.fixture
def client(app):
    return TestClient(app)


def login(client, settings, roles, usuario="u1", contrasena="s3creta", sedes=("IE Santa Librada",)):
    """Crea un usuario y abre sesión con el cliente dado."""
    from nutripae import auth, db
    con = db.conectar(settings.db_path)
    auth.crear_usuario(con, usuario, usuario, contrasena, list(roles), list(sedes))
    r = client.post("/entrar", data={"usuario": usuario, "contrasena": contrasena},
                    follow_redirects=False)
    assert r.status_code == 302
    return r
