# Architecture of the core

Status: approved by the owner on 2026-11-11 with the rulings DEC-021 to DEC-026 in the [decision log](decisions.md). The design applies the earlier rulings DEC-005 to DEC-015. The corpus parser, the index, and the tools came first. The agents, the grounding checks, and the pipeline were built on 2026-11-12, after the owner's go-ahead (DEC-031). The streaming endpoint is not built yet.

## Request flow

One question passes through these stages. Stages 1, 2, 3, 5, and 7 are LLM calls. Stages 4 and 8 are plain code.

1. **Plan.** The planner returns a typed `Plan`: whether the question is in scope, and a list of sub-questions, each with the drugs it concerns.
2. **Research.** One worker per sub-question, up to six at the same time. Each worker runs its own tool-calling loop over the four tools, with at most ten tool calls, and returns typed `Findings`: statements, each with a verbatim quote and the ID of the chunk the quote comes from.
3. **Write.** The writer returns a typed `Draft`: the answer as prose, and a numbered list of claims. The prose cites each claim with its marker, such as `[3]`. Each claim carries its citations (chunk ID and quote) and a kind: a fact from one passage, or a synthesis across passages. A draft whose prose uses a marker with no claim goes back to the writer inside the same call.
4. **Quote check.** Code confirms that each quote occurs in the chunk it cites, and that a tool returned that chunk during this request. The comparison splits both texts into whole words, whole numbers (with their decimal or thousands separators), and comparison signs, and the quote must be a contiguous run of the chunk's tokens; case, spacing, punctuation, and Markdown marks do not matter, but "5 mg" does not match "0.5 mg". A claim with a failed quote is marked unsupported with no LLM involved. A worker whose finding fails the same check is sent back to the worker inside the same call.
5. **Review.** The critic sees the prose, the claims, and the cited chunks, each with its section heading path. It returns a verdict per claim: supported, unsupported, or ambiguous, with a reason, and a follow-up query for each unsupported claim. It also reports any statement in the prose that carries no marker, and such a statement counts as an unsupported claim.
6. **Retry, at most once.** New workers research the follow-up queries. The writer revises the draft. Stages 4 and 5 run again, and their verdicts are final. When the retry round itself fails, including the second review, the first draft goes on to stage 7 with its verdicts.
7. **Redact, only if needed.** If a claim is still unsupported, the writer rewrites the prose without it. This is the last LLM call. Code does not trust the result: a sentence of the draft that carried the marker of an unsupported claim, or a statement the critic found with no marker, is removed when it is still in the prose word for word. When the redaction call fails, stage 8 does that removal on the draft's own prose and reports `repaired`.
8. **Respond.** Code confirms that every marker in the prose points to a surviving claim. As a last resort it drops a sentence that still carries a marker of a removed claim, and reports `marker_check: repaired`. It lists the source files, which are the files cited by the claims left in the prose. It reports the removed claims and the cautions under `critic`. The trace is the `plan`, `tool_calls`, `timings`, and `usage` fields. To the prose it appends the cautions, a numbered source list (marker, file, section, lines), and the disclaimer, so a reader of `answer` alone sees the exact file names.

An out-of-scope question skips stages 2 to 7 and gets a short refusal with the disclaimer, as a 200 (DEC-012).

## Data shapes

| Type | Fields | Made by |
|---|---|---|
| `Chunk` | `id` (file name plus line range), `file`, `drug`, `source`, `section` (canonical key), `heading_path`, `line_start`, `line_end`, `text` | Corpus parser, at startup |
| `Plan` | `in_scope`, `reason`, `sub_questions` (each with `text` and `drugs`) | Planner |
| `Findings` | `findings` (each with `statement`, `chunk_id`, `quote`), `not_found`. Code pairs each result with its sub-question | Worker |
| `Draft` | `answer` (prose with markers), `claims` (each with `text`, `kind`, `citations`) | Writer |
| `Verdict` | per claim: `status`, `reason`, `follow_up`. Plus the unmarked statements found in the prose | Quote check, then critic |
| `TraceEvent` | `stage`, `kind`, `data`, elapsed time | Every stage |
| `AskResponse` | `answer`, `sources`, `citations`, `plan`, `tool_calls`, `critic`, `disclaimer`, `timings`, `usage` | Stage 8 |

## Modules

| File | Owns |
|---|---|
| `config.py` | Settings, the strict config check, and the four role overrides |
| `api.py` | Routes: `/health`, `/ask`, `/ask/stream`, and the static page. It builds the engine in the background |
| `models.py` | The types above |
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
- A live build of the index took 10.3 seconds for the 451 chunks (one run, four parallel batches of 128).
- The first retrieval eval is in `evals/results/retrieval.json`. With the raw question as the query, 12 of 13 gold passages are in the top six for the heading-tree chunks, against 9 of 13 for 1,000-character windows. The file lists the caveats. In no mode does the search find the warfarin table row that names ibuprofen, which is the case `find_interactions` covers.
- Each LLM call records input tokens, cached input tokens, and output tokens, and the log warns when the cache hit rate drops.
- `POST /ask/stream` sends each `TraceEvent` as a server-sent event while the pipeline runs, and ends with the full `AskResponse` or with an error that names the stage. Beside `started` and `finished` for each stage and `tool_call` for each tool call, the pipeline emits `planned` (scope, reason, sub-questions), `drafted` (the claim count of each draft), and `reviewed` (verdict counts after each review). Tools that run in worker threads hand their events to the event loop, and a client that disconnects cancels the run. The page reads this stream; `/ask` is unchanged.
- A request in which every worker fails gives HTTP 502 at the research stage. A failed index build gives 503, and the next question starts the build again.

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
