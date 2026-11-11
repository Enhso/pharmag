# Scoping: pharmacology research agent

Status: ruled by the owner on 2026-11-11. The [decision log](decisions.md) holds each ruling with its entry number. The option tables below stay as written before the rulings, so the rejected alternatives remain on record.

## What the brief asks for

Build a Python agent that answers compound pharmacology questions from the 21 files in `corpus/`. For each question the agent plans, retrieves passages by in-memory similarity, picks among at least two local tools, runs a critic, and returns a cited answer with a not-medical-advice disclaimer. The agent ships as one Docker container with `GET /health`, `POST /ask`, and a small frontend.

The work window is November 11 to 13, 2026. The deadline is November 13 at 23:59 Casablanca time. That is 22:59 UTC if Morocco is on UTC+1 that day (inferred, to confirm). The brief estimates one focused day for 90% of the work.

## Evidence labels

Each claim in this document carries one of four labels.

- **Read** means the brief states the claim or the corpus shows it. Page numbers refer to the brief.
- **Verified** means a command ran and the result was observed.
- **Inferred** means the claim follows from read or verified facts.
- **Unknown** means only Syntax or a test can settle the claim.

## Hard constraints

All rows are read from the brief. The last column names the check that proves the row.

| ID | Constraint | Page | Proof |
|---|---|---|---|
| H1 | Python 3.11 or later | 2 | Base image tag in the Dockerfile |
| H2 | Dependencies pinned in `pyproject.toml` or `requirements.txt` | 2 | Exact `==` versions, plus a lock file |
| H3 | Plan. The agent splits the question into sub-questions or steps | 2 | The plan appears in the response trace |
| H4 | Retrieve. Passages come from in-memory similarity search | 2 | The index lives in process memory, with no database service |
| H5 | Tools. At least two local tools, chosen by the agent and not by fixed code | 2 | The trace shows different tool calls for different questions |
| H6 | Review. A critic checks grounding and flags unsupported or clinically ambiguous claims before the final answer | 2 | A test plants an unsupported claim and the critic flags it |
| H7 | Answer. The response cites the source files used and states that it is not medical advice | 2 | Response fields and the UI |
| H8 | A Dockerfile at the repo root. The documented build and run commands start the API. The container is self-contained | 2 | Run the exact commands on a clean checkout |
| H9 | The graders run the container with their own environment values | 2, 5 | Config comes from the environment only |
| H10 | `GET /health` returns 200 | 2 | `curl` |
| H11 | `POST /ask` with a JSON body that holds `question` returns 200 | 3 | `curl` |
| H12 | A minimal frontend calls `POST /ask` and shows the answer | 3 | Open the page and ask a question |
| H13 | A public Git repository | 3 | Open the link in a private browser window |
| H14 | Email the repo link and a short summary before the deadline. The graders assess the last commit pushed before it | 5 | Push time on the remote |
| H15 | The AI coding configuration (skills, MCP config) is in the repo | 4 | `ai-config/` |
| H16 | The candidate can explain any file and any design decision | 4 | The decision log and the interview |
| H17 | A 10-minute presentation on the problem, the tools and why, the architecture, and the main challenges | 3 | Rehearsal against a timer |
| H18 | The demo works, with setup that needs no help | 5 | A second machine or a clean clone |

### What the constraints imply

These rows are inferred. Each one narrows a design choice below.

| ID | Consequence | Follows from |
|---|---|---|
| I1 | The API process serves the frontend on port 8000, because the run command publishes only that port | H8, H12 |
| I2 | The corpus is inside the image, because the run command mounts no volume | H8 |
| I3 | `docker build` has no credentials, because the env file arrives only at `docker run`. Embeddings from the API cannot be computed at build time | H8, H9 |
| I4 | At grading, only the OpenAI-style variables exist. A design that needs another provider's key fails | H9 |
| I5 | Model names can change at grading. No model name is hardcoded, and no feature depends on one model without a fallback | H9 |
| I6 | Hidden questions are graded against expected source files, so the response names corpus files exactly | Page 4 |

### Soft preferences

