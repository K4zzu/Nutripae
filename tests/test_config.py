import pytest

from nutripae import config

CLAVES = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "NUTRIPAE_PROVEEDOR")


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda *a, **k: None)
    for c in CLAVES:
        monkeypatch.delenv(c, raising=False)


def test_sin_claves_no_hay_proveedor():
    assert config.cargar().proveedor is None


def test_detecta_openai_por_su_clave(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    assert config.cargar().proveedor == "openai"


def test_orden_de_deteccion(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    assert config.cargar().proveedor == "anthropic"


def test_proveedor_explicito_con_su_clave(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("NUTRIPAE_PROVEEDOR", "gemini")
    assert config.cargar().proveedor == "gemini"


def test_proveedor_explicito_sin_clave_avisa_y_detecta(monkeypatch, caplog):
    monkeypatch.setenv("NUTRIPAE_PROVEEDOR", "anthropic")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    with caplog.at_level("WARNING", logger="nutripae"):
        assert config.cargar().proveedor == "openai"
    assert "ANTHROPIC_API_KEY" in caplog.text


def test_proveedor_explicito_sin_ninguna_clave(monkeypatch):
    monkeypatch.setenv("NUTRIPAE_PROVEEDOR", "openai")
    assert config.cargar().proveedor is None
