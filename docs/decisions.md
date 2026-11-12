# Decision log

This file records each decision the owner makes, on the day the owner makes it. The options behind each ruling are in the [scoping document](scoping.md). An entry quotes the owner's own reason when the owner gave one. Where the owner accepted a recommendation without comment, the entry gives the reason that came with the recommendation and says so. Where the owner ruled against the recommendation without comment, the entry says that too.

## 2026-11-11, working setup

### DEC-001. Working agreement

- **Decision.** The assistant confirms each assumption with the owner before it acts on the assumption. The project uses the most performant, current tools that fit the assignment's constraints. Every owner decision is logged in this file, and a private defense brief grows with the project. Every skill and MCP server the assistant uses is copied into the repo. The main session plans, and subagents do the mechanical work. Scope and decisions come before code and before architecture.
- **Source.** The owner's kickoff message.

### DEC-002. Document visibility

- **Decision.** `docs/scoping.md` and `docs/decisions.md` are public. Both stay free of the proxy hostname, key details, and the brief's own text. `defense-brief.md` sits at the repo root and is gitignored. The assignment PDF is gitignored.
- **Options considered.** Public docs with a private brief (chosen). Only the decision log public. Everything private until submission.
- **Reason.** The owner accepted the recommendation. The reason offered with it: the brief is marked confidential, and reviewers gain from a visible decision trail.

### DEC-003. Layout of the AI configuration

- **Decision.** Used skills and MCP servers are copied verbatim into an inert `ai-config/` folder, with a manifest in `ai-config/README.md`.
- **Options considered.** The inert folder (chosen). A live `.claude/` layout with a root `.mcp.json`.
- **Reason.** The owner accepted the recommendation. The reason offered with it: Claude Code does not load `ai-config/`, so the copies cannot shadow the owner's installed plugins.

### DEC-004. Scope of the AI configuration

- **Decision.** Beyond used skills and MCP servers, the repo publishes the `builder` and `verifier` agent definitions, the model routing file, a manifest of the plugins and hooks active in the sessions, a new `CLAUDE.md` at the repo root, and copies of the owner's two personal CLAUDE.md files with the owner's name and home paths removed.
- **Owner's words.** "Project-level CLAUDE.md + anonymize the others." A follow-up question confirmed the reading above.

### Fact the owner confirmed

The provided `.env` file is exactly as Syntax sent it. This fact feeds risk R1 and DEC-014.

## 2026-11-11, rulings on the scoping decisions

Decision IDs D1 to D12 refer to the scoping document.

### DEC-005. Framework (D1): PydanticAI 2.x

- **Rejected.** LangGraph 1.x, a hand-written loop on the OpenAI SDK, the OpenAI Agents SDK.
- **Reason.** The owner accepted the recommendation. The reason offered with it: typed inputs and outputs, a small dependency tree, and LLM calls that a debugger can step through.

### DEC-006. Agent shape (D2): parallel workers

- **Decision.** One call returns a typed plan. Each sub-question runs in its own tool-calling loop at the same time. One call merges the results. The critic then judges the draft.
- **Rejected.** The same stages run as one sequential loop, which was the recommendation. One loop that writes its plan as text.
- **Reason.** The owner gave none. The owner accepts the costs the scoping document lists: more tokens, concurrency to reason about, and a trace per worker.

### DEC-007. Critic (D3): bounded cycle

- **Decision.** The critic returns a verdict per claim with the evidence it checked. An unsupported claim sends the agent back once. After that round, the answer ships with the remaining flags shown. Before the LLM critic runs, code checks each claim's quote against the chunk it cites.
- **Rejected.** Linear with repair in code. Linear, flag only. Loop until the critic passes.
- **Reason.** The owner accepted the recommendation. The reason offered with it: the critic can close a gap and not only report it, and the round limit caps latency.

### DEC-008. Chunking (D4): heading-tree chunks

- **Decision.** Chunks follow the heading tree and carry a metadata header. Fixed-size windows with overlap stay in the eval harness as the measured baseline.
- **Rejected.** LLM-written context per chunk, embedding-similarity chunking, late chunking.
- **Reason.** The owner accepted the recommendation. The reason offered with it: the split matches how the labels are written, costs no LLM calls, and is deterministic.

### DEC-009. Retrieval (D5, D5a, D5b): hybrid exact search