- GitLab is preferred over other hosts (p. 3).
- The framework is free: LangChain, LangGraph, PydanticAI, or a hand-written loop (p. 2).
- The frontend technology is free, and extras are welcome (p. 3).
- Any LLM provider is allowed during development (p. 2). I4 limits what can ship.
- The graders assess code quality and user experience (p. 2). The criteria are technical competence, innovation and creativity, and problem-solving (p. 3).

### Gaps in the brief

| ID | Gap | Label |
|---|---|---|
| A1 | Page 2 promises five evaluation questions. Page 4 lists four and says hidden ones exist | Read |
| A2 | The fourth question stops mid-sentence after the word "threshold" | Read |
| A3 | The brief does not say whether retrieval counts as one of the two tools | Unknown |
| A4 | The response body of `/ask` has no specified fields | Unknown |
| A5 | No time limit per request is stated | Unknown |
| A6 | The brief does not say whether a correct answer loses points for citing an extra file | Unknown |
| A7 | The provided env file and the brief's code sample disagree on a variable name (see R1) | Verified |

The owner chose not to put these gaps to Syntax (DEC-018). The project assumes that the graders read every field of the response and that no time limit applies to a request.

## Corpus facts that drive the design

- The corpus has 21 Markdown files, 460 KB, and about 68,000 words. Ten are DailyMed labels, ten are MedlinePlus monographs, and one is a glossary (verified with `wc`). At four characters per token that is about 115,000 tokens (estimate).
- The files hold 520 headings across five levels (verified with `grep`), so a heading-based split yields several hundred chunks.
- The DailyMed labels come in three formats (read).

| Format | Files | Example heading | Effect |
|---|---|---|---|
| Numbered prescribing information | warfarin, apixaban, metformin, sertraline, amoxicillin, atorvastatin | `## 4 CONTRAINDICATIONS`, `### 5.3 Increased Risk of Bleeding` | Section numbers are stable keys |
| Older unnumbered label | albuterol, ibuprofen | `## CONTRAINDICATIONS`, `## WARNINGS` | Same topics, no numbers |
| Over-the-counter Drug Facts | acetaminophen, aspirin | `## Uses`, `## Directions`, `## Warnings` | About 2 KB each. There is no contraindications heading. The closest text sits under "Do not use" |

- MedlinePlus files use question headings such as "What special precautions should I follow?" (read).
- Tables are flattened into pipe-separated lines with no Markdown table syntax. Nine lines exceed 1,500 characters, and the longest has 4,734 (verified with `awk`).
- `dailymed-atorvastatin.md` line 223 is a table footnote that starts with `#`, so a naive parser reads it as a second top-level heading (read).
- Numbered labels often use the brand or salt name. The contraindications section of the apixaban label says "ELIQUIS" and never "apixaban" (read). A chunk needs its drug name attached from file metadata.
- Numbered labels cross-reference their own sections, for example "see Warnings and Precautions (5.1)" (read).
- The extraction left artifacts: "m 2" for a superscript, "B 12Deficiency", "haveliver disease" (read).
- The DailyMed aspirin file describes an effervescent product with heartburn indications, which suggests a combination product and not plain aspirin (inferred).
- The proxy reports a context window above 900,000 tokens for the configured chat model (verified by a read-only metadata query). Chunk size is therefore a question of retrieval precision and citation detail, not of context limits.

## Evaluation questions

The four public questions are paraphrased here. Expected sources come from page 4. The location column was checked by reading the files.

