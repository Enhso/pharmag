import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pharmag.config import Settings, load_settings

STATIC_DIR = Path(__file__).parent / "static"
DISCLAIMER = (
    "This is general information from a small set of documents, not medical advice. "
    "Ask a doctor or pharmacist about your own treatment."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = load_settings(os.environ)
    yield


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
    if isinstance(app.state.config, Settings):
        return {"status": "ok"}
    return {"status": "degraded", "config_problems": _problems()}


@app.post("/ask")
def ask(body: Question):
    if not isinstance(app.state.config, Settings):
        return JSONResponse(
            {"error": "configuration", "config_problems": _problems()}, status_code=503
        )
    return {
        "answer": "Placeholder answer: the research agent is not built yet, "
        "so this reply was not written from the documents.",
        "sources": [],
        "disclaimer": DISCLAIMER,
    }
