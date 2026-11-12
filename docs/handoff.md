# Handoff

Originally written on 2026-11-12 at the end of the first working session. Updated on 2026-11-12 with the property-review results and their preservation for follow-up (DEC-030). The review and its preservation are not owner approval of the property contracts or fixes, or a new architecture decision. Rewrite this file before the next session stops.

The deadline is 2026-11-13 at 23:59 Casablanca time, which is 22:59 UTC if Morocco is on UTC+1 that day. The graders assess the last commit pushed before it.

## Read these first

| File | Why |
|---|---|
| `CLAUDE.md` | The working agreement. The owner decides, and every ruling is logged |
| `docs/decisions.md` | The authority on what is decided, DEC-001 to DEC-030. Do not reopen a ruling |
| `docs/architecture.md` | The approved design of the core: request flow, data shapes, modules, limits |
| `docs/scoping.md` | The brief's constraints H1 to H18, their consequences I1 to I6, and the risks |
| [`tests/PROPERTIES_findings.md`](../tests/PROPERTIES_findings.md) | Authoritative detailed property review: F01–F16, with 7 HIGH and 9 MEDIUM finding groups. Read before proposing property changes |
| `defense-brief.md` | Private and gitignored. Evidence E1 to E13, proxy details, and the defense of each ruling. Add to it with every decision and measurement |
| `ai-config/README.md` | Manifest of skills, MCP servers, agents, and plugins. Add a row when a session first uses a skill or an MCP server, and copy the skill into `ai-config/skills/` |

## What exists on main

Everything below is merged, pushed, and covered by 67 passing tests (`uv run --locked pytest -q`).

- **Skeleton.** `config.py` (strict config check), `api.py` (`/health`, a placeholder `/ask`, the static page), `Dockerfile`, `.dockerignore`. Verified with the graders' exact commands on 2026-11-11.
- **Corpus parser.** `corpus.py` cuts the 21 files into 451 chunks on the heading tree, with a cap of 5,000 characters.
- **Search index.** `index.py` holds embeddings in a NumPy array and BM25 through `bm25s`, and fuses the two rankings.
- **Tools.** `tools.py` has `search_corpus`, `get_section`, `find_interactions`, and `lookup_glossary` as plain functions. Brand names and class terms come from the corpus.
- **Retrieval eval.** `evals/retrieval_eval.py` and its result in `evals/results/retrieval.json`.
- **Eval questions.** `evals/questions.json`, 11 questions with expected sources, gold line ranges, and key facts.

Not built yet: `agents.py`, `grounding.py`, `pipeline.py`, the real `/ask`, `/ask/stream`, the index build at startup, the UI beyond a question box, the answer eval with DeepEval, the README, and an `.env.example`.

## What waits on the owner

Raise these at the start of the next session. The first three block work.

1. **Check-in before the agents (DEC-028).** Show the retrieval numbers below and get the go-ahead for the agents step.
2. **Expected answers.** `evals/questions.json` still says "Draft". The owner confirms each expected answer, or corrects it.
3. **Properties.** `tests/PROPERTIES.md` lists 47 properties in six sections. The owner's rule is to confirm each one. On 2026-11-12 the owner requested evaluation of all 47 entries, not approval. [`tests/PROPERTIES_findings.md`](../tests/PROPERTIES_findings.md) is the authoritative detailed review. DEC-030 approves preserving it and this handoff pointer only. Its proposed improvements and unresolved contract choices await owner confirmation; the catalogue, tests, and production code are unchanged.
4. **Choices the assistant made that the owner can veto.** Python 3.15. `bm25s` for BM25. `httpx2` as the test client dependency. A 503 from `/ask` on a config error. The four `OPENAI_*` variables as the required fields. This handoff file being tracked and public.

## Next steps, in order

Each step names the check that proves it.