| ID | Question | Shape | Expected sources | Where the answer is | What makes it hard |
|---|---|---|---|---|---|
| P1 | Main contraindications of warfarin | Single-document lookup | `dailymed-warfarin.md` | Section 4, lines 127 to 146 | A long list. One nested bullet is flattened into a single line. The answer must be complete |
| P2 | Contraindications of warfarin and apixaban, shared and unique | Two-document comparison | `dailymed-warfarin.md`, `dailymed-apixaban.md` | Warfarin section 4. Apixaban section 4, lines 108 to 114 | Apixaban lists two items. Calling an item "shared" means equating two different wordings, which is a clinical judgment the critic must flag |
| P3 | Bleeding risk and monitoring when a patient on warfarin starts sertraline | Multi-hop interaction | `dailymed-warfarin.md`, `dailymed-sertraline.md` | Warfarin sections 7.3 and 2.4. Sertraline sections 5.3 and 7.1 | The warfarin label names sertraline only inside a flattened table row under its drug class |
| P4 | Whether metformin is contraindicated at an eGFR of 25, and the threshold | Single-document numeric check | `dailymed-metformin.md` | Sections 4, 2.3, and 8.6 | The label's unit includes body surface area and the question's unit does not. The question text is cut off |

### Candidate extra questions

These candidates cover the corners that the public questions miss. The owner adopted all seven (DEC-017). Expected sources marked "to verify" need a read of the file first.

| ID | Question shape | Expected sources | What it tests |
|---|---|---|---|
| C1 | Contraindications of a drug that has no file (rivaroxaban appears only in the glossary) | None | The agent says the corpus lacks the drug and invents no source |
| C2 | Daily limit and liver warning for acetaminophen | `dailymed-acetaminophen.md` | The Drug Facts format |
| C3 | Ibuprofen for a patient on warfarin | `dailymed-warfarin.md`, `dailymed-ibuprofen.md` (to verify) | The older label format and a drug-class hop |
| C4 | Sertraline together with an MAOI, and the washout period | `dailymed-sertraline.md` | A contraindication stated by drug class |
| C5 | Aspirin for a child with flu symptoms | `dailymed-aspirin.md`, `medlineplus-aspirin.md` (to verify) | A consumer monograph as a needed source |
| C6 | "Should I stop my warfarin before dental work?" | `dailymed-warfarin.md` | Label facts with no personal instruction |
| C7 | An off-topic question, or a question that carries instructions for the model | None | Scope rules |

## Decisions

The owner ruled on every decision on 2026-11-11. This table gives each ruling. The sections after it list the options in the order they were ranked before the rulings, with the owner's stated leaning where one existed.

| ID | Ruling | Same as the recommendation | Log entry |
|---|---|---|---|
| D1 | PydanticAI 2.x | Yes | DEC-005 |
| D2 | Parallel workers | No. The recommendation was the sequential loop | DEC-006 |
| D3 | Bounded cycle with one retry round, plus the quote check in code | Yes | DEC-007 |
| D4 | Heading-tree chunks, with fixed-size windows as the measured baseline | Yes | DEC-008 |
| D5 | Hybrid exact search. No reranker at first. Embeddings computed at container start | Yes | DEC-009 |
| D6 | Four tools to start, and more if the evals show the need | Yes | DEC-010 |
| D7 | Per-role model overrides that default to `OPENAI_MODEL` | No. The recommendation was one model with no overrides | DEC-011 |
| D8 | Rich JSON, with the four related rulings as recommended | Yes | DEC-012 |
| D9 | Static page served at `/` | Yes | DEC-013 |
| D10 | Fully strict config check that keeps the server up. Defaults confirmed | No. The recommendation was to normalize the values first | DEC-014 |
| D11 | Eval set and script, with DeepEval for metrics | No. The recommendation was no metrics library | DEC-015 |
| D12 | GitHub | No. The recommendation was GitLab | DEC-016 |

### D1. Orchestration framework

The owner's leaning is a framework whose data flow stays visible.

| Rank | Option | For | Against |
|---|---|---|---|
| 1 | PydanticAI 2.x | Typed inputs and outputs for each agent, validated tool arguments, and a small dependency tree. Each LLM call is one visible function call that a debugger can step through. Its eval library can serve D11 | Fewer reviewers know it than LangGraph. The 2.x API is newer than most coding assistants' training data, so the build starts from current docs |
| 2 | LangGraph 1.x | State and edges are explicit objects. A critic cycle is one conditional edge. The graph exports as a diagram for the presentation. The brief names it, so reviewers know it | It brings the LangChain core packages, which put more layers between the code and the HTTP request |
| 3 | A hand-written loop on the OpenAI SDK | Nothing hidden, the fewest dependencies, and every line is explainable | The brief's objective asks for framework skills. The loop must re-implement retries, output validation, and streaming |
| 4 | OpenAI Agents SDK | Built-in handoffs, guardrails, and tracing | It defaults to the Responses API and to trace upload. Both need overrides behind a LiteLLM proxy, and neither is tested here |

