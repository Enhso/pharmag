import os
import re

import pytest
from fastapi.testclient import TestClient

from pharmag.api import DISCLAIMER, STATIC_DIR, app

GOOD_ENV = {
    "OPENAI_API_KEY": "sk-test-key",
    "OPENAI_BASE_URL": "https://llm.example/v1",
    "OPENAI_MODEL": "some-model",
    "OPENAI_EMBEDDING_MODEL": "some-embedding-model",
}
# The defects seen in a real env file: quoted values and a misspelled variable name.
BAD_ENV = {
    "OPENAI_API_KEY": "'sk-FAKE-leak-check-123'",
    "OPENAI_BASE_UR": "'https://llm.example/v1'",
    "OPENAI_MODEL": "'some-model'",
    "OPENAI_EMBEDDING_MODEL": "'some-embedding-model'",
}


@pytest.fixture
def client_for(monkeypatch):
    """Start the app (so startup reads the environment) with exactly these OPENAI_* values."""

    def start(env):
        for name in [n for n in os.environ if n.startswith("OPENAI_")]:
            monkeypatch.delenv(name)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        return TestClient(app)

    return start


def test_health_is_ok_with_valid_config(client_for):
    with client_for(GOOD_ENV) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_degraded_but_200_with_invalid_config(client_for):
    with client_for(BAD_ENV) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert [p["variable"] for p in body["config_problems"]] == [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        "OPENAI_EMBEDDING_MODEL",
    ]
    assert "OPENAI_BASE_UR" in body["config_problems"][1]["problem"]
    assert "sk-FAKE-leak-check-123" not in response.text


def test_server_starts_with_no_configuration_at_all(client_for):
    with client_for({}) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert len(response.json()["config_problems"]) == 4


def test_ask_returns_the_placeholder_with_valid_config(client_for):
    with client_for(GOOD_ENV) as client:
        response = client.post("/ask", json={"question": "What is aspirin used for?"})
    assert response.status_code == 200
    body = response.json()
    assert "placeholder" in body["answer"].lower()
    assert body["sources"] == []
    assert body["disclaimer"] == DISCLAIMER
    assert "not medical advice" in DISCLAIMER


def test_ask_is_503_and_names_the_bad_variables_with_invalid_config(client_for):
    with client_for(BAD_ENV) as client:
        response = client.post("/ask", json={"question": "What is aspirin used for?"})
    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "configuration"
    assert {p["variable"] for p in body["config_problems"]} == set(GOOD_ENV)
    assert "sk-FAKE-leak-check-123" not in response.text


@pytest.mark.parametrize("body", [{}, {"question": ""}, {"question": 5}, {"q": "x"}])
def test_ask_rejects_a_malformed_body_with_422(client_for, body):
    with client_for(GOOD_ENV) as client:
        assert client.post("/ask", json=body).status_code == 422


def test_root_serves_the_page_and_its_assets(client_for):
    with client_for(GOOD_ENV) as client:
        page = client.get("/")
        script = client.get("/static/app.js")
        style = client.get("/static/style.css")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert '<label for="question">' in page.text
    assert script.status_code == 200
    assert style.status_code == 200


def test_the_page_loads_nothing_from_another_host():
    for path in STATIC_DIR.iterdir():
        assert not re.search(r"https?://|//[a-z]", path.read_text()), path.name
