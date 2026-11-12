from dataclasses import dataclass

from pydantic_ai.models import Model

from pharmag.config import Settings


@dataclass(frozen=True)
class RoleModels:
    """One chat model per role. All four share the key and the base URL (DEC-011, DEC-025)."""

    planner: Model
    worker: Model
    writer: Model
    critic: Model


def build_models(settings: Settings) -> RoleModels:
    raise NotImplementedError
