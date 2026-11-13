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

## 2026-11-12, property-review preservation

### DEC-030. Preserve property review for follow-up

- **Decision.** Preserve the prior property-review findings in `tests/PROPERTIES_findings.md` and point to that authoritative detailed review from `docs/handoff.md`, so the next agent can pick up the follow-up.
- **Source.** The owner's request: "Saved these findings in `tests/PROPERTIES_findings.md` file so we can address them (and update the handoff to make sure the next agent picks it up)."
- **Scope.** Approval to record and hand off only. This does not approve the property contracts, authorize implementation of the recommendations, or settle unresolved contract questions. Those still require owner confirmation.

## 2026-11-12, second working session

### DEC-031. A working proof of concept this session

- **Decision.** The session ends with a container that already meets the brief end to end, pushed to `main`, as the fallback submission. This is the go-ahead for the agents step that DEC-028 asked for. The owner also asked for a visual overview of the project for the presentation, to be made once the proof of concept works.
- **Owner's words.** "i want to have a working poc at the end of this session which would be the lowest possible deliverable, in case things go awry tomorrow."
- **Assistant's reading, open to the owner's veto.** The proof of concept is the approved pipeline of `docs/architecture.md` with every stage, a plain page, a short README, and an `.env.example`. The answer eval with DeepEval, the streaming endpoint, the design pass, and the property-review follow-ups wait for the next session.
- **Assistant's choices, open to the owner's veto.**
  - The `answer` text ends with three blocks that code builds: the cautions, a numbered source list that maps each marker to its file, section, and lines, and the disclaimer. A grader who reads only `answer` then sees the exact file names and the disclaimer.
  - A corpus file counts as a source only when a claim that cites it is still in the final prose.
  - A citation must point to a passage that a tool returned during the same request.
  - When the redacted prose still carries a marker of a removed claim, code drops the sentence that carries it and reports `marker_check: repaired`.
  - A stage that fails gives HTTP 502 with the stage name. A failed index build gives 503, and the next question starts the build again.
  - The worker's typed output has no `sub_question` field. Code pairs each result with its sub-question.

## 2026-11-13, third working session (readiness)

The session started with checks on the pushed proof of concept: a clean clone, a secret scan, a re-read of the 33 saved answers, and a live trace of 15 answers. The owner then ruled on one sheet with the words "ok, go ahead", which accepts every recommendation on it.

### DEC-032. The assistant's earlier choices stand

- **Decision.** The owner accepts the choices that earlier entries left open to a veto.
  - The six choices of DEC-031: the code-built end of `answer`, a file counting as a source only while a claim that cites it survives, citations limited to passages a tool returned in the request, the dropped sentence with `marker_check: repaired`, HTTP 502 for a failed stage and 503 for a failed index build, and code pairing each worker result with its sub-question.
  - Python 3.15, `bm25s`, `httpx2` as a test-only dependency, and 503 from `/ask` on a config error.
  - `docs/handoff.md` stays tracked and public (DEC-029).
  - The built-in `artifact-diagramming` skill is listed in the manifest without a copy, because no license permits one.
  - The disclaimer's wording as it is in `pipeline.py`.
- **Reason.** The owner accepted the recommendation. The reason offered with it: each choice was checked on the running container, and none conflicts with an earlier ruling.

### DEC-033. Quote check on whole words, and five more fixes

- **Decision.** The quote check compares whole words and whole numbers in order, and ignores punctuation, Markdown marks, and letter case. It has no minimum length. This settles the open question on how strict the check is. Five more fixes go in with it: a worker gets a failing quote back inside its own call, the critic sees each passage's section heading, the writer's prompt rules out remarks on what a document lacks or how it is organized, a failed second review or a failed redaction call ships the draft in hand, and the token usage lines reach the container log.
- **Rejected.** A minimum number of words per quote.
- **Reason.** The owner accepted the recommendation. The reason offered with it, from the live trace: four of six failing quotes had every word right and failed on a final period or on the corpus's Markdown escapes, which removed both warfarin claims from one answer to P3. Real list items are two words long, so a minimum length would remove correct claims. The retry rounds whose cause was recorded came from these artifacts, not from a wrong medical statement.

### DEC-034. Open items closed

- **Decision.**
  - The cleaned session transcript is not committed. An ignore rule keeps it out of the repo.
  - The presentation overview stays a private page, with no copy in the repo.
  - The expected answers of the eleven eval questions are confirmed, with one edit: the fourth key fact of P2 no longer reads as a complete list. A verifier agent found 33 of the 35 key facts stated in the gold lines, and the other two true but loosely worded.
  - The property catalogue in `tests/PROPERTIES.md` is confirmed as listed. The follow-ups F01 to F16 are deferred: they are gaps in test strength, not product defects.
  - The limits stay at six workers and ten tool calls (DEC-026). The most seen was eight calls by one worker. The time cap is set from a run after the fixes.
  - A marker written as a range, and a redactor that renumbers markers, stay documented limits. No saved answer shows either.
  - No reranker and no fifth tool (DEC-009, DEC-010). Nothing measured asks for one.
- **Reason.** The owner accepted the recommendations.

### DEC-035. Scope of the rest of this session

- **Decision.** The fixes are verified with one run of the eleven questions, not two. The session then prepares the handoff for a design session later the same morning.
- **Owner's words.** "one run and then set the stage for the design polish we'll do later in the morning (in another session). we don't have a lot of usage to spend so be careful not to go overboard on non-essential things."

### DEC-036. Cleaned session transcripts are published

- **Decision.** The cleaned transcripts of the working sessions go into `ai-config/transcripts/`, and the ignore rule for that folder is removed. An agent cleans the transcript of the second session the way the first was cleaned, and nothing that should stay private is published. This replaces the transcript item of DEC-034.
- **Owner's words.** "nothing that should stay private should be published", and "transparency is really important to me."
- **Rejected.** Keeping the transcripts out of the repo, which was the recommendation accepted an hour earlier in DEC-034.
- **No second check.** The owner told the assistant to take the cleaning agent's result as it is, to save usage: "trust the agent's work (blindly)." The main session ran no independent check of the cleaned files. The commit still ran the standing scan of the staged diff for the env values.