- **Decision.** Dense vectors compared with a NumPy matrix product, in-memory BM25, reciprocal rank fusion, and metadata filters. No reranker at first, to be revisited when the evals show ranking errors. Embeddings are computed at container start through the API.
- **Rejected.** Dense only. An approximate index library. An embedded vector database. A committed embedding cache. A local embedding model.
- **Reason.** The owner accepted the recommendations. The reason offered with them: exact tokens need BM25, paraphrase needs dense vectors, and several hundred chunks need no approximate index.

### DEC-010. Tools (D6): four tools to start

- **Decision.** `search_corpus`, `get_section`, `find_interactions`, and `lookup_glossary`. `resolve_reference` and `list_documents` join if the evals show the need. No numeric helper.
- **Reason.** The owner accepted the recommendation. The reason offered with it: each tool answers a question shape that similarity search handles badly.

### DEC-011. Models (D7): per-role overrides

- **Decision.** Each role reads an optional model override that defaults to `OPENAI_MODEL`. Calls use the Chat Completions API.
- **Rejected.** One model for every role with no overrides, which was the recommendation. Hardcoded model names.
- **Reason.** The owner gave none.
- **Note.** The owner's message gave this ruling as "option 2" in the D7 position without the label. The assistant stated that reading back to the owner.

### DEC-012. Response contract (D8): rich JSON

- **Decision.** `/ask` returns `answer`, `sources`, `citations`, `plan`, `tool_calls`, `critic`, `disclaimer`, timings, and token counts. `/ask` stays plain JSON, and a second streaming endpoint feeds the UI. A time cap per request is set after measurement. A malformed body gets a standard 4xx code, and every well-formed question gets 200, refusals included. Code appends the disclaimer.
- **Rejected.** Minimal JSON with `answer` only.
- **Reason.** The owner accepted the recommendation. The reason offered with it: extra fields cost nothing, and the UI and the presentation use the trace.

### DEC-013. Frontend (D9): static page

- **Decision.** Static HTML, CSS, and JavaScript served by the API at `/`, with every asset vendored. The `impeccable` skill handles the design pass.
- **Rejected.** HTMX fragments. Gradio, Streamlit, or Chainlit. React with a Vite build.
- **Reason.** The owner accepted the recommendation. The reason offered with it: no build stage, no Node, and nothing fetched at runtime.

### DEC-014. Config check (D10): fully strict, server stays up

