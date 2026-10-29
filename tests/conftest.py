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
