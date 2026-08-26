import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.config import settings
from backend.routes import dev_demo


def _paths(app: FastAPI) -> set[str]:
    return set(app.openapi()["paths"])


def test_demo_login_nao_e_registrado_em_producao(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    app = FastAPI()

    dev_demo.registrar_rota_demo(app)

    assert "/api/v1/dev/demo-login" not in _paths(app)


def test_demo_login_permanece_inacessivel_se_router_for_incluido_em_producao(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    app = FastAPI()
    app.include_router(dev_demo.router)

    response = TestClient(app).post("/api/v1/dev/demo-login")

    assert response.status_code == 404


@pytest.mark.parametrize("environment", ["dev", "test", " DEV ", "TEST"])
def test_demo_login_so_e_registrado_em_ambientes_permitidos(monkeypatch, environment):
    monkeypatch.setattr(settings, "app_env", environment)
    app = FastAPI()

    dev_demo.registrar_rota_demo(app)

    assert "/api/v1/dev/demo-login" in _paths(app)