- **Decision.** The app requires `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, and `OPENAI_EMBEDDING_MODEL`. A missing, empty, quoted, or misspelled variable is a config error. The server still starts. `/health` returns 200, and `/ask` returns an error that names the field. The assistant corrects the local `.env` so that it passes the check.
- **Owner's words.** "Correct the current `.env`. Fully strict, stay up."
- **Rejected.** Normalize the values and then validate, which was the recommendation. Strict with an exit at startup.
- **Risk the owner accepted.** If the graders' env file carries the same defects as the file Syntax sent, every `/ask` call fails with the config error.
- **Defaults confirmed.** `uv` with exact `==` pins and a committed lock file. The newest CPython release for which every pinned dependency ships amd64 and arm64 wheels. FastAPI on uvicorn at `0.0.0.0:8000`. A slim, pinned, multi-stage image with a non-root user and a `.dockerignore`.

### DEC-015. Evaluation harness (D11): eval set plus DeepEval

- **Decision.** An eval set in the repo and one script that runs it against the live API. DeepEval supplies the metrics as a development-only dependency that stays out of the image.
- **Rejected.** The eval set with no metrics library, which was the recommendation. Ragas. Four `curl` calls.
- **Reason.** The owner gave none for adding a library. On the choice of library, the owner accepted the recommendation. The reason offered with it: agent metrics such as tool correctness, pytest-style runs, and a judge class that can reuse the app's own client.

### DEC-016. Repository host (D12): GitHub

- **Decision.** The repo stays on GitHub. No GitLab project.
- **Owner's words.** "i work with github, don't want to go through the hassle of opening a new account and setting things up."

### DEC-017. Extra evaluation questions: all seven

- **Decision.** Candidates C1 to C7 join the eval set. The assistant read the files afterwards and confirmed the expected sources of C3 and C5.

### DEC-018. No questions to Syntax

- **Decision.** The owner does not email the recruitment contact. The project works on three assumptions. The graders read every field of the response. No time limit applies to a request, and the project measures the time cost of its runs if time permits. The config check follows DEC-014.
- **Owner's words.** "sending an email looks good but it introduces a hurdle. i don't have a lot of time to complete this, so we'll make some assumptions."

### DEC-019. Order of work

- **Decision.** The assistant commits the docs and config, smoke-tests the proxy, and has a subagent build the walking skeleton. The assistant then shows the owner a one-page architecture sketch of the core before any core code.
- **Rejected.** An architecture sketch with no code first. An unattended run to the end.

### DEC-020. Git policy

- **Decision.** The assistant commits and pushes after each verified step. The first push publishes `ai-config/` as it stood on 2026-11-11. Commit messages carry no co-author lines and end with the session link line that the harness requests.
- **Rejected.** Local commits with a push on the owner's word, which was the recommendation. No commits by the assistant.

## 2026-11-11, rulings on the architecture sketch

Point numbers refer to the draft of `docs/architecture.md` that the owner reviewed. With these rulings the owner approved the sketch, which opens the core build (DEC-019).

### DEC-021. Answer text: free prose from the writer

- **Decision.** The writer model writes the answer as prose. The prose cites claims with numbered markers, and a claim list with quotes travels beside it.
- **Rejected.** An answer that code renders from the checked claims, which was the recommendation.
- **Reason.** The owner gave none. The cost the sketch named: a sentence can appear in the prose that no check saw. DEC-023 answers that cost.

### DEC-022. Claims still unsupported after the retry: remove and report

- **Decision.** A claim that is still unsupported after the retry round leaves the answer and is listed under `critic` in the response and the UI. An ambiguous claim stays in the answer with a visible caution.
- **Rejected.** Keeping the unsupported claim in the answer with a flag.
- **Reason.** The owner accepted the recommendation. The reason offered with it: the user never receives a claim the system knows is unsupported.

### DEC-023. How a claim is removed from free prose

- **Decision.** The writer gets one last call to rewrite the answer without the rejected claims. Code then confirms that every marker left in the prose points to a surviving claim. The critic also reads the prose and reports any statement that carries no marker.
- **Rejected.** Code that deletes each sentence carrying the rejected claim's marker.
- **Reason.** The owner accepted the recommendation. The reason offered with it: a deleted sentence can leave the surrounding prose reading oddly, and the marker check keeps the removal verifiable.

### DEC-024. Index build: in the background

- **Decision.** The server starts at once and builds the index in the background. `/health` returns 200 and reports `building`, `ready`, or `failed`. `/ask` waits for the index.
- **Rejected.** Blocking startup until the index exists.
- **Reason.** The owner accepted the recommendation. The reason offered with it: `/health` answers from the first second.

### DEC-025. Names of the role overrides

- **Decision.** `PHARMAG_PLANNER_MODEL`, `PHARMAG_WORKER_MODEL`, `PHARMAG_WRITER_MODEL`, and `PHARMAG_CRITIC_MODEL`. An unset name means `OPENAI_MODEL`.
- **Rejected.** The same names without the prefix, which was the recommendation.
- **Reason.** The owner gave none. The reason offered with the chosen option: a prefixed name cannot collide with another variable in the graders' environment.

### DEC-026. Starting limits

- **Decision.** Six workers at once, ten tool calls per worker, one retry round. The measured latency and cost from the eval script decide the final numbers.
- **Rejected.** Four workers and six tool calls, which was the recommendation. Three workers and four tool calls.
- **Reason.** The owner gave none.

### DEC-027. The four public questions are tracked verbatim

- **Decision.** The eval file holds the four public questions word for word. This is an exception to DEC-002 for those four sentences only.
- **Rejected.** A gitignored file with the verbatim text.
- **Reason.** The owner accepted the recommendation. The reason offered with it: reviewers type these questions into the UI anyway.

### DEC-028. Next stretch of work

- **Decision.** The assistant builds the eval set, the corpus parser, retrieval, and the tools, and checks in with the owner before the agents.
- **Rejected.** Building through a working `/ask` before the check-in. Writing only the eval set.

### Point 5 of the sketch needed no new ruling

DEC-012 already gives every well-formed question a 200, refusals included. An out-of-scope question gets a short refusal with the disclaimer.

## 2026-11-12, session handoff

### DEC-029. Wrap up and hand off

- **Decision.** The session finishes the work already in flight and then writes a handoff document with enough context for the next session to start well.
- **Owner's words.** "this conversation is getting too long so try and wrap up what has already started before writing a handoff doc with enough context for the next session to start on a good basis."
- **Assistant's choice, open to the owner's veto.** The handoff is `docs/handoff.md`, tracked and public like the other docs, and `CLAUDE.md` points to it.