Recommendation: PydanticAI 2.x. LangGraph takes first place if reviewer familiarity and a generated graph diagram matter more to the owner than typed data flow.

### D2. Agent shape

| Rank | Option | For | Against |
|---|---|---|---|
| 1 | A typed plan, then a tool-calling loop, then a critic. One call returns the plan as data. The loop works through the plan and picks its own tools. The critic judges the draft | The response and the UI can show the plan as an object. Tool choice stays with the model. Each stage has one job and one test | At least three LLM calls per question |
| 2 | Parallel workers. Option 1, but each sub-question runs in its own tool loop at the same time, and one call merges the results | Lower latency on multi-drug questions | More tokens, concurrency to reason about, and a trace that is harder to read |
| 3 | One loop that first writes its plan as text | The fewest calls and the least code | The plan is prose inside a transcript, which is hard to show and hard to test |

Recommendation: option 1. Move to option 2 only if measured latency on multi-drug questions requires it.

### D3. Critic topology

The owner's question is linear or cyclic.

| Rank | Option | For | Against |
|---|---|---|---|
| 1 | Bounded cycle. The critic returns a verdict per claim (supported, unsupported, or ambiguous) with the evidence it checked. An unsupported claim sends the agent back once, to retrieve more or to drop the claim. After the round limit, the answer ships with the remaining flags shown | The critic can close a gap and not only report it. The round limit caps latency | One more loop to bound and test. Worst-case latency about doubles |
| 2 | Linear with repair in code. One critic pass. Code removes or marks the claims the critic rejects | Predictable latency and no loop | A claim is cut even when its evidence exists in the corpus but was not retrieved |
| 3 | Linear, flag only. One critic pass that annotates the answer | The least code. It meets the brief's wording | The user receives claims the system knows are unsupported |
| 4 | Loop until the critic passes | The cleanest final answer when it ends | Unbounded latency and cost. The loop can oscillate |

Recommendation: option 1 with one retry round.

One addition applies under every option. Before the LLM critic runs, code checks each claim's quote against the chunk it cites and rejects a quote that does not occur there. This check makes part of "grounded" a property that a test can assert.

### D4. Chunking and indexing

The owner's leaning is no naive fixed-size chunking.

| Rank | Option | For | Against |
|---|---|---|---|
| 1 | Heading-tree chunks. Split on the heading tree. A leaf section is one chunk. A flattened table stays whole, or splits on row boundaries with its header row repeated. Each chunk stores drug, source, canonical section, heading path, and line range. The embedded text starts with a header line built from that metadata | Matches how the labels are written. A citation can name file, section, and lines. The header line fixes the brand-name problem. No LLM cost at index time. Deterministic | Needs a parser for three label formats and their artifacts |
| 2 | Option 1 plus LLM-written context per chunk (contextual retrieval) | May help chunks whose headings say little | Hundreds of extra LLM calls at startup, or a committed cache to maintain. Not deterministic. The heading path already carries most of that context in this corpus |
| 3 | Embedding-similarity ("semantic") chunking | Needs no format knowledge | Discards the structure the authors supplied. Extra embedding calls. Boundaries are hard to explain |
| 4 | Late chunking | Strong on long documents in published results | Needs token-level embeddings, which a hosted embedding endpoint does not return. A local model enlarges the image and ignores the embedding model the graders configure |
| 5 | Fixed-size windows with overlap | The least code | Splits tables and lists, and loses the section identity |

Recommendation: option 1. Keep option 5 as the measured baseline in D11, so the gain is a number and not a claim.

### D5. In-memory retrieval

The owner's leaning is in-memory search with no database.

