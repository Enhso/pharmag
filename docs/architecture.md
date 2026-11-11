# Architecture of the core

Status: approved by the owner on 2026-11-11 with the rulings DEC-021 to DEC-026 in the [decision log](decisions.md). The design applies the earlier rulings DEC-005 to DEC-015. The corpus parser, the index, and the tools come first. The agents follow after a check-in with the owner (DEC-028).

## Request flow

One question passes through these stages. Stages 1, 2, 3, 5, and 7 are LLM calls. Stages 4 and 8 are plain code.

1. **Plan.** The planner returns a typed `Plan`: whether the question is in scope, and a list of sub-questions, each with the drugs it concerns.
2. **Research.** One worker per sub-question, up to six at the same time. Each worker runs its own tool-calling loop over the four tools, with at most ten tool calls, and returns typed `Findings`: statements, each with a verbatim quote and the ID of the chunk the quote comes from.
3. **Write.** The writer returns a typed `Draft`: the answer as prose, and a numbered list of claims. The prose cites each claim with its marker, such as `[3]`. Each claim carries its citations (chunk ID and quote) and a kind: a fact from one passage, or a synthesis across passages.
4. **Quote check.** Code confirms that each quote occurs in the chunk it cites. A claim with a failed quote is marked unsupported with no LLM involved.
5. **Review.** The critic sees the prose, the claims, and the cited chunks. It returns a verdict per claim: supported, unsupported, or ambiguous, with a reason, and a follow-up query for each unsupported claim. It also reports any statement in the prose that carries no marker, and such a statement counts as an unsupported claim.
6. **Retry, at most once.** New workers research the follow-up queries. The writer revises the draft. Stages 4 and 5 run again, and their verdicts are final.
7. **Redact, only if needed.** If a claim is still unsupported, the writer rewrites the prose without it. This is the last LLM call.
8. **Respond.** Code confirms that every marker in the prose points to a surviving claim. It lists the source files, reports the removed claims and the cautions under `critic`, attaches the trace, and appends the disclaimer.

An out-of-scope question skips stages 2 to 7 and gets a short refusal with the disclaimer, as a 200 (DEC-012).

## Data shapes

| Type | Fields | Made by |
|---|---|---|
| `Chunk` | `id` (file name plus line range), `file`, `drug`, `source`, `section` (canonical key), `heading_path`, `line_start`, `line_end`, `text` | Corpus parser, at startup |
| `Plan` | `in_scope`, `reason`, `sub_questions` (each with `text` and `drugs`) | Planner |
| `Findings` | `sub_question`, `findings` (each with `statement`, `chunk_id`, `quote`), `not_found` | Worker |
| `Draft` | `answer` (prose with markers), `claims` (each with `text`, `kind`, `citations`) | Writer |
| `Verdict` | per claim: `status`, `reason`, `follow_up`. Plus the unmarked statements found in the prose | Quote check, then critic |
| `TraceEvent` | `stage`, `kind`, `data`, elapsed time | Every stage |
| `AskResponse` | `answer`, `sources`, `citations`, `plan`, `tool_calls`, `critic`, `disclaimer`, `timings`, `usage` | Stage 8 |

## Modules

| File | Owns |
|---|---|
| `config.py` (exists) | Settings and the strict config check |
| `api.py` (exists) | Routes: `/health`, `/ask`, `/ask/stream`, and the static page |
| `models.py` (started) | The types above |
| `corpus.py` | Files to chunks: heading tree, flattened tables, the three label formats, canonical section keys |
| `index.py` | Embeddings in a NumPy array, BM25, rank fusion, metadata filters |
| `tools.py` | `search_corpus`, `get_section`, `find_interactions`, `lookup_glossary`, as plain functions over the corpus and the index |
| `agents.py` | The four PydanticAI agents (planner, worker, writer, critic) and their prompts |
| `grounding.py` | The quote check and the marker check |
| `pipeline.py` | The stages, the retry, the limits, and the trace |

## Where the brief's five steps land

| Brief step | Place in the design | Proof in the response |
|---|---|---|
| Plan | Stage 1 | `plan` |
| Retrieve by in-memory similarity | `index.py`, reached through `search_corpus` | `tool_calls` with chunk IDs and scores |
| At least two tools, chosen by the agent | Each worker picks among four tools. No code path fixes the order | `tool_calls` differ by question |
| Critic before the final answer | Stages 4 to 7 | `critic` |
| Cited answer with a disclaimer | Stage 8 | `answer`, `sources`, `citations`, `disclaimer` |

## Startup, limits, and measurements

- The server starts at once and builds the index in the background. `/health` returns 200 and reports `building`, `ready`, or `failed`. `/ask` waits for the index (DEC-024).
- Each role's model comes from `PHARMAG_PLANNER_MODEL`, `PHARMAG_WORKER_MODEL`, `PHARMAG_WRITER_MODEL`, or `PHARMAG_CRITIC_MODEL`. An unset name means `OPENAI_MODEL` (DEC-025). All roles share one key and one base URL.
- Starting limits are six workers at once, ten tool calls per worker, and one retry round (DEC-026). The eval script's measured latency and cost decide the final numbers.
- The smoke test on 2026-11-11 measured single calls at 1 to 5 seconds for small prompts, and one embedding request of 256 passages at 8.5 seconds. These are single measurements.
- Each LLM call records input tokens, cached input tokens, and output tokens, and the log warns when the cache hit rate drops.
- The streaming endpoint sends each `TraceEvent` as it happens and ends with the full `AskResponse`.

## Chunk size, from the corpus

A heading-tree split gives 456 leaf sections with a median of 514 characters. Seventeen sections exceed 4,000 characters, and the largest has 16,952. The largest pipe table is one block of 4,806 characters. The parser therefore caps a chunk at 5,000 characters and splits a longer section between paragraph blocks, which keeps every table in the corpus whole. A single line longer than the cap stays whole.

## Rulings on the sketch

| Point | Ruling | Log entry |
|---|---|---|
| How the answer text is built | Free prose from the writer, with numbered claim markers | DEC-021 |
| A claim still unsupported after the retry | Removed from the answer and reported under `critic`. Ambiguous claims stay with a caution | DEC-022 |
| How a claim is removed from prose | One redaction call by the writer, then a marker check in code. The critic also reports unmarked statements | DEC-023 |
| When the index is built | In the background, after the server starts | DEC-024 |
| Names of the role overrides | `PHARMAG_` prefix | DEC-025 |
| Starting limits | Six workers, ten tool calls each, one retry | DEC-026 |
