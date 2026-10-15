"""Dashboard login: email/password -> session token -> /api access."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PACOS_LOGIN_EMAIL", "abc@pacos.com")
    monkeypatch.setenv("PACOS_LOGIN_PASSWORD", "12345678")
    monkeypatch.setenv("PACOS_LOGIN_TRIAL", "1")
    return TestClient(app)


def _login(client, email="abc@pacos.com", password="12345678"):
    return client.post("/api/login", json={"email": email, "password": password})


def test_api_is_locked_without_login(client):
    assert client.get("/api/stats").status_code == 401
    assert client.get("/api/health").status_code == 200


def test_wrong_password_is_rejected(client):
    assert _login(client, password="nope").status_code == 401
    assert _login(client, email="x@pacos.com").status_code == 401


def test_login_token_unlocks_api(client):
    r = _login(client, email="  ABC@pacos.com ")  # case/space-insensitive email
    assert r.status_code == 200
    headers = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.get("/api/stats", headers=headers).status_code == 200
    bad = {"Authorization": "Bearer not-the-token"}
    assert client.get("/api/stats", headers=bad).status_code == 401


def test_changing_password_invalidates_session(client, monkeypatch):
    token = _login(client).json()["token"]
    monkeypatch.setenv("PACOS_LOGIN_PASSWORD", "new-password")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/stats", headers=headers).status_code == 401


def test_trial_box_only_when_enabled(client, monkeypatch):
    assert client.get("/api/login/trial").json() == {
        "email": "abc@pacos.com", "password": "12345678"}
    monkeypatch.setenv("PACOS_LOGIN_TRIAL", "0")
    assert client.get("/api/login/trial").json() == {"email": "", "password": ""}


def test_no_login_configured_keeps_api_open(monkeypatch):
    monkeypatch.setenv("PACOS_LOGIN_EMAIL", "")
    monkeypatch.setenv("PACOS_LOGIN_PASSWORD", "")
    c = TestClient(app)
    assert c.get("/api/stats").status_code == 200
    assert c.post("/api/login", json={"email": "a", "password": "b"}).status_code == 400
