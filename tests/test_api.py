import asyncio
import json
import logging
import os
import re
import threading
import time

import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from pharmag.api import DISCLAIMER, STATIC_DIR, _scrub, app
from pharmag.models import AskResponse, CriticReport, Plan, TraceEvent, Usage
from pharmag.pipeline import PipelineError

def test_importing_the_api_enables_the_pipelines_usage_lines_without_touching_the_root_logger():
    assert logging.getLogger("pharmag.pipeline").isEnabledFor(logging.INFO)
    assert not logging.getLogger("openai").isEnabledFor(logging.INFO)


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


KEY = GOOD_ENV["OPENAI_API_KEY"]
ENGINE = object()  # the fakes never look inside it
FAKE_RESPONSE = AskResponse(
    answer="Fake answer [1].",
    sources=["dailymed-warfarin.md"],
    citations=[],
    plan=Plan(in_scope=True, reason="r", sub_questions=[]),
    tool_calls=[],
    critic=CriticReport(
        review_rounds=1, verdicts=[], removed=[], cautions=[], unmarked=[], marker_check="passed"
    ),
    disclaimer=DISCLAIMER,
    timings={"total": 0.1},
    usage=Usage(),
)


class Fakes:
    """Stand-ins for build_engine and answer; the knobs are set by each test."""

    def __init__(self):
        self.build_calls = 0
        self.fail_first = 0  # the first this-many build attempts raise
        self.fail_text = f"embedding call failed for key {KEY}"
        self.hold = False  # while true, a build attempt waits
        self.pipeline_error = None
        self.script = None  # an async function of emit that runs inside the fake answer


@pytest.fixture
def fakes(monkeypatch):
    fakes = Fakes()

    async def build_engine(settings, corpus_dir):
        fakes.build_calls += 1
        while fakes.hold:
            await asyncio.sleep(0.01)
        if fakes.build_calls <= fakes.fail_first:
            raise RuntimeError(fakes.fail_text)
        return ENGINE

    async def answer(question, engine, emit=None):
        assert engine is ENGINE
        if fakes.script:
            await fakes.script(emit)
        if fakes.pipeline_error:
            raise fakes.pipeline_error
        return FAKE_RESPONSE

    # api.py bound these names at import, so patch them where they are used.
    monkeypatch.setattr("pharmag.api.build_engine", build_engine)
    monkeypatch.setattr("pharmag.api.answer", answer)
    monkeypatch.setattr("pharmag.api.RETRY_PAUSES", (0, 0, 0))
    return fakes


def wait_for_index(client, state):
    deadline = time.monotonic() + 5
    while client.get("/health").json().get("index") != state:
        assert time.monotonic() < deadline, f"index never became {state}"
        time.sleep(0.01)


@pytest.fixture
def client_for(monkeypatch, fakes):
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
        wait_for_index(client, "ready")
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "index": "ready"}


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


def test_health_says_building_while_the_build_is_held_then_ready(client_for, fakes):
    fakes.hold = True
    with client_for(GOOD_ENV) as client:
        held = client.get("/health")
        fakes.hold = False
        wait_for_index(client, "ready")
    assert held.status_code == 200
    assert held.json() == {"status": "ok", "index": "building"}


def test_ask_waits_for_the_build_and_returns_every_contract_field(client_for, fakes):
    fakes.hold = True
    with client_for(GOOD_ENV) as client:
        threading.Timer(0.3, lambda: setattr(fakes, "hold", False)).start()
        response = client.post("/ask", json={"question": "What is aspirin used for?"})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == set(AskResponse.model_fields)
    assert body == FAKE_RESPONSE.model_dump(mode="json")
    assert body["disclaimer"] == DISCLAIMER
    assert "not medical advice" in DISCLAIMER


def test_a_build_that_fails_every_attempt_gives_503_and_a_later_ask_rebuilds(client_for, fakes):
    fakes.fail_first = 8  # all four attempts of the startup build and of the first rebuild
    with client_for(GOOD_ENV) as client:
        wait_for_index(client, "failed")
        health = client.get("/health").json()
        first = client.post("/ask", json={"question": "q"})
        second = client.post("/ask", json={"question": "q"})
    assert fakes.build_calls == 9
    assert "embedding call failed" in health["index_error"]
    assert first.status_code == 503
    assert first.json()["error"] == "index"
    assert second.status_code == 200


def test_a_build_that_fails_twice_then_succeeds_ends_ready(client_for, fakes):
    fakes.fail_first = 2
    with client_for(GOOD_ENV) as client:
        wait_for_index(client, "ready")
    assert fakes.build_calls == 3


def test_a_pipeline_error_gives_502_with_the_stage(client_for, fakes):
    fakes.pipeline_error = PipelineError("write", "the model returned no draft")
    with client_for(GOOD_ENV) as client:
        response = client.post("/ask", json={"question": "q"})
    assert response.status_code == 502
    body = response.json()
    assert (body["error"], body["stage"]) == ("pipeline", "write")
    assert "the model returned no draft" in body["detail"]


