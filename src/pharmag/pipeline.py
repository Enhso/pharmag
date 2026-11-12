from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from pharmag.agents import RoleModels
from pharmag.config import Settings
from pharmag.models import AskResponse, Chunk, Stage, TraceEvent
from pharmag.tools import Tools

DISCLAIMER = (
    "This is general information from a small set of documents, not medical advice. "
    "Ask a doctor or pharmacist about your own treatment."
)
# Starting limits (DEC-026). The eval's measured latency and cost decide the final numbers.
MAX_WORKERS = 6
MAX_TOOL_CALLS = 10
MAX_RETRY_ROUNDS = 1

Emit = Callable[[TraceEvent], None]


@dataclass(frozen=True)
class Engine:
    """Everything a request needs, built once at startup."""

    tools: Tools
    chunks: Mapping[str, Chunk]  # by chunk ID
    models: RoleModels


class PipelineError(Exception):
    """A stage failed and no answer can be given. `stage` names where."""

    def __init__(self, stage: Stage, message: str) -> None:
        super().__init__(f"{stage}: {message}")
        self.stage = stage


async def build_engine(settings: Settings, corpus_dir: Path) -> Engine:
    """Parse the corpus, embed every chunk through the API, and build the role models."""
    raise NotImplementedError


async def answer(question: str, engine: Engine, emit: Emit | None = None) -> AskResponse:
    """Run stages 1 to 8 of docs/architecture.md for one question. Raises PipelineError."""
    raise NotImplementedError
