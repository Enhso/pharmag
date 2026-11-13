import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pharmag.config import Settings, load_settings
from pharmag.pipeline import DISCLAIMER, Engine, PipelineError, answer, build_engine

_log = logging.getLogger("pharmag")  # its own handler: the root logger would also print the HTTP client's request lines
_log.setLevel(logging.INFO)
_log.addHandler(logging.StreamHandler())

STATIC_DIR = Path(__file__).parent / "static"
CORPUS_DIR = Path("corpus")
# Seconds to wait after the 1st, 2nd and 3rd failed attempt (the embeddings come from a remote API).
RETRY_PAUSES = (1, 2, 4)


def _scrub(text: str, api_key: str) -> str:
    return text.replace(api_key, "[key removed]")


class IndexUnavailable(Exception):
    pass


class EngineBuild:
    """Builds the engine in a background task and hands it to requests."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.state = "building"
        self.error: str | None = None
        self._task: asyncio.Task[Engine | None] | None = None

    def start(self) -> None:
        self.state, self.error = "building", None
        self._task = asyncio.create_task(self._build())

    async def _build(self) -> Engine | None:
        for pause in (*RETRY_PAUSES, None):
            try:
                engine = await build_engine(self.settings, CORPUS_DIR)
            except Exception as exc:
                if pause is None:
                    self.state = "failed"
                    self.error = _scrub(f"{type(exc).__name__}: {exc}", self.settings.api_key)
                    return None
                await asyncio.sleep(pause)
            else:
                self.state = "ready"
                return engine

    async def engine(self) -> Engine:
        if self.state == "failed":
            self.start()
        # shield: a client that disconnects must not cancel the build for everyone else.
        built = await asyncio.shield(self._task)
        if built is None:
            raise IndexUnavailable(self.error)
        return built

    async def stop(self) -> None:
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = load_settings(os.environ)
    app.state.build = None
    if isinstance(app.state.config, Settings):
        app.state.build = EngineBuild(app.state.config)
        app.state.build.start()
    yield
    if app.state.build:
        await app.state.build.stop()


app = FastAPI(title="pharmag", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class Question(BaseModel):
    question: str = Field(min_length=1)


def _problems() -> list[dict[str, str]]:
    return [asdict(p) for p in app.state.config]


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    if not isinstance(app.state.config, Settings):
        return {"status": "degraded", "config_problems": _problems()}
    build = app.state.build
    body = {"status": "ok", "index": build.state}
    if build.state == "failed":
        body["index_error"] = build.error
    return body


@app.post("/ask")
async def ask(body: Question):
    config = app.state.config
    if not isinstance(config, Settings):
        return JSONResponse(
            {"error": "configuration", "config_problems": _problems()}, status_code=503
        )
    try:
        engine = await app.state.build.engine()
    except IndexUnavailable as exc:
        return JSONResponse({"error": "index", "detail": str(exc)}, status_code=503)
    try:
        return await answer(body.question, engine)
    except PipelineError as exc:
        return JSONResponse(
            {"error": "pipeline", "stage": exc.stage, "detail": _scrub(str(exc), config.api_key)},
            status_code=502,
        )


def _frame(name: str, data: str) -> str:
    return f"event: {name}\ndata: {data}\n\n"


@app.post("/ask/stream")
async def ask_stream(body: Question):
    """Same checks as /ask, then server-sent events: trace*, then one answer or one error."""
    config = app.state.config
    if not isinstance(config, Settings):
        return JSONResponse(
            {"error": "configuration", "config_problems": _problems()}, status_code=503
        )
    try:
        engine = await app.state.build.engine()
    except IndexUnavailable as exc:
        return JSONResponse({"error": "index", "detail": str(exc)}, status_code=503)

    async def frames():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        # emit can run in a worker thread (the synchronous research tools).
        task = asyncio.create_task(
            answer(body.question, engine, lambda e: loop.call_soon_threadsafe(queue.put_nowait, e))
        )
        task.add_done_callback(lambda _: queue.put_nowait(None))  # queued after every event emitted before the end
        try:
            while (event := await queue.get()) is not None:
                yield _frame("trace", event.model_dump_json())
            try:
                yield _frame("answer", task.result().model_dump_json())
            except PipelineError as exc:
                error = {"error": "pipeline", "stage": exc.stage, "detail": _scrub(str(exc), config.api_key)}
                yield _frame("error", json.dumps(error))
            except Exception as exc:
                detail = _scrub(f"{type(exc).__name__}: {exc}", config.api_key)
                yield _frame("error", json.dumps({"error": "internal", "detail": detail}))
        finally:
            task.cancel()  # a client that disconnects stops the model spend; the shielded engine build is not this task

    return StreamingResponse(
        frames(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