| Rank | Option | For | Against |
|---|---|---|---|
| 1 | Hybrid exact search. Dense vectors from the configured embedding model, compared with one NumPy matrix product. In-memory BM25 beside it. Reciprocal rank fusion merges the two lists. Metadata filters narrow by drug, source, and section | BM25 catches exact tokens such as drug names, INR, eGFR, and CYP3A4. Dense search catches paraphrase. With several hundred chunks, a full scan is one small matrix product, so an approximate index would add error and no speed | Two indexes and a fusion step to explain |
| 2 | Dense only, exact | The least code | Weak on rare exact tokens |
| 3 | An approximate index library (FAISS, hnswlib, usearch) | Standard at large scale | Built for millions of vectors. Adds a native dependency and approximation with no gain at this size |
| 4 | An embedded vector database in memory mode (Chroma, LanceDB, Qdrant local) | Familiar API | Contradicts the owner's leaning and hides the similarity code that the brief asks for |

Recommendation: option 1.

Two sub-decisions follow.

- **D5a, reranking.** Ranked options: none until the eval shows ranking errors, then the hosted reranker that the proxy lists, used when the call succeeds and skipped when it fails. An LLM rerank with the chat model costs more tokens and time. A local cross-encoder enlarges the image.
- **D5b, when to embed.** Ranked options: embed at container start through the API, which always matches the configured embedding model. Second, a committed cache keyed by embedding model name and chunk hash, with misses embedded at start. Third, a local embedding model. Move from the first to the second only if measured start time is a problem.

### D6. Tool set

The owner's leaning is no toy tools. Each candidate answers a question shape that similarity search handles badly.

| Tool | What it does | Corpus fact behind it |
|---|---|---|
| `search_corpus(query, drug?, source?, section?)` | Hybrid search with optional filters | The agent decides when to search and for what |
| `get_section(drug, section)` | Returns one whole canonical section, such as contraindications, from any of the three label formats | P1 and P2 need complete lists. A top-k search can drop list items |
| `find_interactions(drug_a, drug_b)` | Returns every passage in A's files that names B, B's brand, or B's drug class, and the reverse | The warfarin label names sertraline only in a table row under its class |
| `resolve_reference(drug, section_number)` | Follows a label's own reference to another section | Numbered labels cross-reference their sections often |
| `lookup_glossary(term)` | Returns a definition and the class members from `GLOSSARY.md` | Gives the agent the class hop (sertraline is an SSRI) and expands abbreviations |
| `list_documents()` | Lists the drugs, sources, and sections in the corpus | Lets the agent say that a drug has no file |
| Numeric helper | Compares a patient value with a threshold | P4. A weak candidate, because the model compares 25 with 30 unaided. This is the toy-tool pattern |

Ranked sets:

1. `search_corpus`, `get_section`, `find_interactions`, and `lookup_glossary`.
2. Set 1 plus `resolve_reference` and `list_documents`.
3. `search_corpus` and `lookup_glossary`. This set meets the count only if retrieval counts as a tool (gap A3).

Recommendation: set 1, and grow to set 2 if the evals show the need. Leave the numeric helper out.

### D7. Model strategy

| Rank | Option | For | Against |
|---|---|---|---|
| 1 | One chat model for every role, read from `OPENAI_MODEL`, through the Chat Completions API that the brief's sample uses | Works with any value the graders inject | The writer and the critic share blind spots |
| 2 | Optional per-role overrides that default to `OPENAI_MODEL` | A demo can show a critic from another model family. Grading still works | More config, and a path the graders never exercise |
| 3 | Hardcoded model names | None under I5 | Breaks when the graders' key or model differs |

Recommendation: option 1. Option 2 is a stretch item.

### D8. Response contract of `/ask`

The brief fixes the request body and the 200 status only (gap A4).

| Rank | Option | For | Against |
|---|---|---|---|
| 1 | Rich JSON. `answer` as Markdown with inline file citations. `sources` as exact corpus file names. `citations` with claim, file, section, and quote. `plan`, `tool_calls`, `critic`, `disclaimer`, timings, and token counts | A grading script most likely reads `answer` or searches for file names, and extra fields cost nothing. The UI and the presentation use the trace | A larger payload and a schema to maintain |
| 2 | Minimal JSON with `answer` only | The smallest contract | Fails a grader that reads a `sources` field |

