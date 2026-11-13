# pharmag

Pharmacology Hybrid Agent for Retrieval & Multi-hop Analysis.

pharmag answers pharmacology questions from the 21 Markdown files in `corpus/` (DailyMed labels, MedlinePlus pages and a glossary). Every claim in an answer carries a quote from a named file, section and line range, and a critic step checks each claim against its quote before the answer goes out. It is a small FastAPI service with a plain web page.

## Build and run

```
docker build -t agent . && docker run -p 8000:8000 --env-file .env agent
```

Copy `.env.example` to `.env` first and fill it in (see Environment variables). Then open <http://localhost:8000/> or call the API.

The server starts at once and builds the search index in the background, which takes a short while because the embeddings come from a remote API. `/health` reports the progress, and `/ask` waits for the index.

```
curl -s localhost:8000/health
# {"status":"ok","index":"ready"}   ("index" is "building", "ready" or "failed")

curl -s -X POST localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "Can I take ibuprofen while on warfarin?"}'
```

An answer can take a minute or more.

`/health` always answers 200. If the configuration is defective it answers `{"status": "degraded", "config_problems": [...]}`, and `/ask` answers 503 with the same list. Other errors from `/ask`: 503 `{"error": "index", "detail": ...}` when the index could not be built (the next request tries again), 502 `{"error": "pipeline", "stage": ..., "detail": ...}` when a stage failed, and 422 for a body without a non-empty `question`.

### Response of `POST /ask`

| Field | Content |
|---|---|
| `answer` | The prose with `[n]` markers, then any cautions, a numbered source list, and the disclaimer |
| `sources` | The corpus files cited by the claims that remain in the answer |
| `citations` | Per claim: marker, claim text, file, section, line range, and the verbatim quote |
| `plan` | Whether the question is in scope, why, and the sub-questions with their drugs |
| `tool_calls` | Per tool call: the sub-question, the tool, its arguments, the chunk IDs it returned, a note |
| `critic` | Review rounds, verdicts, removed claims, cautions, unmarked statements, marker check |
| `disclaimer` | The not-medical-advice sentence |
| `timings` | Seconds per stage, plus `total` |
| `usage` | Request and token counts, in total and per role |

## Environment variables

Set these four. The server stays up without them but every `/ask` call fails with a message that names the variable.

| Variable | Meaning |
|---|---|
| `OPENAI_API_KEY` | API key |
| `OPENAI_BASE_URL` | Base URL of the OpenAI-compatible API, starting with `http://` or `https://` |
| `OPENAI_MODEL` | Chat model name |
| `OPENAI_EMBEDDING_MODEL` | Embedding model name |

Optional overrides give one role its own model. A role without an override uses `OPENAI_MODEL`.

| Variable | Role |
|---|---|
| `PHARMAG_PLANNER_MODEL` | Planner |
| `PHARMAG_WORKER_MODEL` | Research workers |
| `PHARMAG_WRITER_MODEL` | Writer |
| `PHARMAG_CRITIC_MODEL` | Critic |

Write values without quotes. `docker run --env-file` passes quote characters through as part of the value, and the config check rejects a value that is empty, has leading or trailing whitespace, or starts or ends with a quote. A variable that is set is checked even when it is optional.

## How it works

1. Plan. The planner decides whether the question is in scope and splits it into sub-questions.
2. Research. One worker per sub-question searches the corpus with four tools and returns findings with verbatim quotes.
3. Write. The writer drafts the answer and a numbered list of claims with citations.
4. Quote check. Code confirms each quote occurs in the passage it cites.
5. Review. The critic rates each claim supported, unsupported or ambiguous and lists statements without a marker.
6. Retry. At most once, new workers look for the missing evidence and the writer revises.
7. Redact. A claim that is still unsupported is removed from the prose.
8. Respond. Code checks every marker, lists the sources, and appends the cautions and the disclaimer.

The full design is in `docs/architecture.md`.

## Tests

```
uv run --locked pytest -q
```

The tests need no network and no `.env`.

## Repository map

| Path | Content |
|---|---|
| `corpus/` | The 21 source documents |
| `src/pharmag/api.py` | HTTP routes and the background index build |
| `src/pharmag/config.py` | Environment check |
| `src/pharmag/pipeline.py`, `agents.py`, `tools.py`, `index.py`, `corpus.py`, `models.py` | The eight stages, the role models, the corpus tools, the search index, the corpus parser, and the shared types |
| `src/pharmag/static/` | The web page |
| `tests/` | Tests; `tests/PROPERTIES.md` lists what each property test checks |
| `evals/` | The eval questions, the retrieval evaluation, and `live_check.py`, which asks the questions against a running server |
| `docs/` | Architecture, scoping and decision log |

## AI coding configuration

The configuration and the skills used to build this repo are copied into `ai-config/`; see `ai-config/README.md`.