def test_the_api_key_in_an_exception_text_never_reaches_a_response(client_for, fakes):
    fakes.fail_first = 8
    with client_for(GOOD_ENV) as client:
        wait_for_index(client, "failed")
        health = client.get("/health")
        index_failure = client.post("/ask", json={"question": "q"})
        fakes.pipeline_error = PipelineError("review", f"rejected key {KEY}")
        pipeline_failure = client.post("/ask", json={"question": "q"})
    assert (index_failure.status_code, pipeline_failure.status_code) == (503, 502)
    for response in (health, index_failure, pipeline_failure):
        assert KEY not in response.text


def test_a_defective_config_starts_no_build(client_for, fakes):
    with client_for(BAD_ENV) as client:
        client.get("/health")
        client.post("/ask", json={"question": "q"})
    assert fakes.build_calls == 0


@given(st.text(), st.text(), st.builds("sk-{}".format, st.text("abc0129", min_size=1)))
def test_scrub_removes_every_occurrence_of_the_key(before, after, key):
    assert key not in _scrub(f"{before}{key}{after}{key}", key)


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


def sse_frames(text):
    """The (event name, parsed data) of each frame, requiring the exact two-line frame format."""
    frames = []
    for raw in text.split("\n\n")[:-1]:
        name_line, data_line = raw.split("\n")
        assert name_line.startswith("event: ") and data_line.startswith("data: ")
        frames.append((name_line[7:], json.loads(data_line[6:])))
    assert text.endswith("\n\n")
    return frames


def trace(kind):
    return TraceEvent(stage="plan", kind=kind, data={"n": 1}, elapsed=0.5)


def test_the_stream_sends_each_trace_event_in_order_then_the_answer(client_for, fakes):
    async def script(emit):
        emit(trace("from_the_loop"))
        await asyncio.to_thread(emit, trace("from_a_thread"))

    fakes.script = script
    with client_for(GOOD_ENV) as client:
        response = client.post("/ask/stream", json={"question": "q"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    frames = sse_frames(response.text)
    assert [name for name, _ in frames] == ["trace", "trace", "answer"]
    assert [data["kind"] for _, data in frames[:2]] == ["from_the_loop", "from_a_thread"]
    assert set(frames[0][1]) == {"stage", "kind", "data", "elapsed"}
    assert frames[-1][1] == FAKE_RESPONSE.model_dump(mode="json")


def test_a_pipeline_error_in_the_stream_is_a_last_error_frame_with_the_stage_and_no_key(client_for, fakes):
    async def script(emit):
        emit(trace("before_the_failure"))

    fakes.script = script
    fakes.pipeline_error = PipelineError("review", f"rejected key {KEY}")
    with client_for(GOOD_ENV) as client:
        response = client.post("/ask/stream", json={"question": "q"})
    assert response.status_code == 200
    frames = sse_frames(response.text)
    assert [name for name, _ in frames] == ["trace", "error"]
    assert frames[-1][1] == {"error": "pipeline", "stage": "review", "detail": "review: rejected key [key removed]"}
    assert KEY not in response.text


def test_any_other_exception_in_the_stream_is_an_internal_error_frame_with_no_key(client_for, fakes):
    fakes.pipeline_error = ValueError(f"bad {KEY}")
    with client_for(GOOD_ENV) as client:
        response = client.post("/ask/stream", json={"question": "q"})
    assert sse_frames(response.text) == [("error", {"error": "internal", "detail": "ValueError: bad [key removed]"})]
    assert KEY not in response.text


def test_the_stream_is_503_for_a_config_error_and_for_a_failed_index_build(client_for, fakes):
    with client_for(BAD_ENV) as client:
        config = client.post("/ask/stream", json={"question": "q"})
    assert config.status_code == 503
    assert config.json()["error"] == "configuration"
    assert {p["variable"] for p in config.json()["config_problems"]} == set(GOOD_ENV)
    fakes.fail_first = 8  # the startup build and the rebuild this request starts
    with client_for(GOOD_ENV) as client:
        wait_for_index(client, "failed")
        index = client.post("/ask/stream", json={"question": "q"})
    assert index.status_code == 503
    assert index.json()["error"] == "index" and "embedding call failed" in index.json()["detail"]
    assert KEY not in index.text


@pytest.mark.parametrize("body", [{}, {"question": ""}, {"question": 5}, {"q": "x"}])
def test_the_stream_rejects_a_malformed_body_with_422(client_for, body):
    with client_for(GOOD_ENV) as client:
        assert client.post("/ask/stream", json=body).status_code == 422


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


def test_the_page_names_every_corpus_medicine_and_offers_the_four_public_questions():
    root = STATIC_DIR.parents[2]
    page = (STATIC_DIR / "index.html").read_text()
    medicines = {path.stem.split("-", 1)[1] for path in (root / "corpus").glob("*-*.md")}
    questions = json.loads((root / "evals" / "questions.json").read_text())["questions"]
    public = [q["question"] for q in questions if q["id"].startswith("P")]
    assert (len(medicines), len(public)) == (10, 4)
    for text in (*medicines, *public):
        assert text in page, text


def test_the_page_script_never_parses_text_as_html():
    script = (STATIC_DIR / "app.js").read_text()
    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "DOMParser", "eval("):
        assert sink not in script, sink