Recommendation: option 1.

Four related rulings:

- **Streaming.** Recommended: `/ask` stays plain JSON, and a second streaming endpoint feeds the UI.
- **Time cap.** Recommended: set a cap per request after the smoke test measures one call's latency.
- **Errors.** Recommended: standard 4xx codes for a malformed body, and 200 for every well-formed question, refusals included.
- **Disclaimer.** Recommended: code appends the disclaimer, so its presence never depends on the model.

### D9. Frontend

The owner's leaning is a single port, no build step, and a design pass with the `impeccable` skill. I1 already forces the single port.

| Rank | Option | For | Against |
|---|---|---|---|
| 1 | Static HTML, CSS, and JavaScript served by the API at `/`. No framework, or one small vendored ES module. The page shows the answer, the sources with the cited passage, the plan, the tool calls, and the critic's flags | No build stage, no Node, and nothing fetched at runtime. Full control for the design pass | Hand-written DOM code |
| 2 | HTMX with server-rendered fragments | The logic stays in Python | Templates plus a vendored library. Streaming needs an extension |
| 3 | Gradio, Streamlit, or Chainlit | The fastest route to a working chat | A generic look and heavy dependencies. Streamlit needs its own port |
| 4 | React with a Vite build in a Docker stage | The widest component choice | Contradicts the no-build leaning and adds Node to the build |

Recommendation: option 1. Vendor every asset, because a CDN link fails on a restricted network.

### D10. Runtime, packaging, and config tolerance

One ruling and four defaults to confirm.

- **Config tolerance (ruling).** The provided env file fails under the documented run command (R1). Option 1 tolerates the file. The app strips one pair of surrounding quotes from each `OPENAI_*` value, reads the base URL from `OPENAI_BASE_URL` first and from the misspelled name second, and logs which name it used. Option 2 is strict and fails at startup with a clear message. Recommendation: option 1, plus a question to Syntax. A follow-up question added a third option, strict with the server kept up, and the owner chose it.
- **Packaging.** `uv` with exact `==` pins in `pyproject.toml` and a committed `uv.lock`. The exact pins meet the brief's wording, and the lock file pins transitive dependencies.
- **Python.** The newest CPython release for which every pinned dependency ships amd64 and arm64 wheels, checked at build time.
- **Server.** FastAPI on uvicorn, bound to `0.0.0.0:8000`.
- **Image.** A slim base image with a pinned tag, a multi-stage build, a non-root user, and a `.dockerignore` that excludes the env file, `.git`, the brief, and the private notes.

### D11. Evaluation harness

| Rank | Option | For | Against |
|---|---|---|---|
| 1 | An eval set in the repo. The four public questions plus the adopted extras, each with expected source files and key facts. One script runs them against the live API and reports source recall and precision, key-fact coverage, critic flags, latency, and tokens. The same script compares chunking strategies | Produces numbers for the presentation and catches regressions | Costs build time and proxy budget |
| 2 | Option 1 plus a metrics library such as Ragas or DeepEval | Metric names that reviewers may know | Another dependency and more judge calls |
| 3 | Four `curl` calls | Minutes of work | No evidence for any design claim |

Recommendation: option 1, on the framework's eval library if D1 picks PydanticAI.

### D12. Repository host

The current remote is on GitHub, and the brief prefers GitLab. Ranked options: GitLab as the submitted repo with GitHub kept as a second push URL, GitLab only, GitHub only. Recommendation: one of the first two, because the preference is stated and the move takes minutes.

### Stretch items

These items wait until the core passes its evals: the tools exposed through an MCP endpoint on the same port, a critic from another model family, LLM-written chunk context, and parallel workers.

## Risks not in the owner's list