1. **Rebuild the container on the merged tree.** Docker Desktop was not running when the session ended, so the image has not been rebuilt since the parser, index, and tools landed. Check: `docker build -t agent .`, then the run command with `.env`, then 200 from `/health` and `/ask` and the page at `/`.
2. **Agents and pipeline (DEC-005, DEC-006, DEC-007, DEC-021 to DEC-026).** Add `pydantic-ai-slim[openai]` with an exact pin. Version 2.67.0 resolved together with the current pins on 2026-11-11. Add the types in `models.py`, the four agents with the `PHARMAG_*_MODEL` overrides, `grounding.py`, and `pipeline.py`. Wire `api.py`: build the index in the background at startup, report its state in `/health`, make `/ask` wait for it, and add `/ask/stream`. Checks:
   - Property tests for the quote check and the marker check.
   - A test that plants an unsupported claim and sees the critic path remove it, with a fake model and no network.
   - The four public questions answered end to end in the container, with every expected source file in `sources`.
3. **Answer eval with DeepEval (DEC-015).** A script that calls the live API for the 11 questions and reports source recall and precision, key-fact coverage, the DeepEval metrics, latency, and tokens per question. DeepEval is a development-only dependency. If it has no Python 3.15 wheels, run it from its own environment, since it only calls the API over HTTP. Check: a results file, and the limits of each number stated beside it.
4. **Interface (DEC-013).** Show the answer with its markers, the sources with the cited passage, the plan, the tool calls, and the critic's flags, fed by the streaming endpoint. Then the design pass with the `impeccable` skill. Check: the page works in the container with no request to another host.
5. **Submission polish.** README with the run commands and the eval numbers, `.env.example` with unquoted values, a secret scan of the whole tree, the presentation outline from section 1 of the private brief, and a draft of the summary email for the owner. Check: a clean clone builds and answers.

## 2026-11-12 property-review results

The owner asked for all 47 catalogue entries to be evaluated for tautology, discrimination, orthogonality, generator relevance, and shrinking. This was a review request, not approval of the properties or a new architecture decision. The catalogue, tests, and production code were not changed.

The authoritative detailed review is [`tests/PROPERTIES_findings.md`](../tests/PROPERTIES_findings.md): **F01–F16, 7 HIGH and 9 MEDIUM finding groups**. It distinguishes executed targeted mutation probes from inspection-based findings. The summary below does not replace it.

During the initial review, main verified the baseline with `UV_CACHE_DIR=/tmp/pharmag-review-uv-cache uv run --locked --offline pytest -q`: **67 passed**. Main also ran **five separate in-memory mutants**. Each mutant survived its corresponding suite: the tests still passed. No baseline or mutation probes were rerun during the subsequent docs-only preservation turn (DEC-030).

- Successful `/ask` response includes the API key: `test_api`, **11 passed**.
- Doubled BM25 contribution to rank fusion: `test_index`, **11 passed**.
- Cache stores only in memory, not on disk: `test_retrieval_eval`, **7 passed**.
- Window size reduced to `max(overlap + 1, size - 1)`: `test_retrieval_eval`, **7 passed**.
- Parser cap raised from 5,000 to 50,000 characters: `test_corpus`, **17 passed**.

These were targeted mutation probes, not a full mutation campaign or evidence of production bugs. They expose gaps in what the current suites discriminate.

Existing strengths include conservation (14), fidelity (15), disjointness (16), the independent line oracle (R4), T1 selection, and T3 symmetry. The properties are generally orthogonal. Most generators shrink well, but sampling the real corpus does not make its document structure shrinkable.

During the initial review, the skill copy in `ai-config/skills/property-based-testing/` and its manifest row in `ai-config/README.md` were added and remain uncommitted. That initial review made no decisions-log or defense-brief edits; subsequent preservation is recorded in DEC-030 and E13. No skill or MCP server was used during preservation. No commits or pushes were made during either turn.

## Next review actions — proposals, not approved

These review actions supplement, and do not replace or authorize, the implementation steps above. The agents check-in, expected-answer confirmation, and property approval blockers remain.

1. **Read the findings first.** Start with [`tests/PROPERTIES_findings.md`](../tests/PROPERTIES_findings.md), the authoritative detailed review, not just this summary.
2. **Clarify the owner's contracts before changes.** Take the unresolved contract questions and proposed fixes to the owner. DEC-030 approves recording the review only; it settles none of those questions and authorizes no fixes.
3. **Follow severity and stable IDs.** After owner approval, work through the 7 HIGH and then 9 MEDIUM finding groups using their stable IDs F01–F16. Update `tests/PROPERTIES.md` and the corresponding tests together for each approved change; production changes also require owner approval. Keep executed targeted probes distinct from inspection-only findings when recording follow-up checks.

