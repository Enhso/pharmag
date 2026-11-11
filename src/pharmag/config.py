from collections.abc import Mapping
from dataclasses import dataclass, field
from difflib import get_close_matches

API_KEY = "OPENAI_API_KEY"
BASE_URL = "OPENAI_BASE_URL"
MODEL = "OPENAI_MODEL"
EMBEDDING_MODEL = "OPENAI_EMBEDDING_MODEL"
REQUIRED = (API_KEY, BASE_URL, MODEL, EMBEDDING_MODEL)
QUOTES = "'\""


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    base_url: str
    model: str
    embedding_model: str


@dataclass(frozen=True)
class ConfigProblem:
    variable: str
    problem: str


def _near_miss(name: str, environ: Mapping[str, str]) -> str:
    others = [k for k in environ if k.startswith("OPENAI_") and k not in REQUIRED]
    close = get_close_matches(name, others, n=1, cutoff=0.8)
    return f"; the environment has {close[0]}, which looks like a misspelling" if close else ""


def _problem_with(name: str, environ: Mapping[str, str]) -> str | None:
    value = environ.get(name)
    if value is None:
        return "is not set" + _near_miss(name, environ)
    if value == "":
        return "is empty"
    if value != value.strip():
        return "has leading or trailing whitespace"
    if value[0] in QUOTES or value[-1] in QUOTES:
        return "starts or ends with a quote character"
    if name == BASE_URL and not value.startswith(("http://", "https://")):
        return "must start with http:// or https://"
    return None


def load_settings(environ: Mapping[str, str]) -> Settings | list[ConfigProblem]:
    problems = []
    for name in REQUIRED:
        text = _problem_with(name, environ)
        if text:
            problems.append(ConfigProblem(name, text))
    if problems:
        return problems
    return Settings(
        api_key=environ[API_KEY],
        base_url=environ[BASE_URL],
        model=environ[MODEL],
        embedding_model=environ[EMBEDDING_MODEL],
    )