| ID | Risk | Evidence | Proposed handling |
|---|---|---|---|
| R1 | The provided env file breaks the documented run command. Docker passes the quote characters through as part of each value, and the base-URL variable name lacks its last letter. A default OpenAI client then has no base URL and a quoted key | Verified in a throwaway container. The owner confirms that the file is as Syntax sent it | DEC-014. The check is strict and the server stays up. The local file is corrected |
| R2 | The graders' environment can differ in model names, key, and variable names | Read (p. 2, p. 5). Details unknown | I4 and I5. A startup check with a clear error |
| R3 | The chat model runs on a hosted backend with its own content filter, which may reject text on self-harm or overdose. The sertraline label opens with a boxed warning on suicidality | Backend read from proxy metadata. Filter behavior untested | Smoke-test that passage. Treat a filtered response as a reported error |
| R4 | Latency. A reasoning model inside a plan, a tool loop, and a critic cycle can take long per question | Inferred. The graders' timeout is unknown | Round limits, and a time cap set after measurement (DEC-012, DEC-018) |
| R5 | Reasoning models reject some request parameters, such as a custom temperature | Inferred from the model family. Untested on this proxy | Send minimal parameters. Smoke test |
| R6 | The key's budget and rate limits are unknown | The proxy declined the key-info query (verified) | Cache LLM and embedding responses during development |
| R7 | Overfitting to four public questions. Hidden questions probably reach the other label formats, the consumer monographs, drug classes, and drugs with no file | Inferred from the corpus and the glossary | The candidate extra questions |
| R8 | Citation grading. A file name that is not exact, or an extra file cited out of habit, may cost points | Read (p. 4). The grading method is unknown | `sources` lists exact file names, and only for passages that support a claim |
| R9 | One model writes and criticizes, so errors correlate | Follows from I4 | The quote check in code. The critic sees claims and evidence only |
| R10 | Confidential material in a public repo: the brief, the env file, the proxy address | Read (the brief's footer) | Ignore rules for git and Docker. Tracked docs paraphrase |
| R11 | The repo holds third-party skill files, and the brief holds the candidate accountable for every line | 87 files under `ai-config/skills/` (`find ai-config/skills -type f \| wc -l`) | The manifest states origin and license for each item |
| R12 | A reviewer may build on Apple Silicon | Unknown | Dependencies with arm64 wheels only |
| R13 | Startup depends on the proxy if embeddings are computed at start | Follows from I3 | Retries with backoff. `/health` reports ready only when the index exists |
| R14 | Questions that ask for personal medical direction, or that carry instructions for the model | Inferred | Scope rules and candidates C6 and C7 |
| R15 | Framework APIs changed after the coding assistant's training data | Web search shows a stable PydanticAI 2.x line and LangGraph 1.1.x. The exact latest versions are unverified | Read current docs before coding |
| R16 | The graders assess the last commit pushed before the deadline | Read (p. 5) | Keep the default branch runnable from the first skeleton, and push after each verified step |
| R17 | P2 and P4 each allow two readings (wording equivalence, units) | Read in the corpus | The critic flags the reading, and the answer states it |

## Work order after the rulings

The owner's three tasks are closed. The owner ruled on every decision, chose not to email Syntax (DEC-018), and keeps the repo on GitHub (DEC-016).

Each remaining step names its check.

1. Commit and push the repo hygiene: ignore rules, `ai-config/`, and these docs. Check: `git status` lists no brief, no env file, and no private notes.
2. Smoke-test the proxy with one chat call that uses a tool and a typed output, one embedding call, and one call that carries the sertraline boxed warning. Check: status, latency, and token counts recorded for each call.
3. Build the skeleton: the Dockerfile, `/health`, a stub `/ask`, a static page at `/`, and the config check. Check: the documented build and run commands return 200 from both endpoints and render the page, and a defective env file makes `/ask` name the bad field. Push.
4. Show the owner a one-page architecture sketch of the core. Check: the owner approves the sketch before any core code (DEC-019).
5. Write the eval set file with the four public questions and C1 to C7. Check: the owner confirms each expected answer.
6. Build in this order, with one check each: the corpus parser and chunks, retrieval, the tools, the agent loop, the critic, the UI, and the polish.