The existing proposal summary follows; use the detailed findings for the full scope and evidence.

1. **Security wording and success-path checks.** Fix property 3: a literal prohibition on any protected value appearing as a substring is impossible for arbitrary values, including the empty string. Ask the owner to settle the protected-value non-disclosure wording; do not choose the contract here. Add a secret-absence assertion for successful `/ask` responses once that contract is agreed.
2. **Independent tool and index witnesses.** Use independent fixture oracles for brands and glossary entries (T6/T7), rather than deriving the expected universe from the system under test. Guarantee independent positive ranking and interaction witnesses (I1–I4, T2/T3). Avoid I4 returning early on any collision and thereby skipping its ranking assertion.
3. **Parser thresholds and structure.** Pin the expected cap independently of the production constant. Generate 4,999/5,000/5,001-character cases and oversized lines, plus heading-level-6 and multifile cases.
4. **Retrieval geometry and cache sequences.** Strengthen exact fixed-window geometry (R1–R4) and nonempty/completeness checks (R5). Model cache sequences with mixed hits, reconstruction, and model switching; use model-tagged outputs so cross-model reuse is observable.
5. **API and static-page coverage.** Expand the partial-configuration/invalid-body cross product. Add configuration cases for HTTP, short values, and whitespace-only values. Strengthen static locality and asset-wiring checks.
6. **Index generators and unresolved contracts.** Add signed, zero, tied, and empty index inputs. Ask the owner to settle zero-vector behavior: I5 claims unit vectors, while the code retains zero vectors. Also ask about negative `k`, invalid batching, and invalid concurrency where their behavior is unspecified. These are contract questions, not decisions made by the review.

## Facts the code does not show

- **The retrieval numbers.** One live run over 13 gold files, with the raw question as the query. Recall at 6 is 0.92 for the heading-tree chunks and 0.69 for 1,000-character windows. With a drug filter, recall at 3 is 0.85 against 0.69. One gold file is 7.7 points, and a larger chunk is easier to hit, so read the gap as an indication.
- **Why `find_interactions` exists.** No search mode finds the warfarin table row that names ibuprofen (question C3). The worker's prompt has to make that tool the obvious choice for a two-drug question, without fixing the tool order in code.
- **The config is strict (DEC-014).** A quoted, missing, or misspelled variable makes `/ask` return 503. The local `.env` is corrected. Run anything live with `uv run --locked --env-file .env ...`. The per-role override variables need the same check when they are added.
- **The proxy, in outline.** The SDK paths work on the base URL with no `/v1` suffix. Tool calls, several tool calls in one turn, strict JSON schema output, `temperature: 0`, and `reasoning_effort` are all accepted. Small chat calls take 1 to 5 seconds. The private brief has the details.
- **Libraries moved after the model's training data.** Starlette's test client needs `httpx2`. The `openai` SDK is on version 3. PydanticAI is on 2.67, and the docs read so far were for 2.0.0. Read current docs through context7 before coding against any of them.
- **A flaky property test can be a false property.** The index test "a chunk's own text returns it first" failed one run in six because rank fusion does not guarantee it. The code was right. Ask whether the property is true before changing code.
- **`GLOSSARY.md` uses Windows line ends.** The parser drops them. A quote check should still compare text with whitespace normalized.

## How the work ran, for the next session's planning

- The main session plans, briefs, reviews every diff, reruns every check, merges, and pushes. Builders use the `builder` agent definition at medium effort.
- Parallel builders each get `isolation: "worktree"` and commit on their own branch. A worktree has no `.env`, so a task that needs live calls runs in the main checkout. Give each builder a different insertion point in `tests/PROPERTIES.md`, or the merge conflicts.
- The owner's plan has a 5-hour usage limit. It ended one builder mid-task. That builder's files were complete in the working tree, so check the tree before redoing the work. Stop a running agent with the `TaskStop` tool.
- After a merge, remove the worktree with `git worktree remove` and delete the branch.
- Before each commit, scan the staged diff for the key and the proxy hostname. Commit messages carry no co-author lines and end with the session link line that the harness provides. Push after each verified step (DEC-020).
- Tracked docs follow pstack's `technical-writing` and `unslop` skills, and stay free of the proxy hostname and of the brief's own text. The four public questions are the one exception (DEC-027).
