# Handoff

Rewritten on 2026-11-12 at the end of the second working session. Rewrite this file before the next session stops.

The deadline is 2026-11-13 at 23:59 Casablanca time, which is 22:59 UTC if Morocco is on UTC+1 that day. The graders assess the last commit pushed before it.

## Where things stand

A working proof of concept is on `main` and pushed (DEC-031). It is the fallback submission. If nothing else lands, this state already meets the brief's hard constraints H1 to H12.

## Read these first

| File | Why |
|---|---|
| `CLAUDE.md` | The working agreement. The owner decides, and every ruling is logged |
| `docs/decisions.md` | The authority on what is decided, DEC-001 to DEC-031. Do not reopen a ruling. DEC-031 lists six choices the assistant made that the owner can still veto |
| `docs/architecture.md` | The design of the core, updated to match what was built |
| `docs/scoping.md` | The brief's constraints H1 to H18, their consequences, and the risks |
| [`tests/PROPERTIES_findings.md`](../tests/PROPERTIES_findings.md) | The review of the first 47 properties, F01 to F16. Read before proposing property changes |
| `defense-brief.md` | Private and gitignored. Evidence E1 to E14, proxy details, and the defense of each ruling. Add to it with every decision and measurement |
| `ai-config/README.md` | Manifest of skills, MCP servers, agents, and plugins. Add a row when a session first uses a skill or an MCP server |

## What exists on main

Everything below is merged and pushed. 112 tests pass with no network (`uv run --locked pytest -q`).

- **Corpus, index, tools.** Unchanged since the first session: 451 heading-tree chunks, hybrid exact search, four tools.
- **Type contract.** `models.py` holds what each LLM role returns and what `/ask` returns.
- **Agents.** `agents.py` has the planner, the worker with its four tool wrappers, the writer, the critic, and a redactor that shares the writer's prompt and model. The writer has an output validator: a draft whose prose uses a marker with no claim goes back to the writer inside the same call.
- **Grounding.** `grounding.py` has the quote check and the marker checks as pure functions.
- **Pipeline.** `pipeline.py` runs stages 1 to 8 with the limits of DEC-026, records tokens per role, and emits trace events.
- **API.** `api.py` builds the engine in the background, reports `building`, `ready`, or `failed` in `/health`, and routes `/ask` through the pipeline. A failed stage gives 502. A failed index build gives 503, and the next question starts the build again.
- **Config.** The four `PHARMAG_*_MODEL` overrides, checked as strictly as the required variables.
- **Page.** Plain. It shows the answer, the sources, and four collapsed blocks: evidence, plan, tool calls, critic.
- **README and `.env.example`.** Run commands, endpoints, variables. No eval numbers yet.

Not built yet: `/ask/stream` and a page that uses it, the design pass, the answer eval with DeepEval, a time cap per request, and the presentation outline.

## How the proof of concept was checked

- **Container.** `docker build -t agent .` gives a 395 MB image. With `docker run -p 8000:8000 --env-file .env agent`, `/health` reports `ready` 5 to 7 seconds after start, the page and its two assets return 200, and a body with no `question` returns 422.
- **Eleven eval questions against the container**, run twice: once before the review fixes and once after. Both times all eleven returned 200 with every expected source file, and no answer needed the marker repair. P2 also cited one file outside its expected and allowed lists (`medlineplus-apixaban.md`). In the second run the median time was 29 seconds, from 3 to 99. Five questions took the retry round, two had claims removed, and P2 carries two cautions.
- **Latency varies with the retry round.** P1 took 26 seconds in two runs and 99 seconds in the third, when the critic sent it back.
- **The page in a real browser.** Headless Chrome asked a question through the page. The answer, the sources, and the four blocks rendered, and no request went to another host. `/favicon.ico` returns 404.
- **What limits those numbers.** One run per question. The expected sources of C1 to C7 are our own. The expected answers are still drafts. Times depend on the proxy and on the model the graders configure.

## Independent review of the pipeline

A verifier agent compared the build with `docs/architecture.md` and the rulings, and proved each finding with scripted models and no network. It shows what the code does when a model misbehaves, not how often a real model does. The status column says what this session did about each finding. A builder fixed nine of them, each with a test that fails without the fix.

| ID | Severity | Finding | Status |
|---|---|---|---|
| V1 | High | After the redaction, code checks only the markers. A redactor that drops a marker and keeps its sentence, or ignores an unmarked statement, lets a known-unsupported claim reach the user (against DEC-022) | Fixed. After the redaction, code removes a sentence of the draft that carried an unsupported marker, or an unmarked statement, when it is still there word for word. A paraphrase is beyond what code can see |
| V2 | Medium | When every worker of the retry round fails, the request returns 502 and the complete first draft is lost (against DEC-007) | Fixed. The first draft ships, and the redaction removes what is unsupported |
| V3 | Medium | An in-scope plan with no sub-questions runs no worker, and the writer answers from nothing | Fixed. The question itself becomes the one sub-question |
| V4 | Medium | Two verdicts for one claim: the first wins, so `supported` can hide `unsupported` | Fixed. The worst status wins |
| V5 | Medium | A failed worker's exception text goes into the writer's prompt. A provider that echoes the key could put it in an answer | Fixed. Only the exception's type name goes into `not_found` |
| V6 | Medium | `drop_dangling` ends a sentence at "e.g." or "St.", so the front of a removed sentence can stay | Fixed for `e.g.`, `i.e.`, `St.`, `vs.`, and `Dr.`. A sentence must also start with a capital, a digit, a bullet, `[`, or `(` |
| V7 | Medium | When every claim is removed, the answer is the disclaimer alone, with no explanation | Fixed. One sentence says that no claim was supported |
| V8 | Low | The quote check accepts a trivial quote such as "the" or a partial word. How strict it should be is the owner's call | Open, owner |
| V9 | Low | A blank follow-up or unmarked string starts a retry round | Fixed |
| V10 | Low | `docs/architecture.md` said stage 8 "attaches the trace", and no trace list is returned | Fixed in the doc |
| V11 | Low | The per-call usage line is logged at INFO, which uvicorn's logging hides. The cache warning does appear | Open |
| V12 | Low | The three synchronous tools run in worker threads, so `emit` is called off the event loop. `/ask/stream` must hand events over with a thread-safe call | Open, matters for step 3 |
| V13 | Low, unproven | A marker written as `[1-3]` passes every marker check | Open |
| V14 | Low, unproven | A redactor that renumbers markers would attach a sentence to the wrong source | Open |

The verifier also ran 21 mutations of the code, and eleven survived the tests. Tests now guard nine of those behaviours: every citation of a claim is checked, a chunk that no tool returned fails the quote check, the ambiguous path and its cautions, the critic's unmarked list, a missing verdict, a duplicate verdict, `sources` without uncited claims, the Markdown-emphasis and Unicode folding, and a stronger property for `drop_dangling`. Two are still unguarded: the cache-drop warning, and the `asyncio.shield` around the engine build.

## What waits on the owner

Each item has a date the owner is as likely to miss as to meet.

1. **The six choices in DEC-031.** Veto or accept each. The first one matters most: code appends the cautions, a numbered source list, and the disclaimer to the `answer` text. By 2026-11-13, 10:00.
2. **Expected answers.** `evals/questions.json` still says "Draft". Confirm or correct each. This blocks the answer eval. By 2026-11-13, 11:00.
3. **Properties.** `tests/PROPERTIES.md` now lists the first 47 entries plus C7, C8, S14 to S18, and 25 to 40. The owner's rule is to confirm each one. The proposals of F01 to F16 also wait. By 2026-11-13, 13:00.
4. **`ai-config/transcripts/2026-11-11a.txt`.** It is untracked. It contains the proxy hostname three times, so this session did not commit it. The owner either redacts it and has it committed, or keeps it out of the repo. By 2026-11-13, 12:00.
5. **The built-in `artifact-diagramming` skill** is listed in the manifest without a copy, because it ships inside Claude Code with no license that permits one. The working agreement says to copy each used skill. Accept or overrule. By 2026-11-13, 12:00.
6. **How strict the quote check is (V8).** Today a quote of one word, or of part of a word, passes when it occurs in the passage. A floor of a few whole words would close that. By 2026-11-13, 12:00.
7. **Earlier choices the owner can veto.** Python 3.15. `bm25s`. `httpx2` as the test client dependency. A 503 from `/ask` on a config error. This handoff file being tracked and public.
8. **The presentation overview.** A private page at <https://claude.ai/artifact/Gh2KSEbR3sKLQwAMwj2den>. Say whether a copy belongs in the repo.
9. **The rehearsal and the summary email** are the owner's own tasks. Rehearse against a timer by 2026-11-13, 19:00. Send the email with the repo link by 2026-11-13, 21:30.

## Next steps, in order

Each step names the check that proves it. Steps 1 and 2 raise the grade most. Step 4 is required by the brief.

1. **Answer quality on the public questions.** P3's answer is correct but thin: two or three sentences. The planner made one sub-question where the prompt allows one per drug as well. Check: P3 cites warfarin sections 7.3 and 2.4 and sertraline sections 5.3 and 7.1, three runs in a row.
2. **Answer eval with DeepEval (DEC-015).** The session's throwaway script already posts the eleven questions and compares the sources. Its logic belongs in `evals/`: source recall and precision, key-fact coverage, the DeepEval metrics, latency, and tokens per question. DeepEval is a development-only dependency. If it has no Python 3.15 wheels, run it from its own environment, since it only calls the API over HTTP. Check: a results file, the limits of each number stated beside it, and the numbers in the README.
3. **Interface (DEC-012, DEC-013).** Add `/ask/stream`, which sends each `TraceEvent` and ends with the full response. The pipeline already emits the events. Then the page shows progress per stage, and the `impeccable` skill handles the design pass. Add a favicon. Check: the page works in the container with no request to another host, in a real browser.
4. **Submission polish.** A secret scan of the whole tree, the presentation outline from section 1 of the private brief, a draft of the summary email, and a clean clone that builds and answers. Check: `git clone`, the two documented commands, and one question, on a path with no `.env` history.
5. **Latency and limits (DEC-012, DEC-026).** A retry round adds 15 to 26 seconds. The slowest question took 72 seconds. Set a time cap per request from these measurements, and decide whether six workers and ten tool calls stay. Check: the cap is a named constant with a test, and the owner has ruled on the limits.
6. **Property-review follow-ups.** Only after the owner rules on item 3 above. Work through F01 to F16 by severity, and update `tests/PROPERTIES.md` and the tests together.

## Facts the code does not show

- **`lookup_glossary` was never called** in the eleven questions. Workers chose among the other three tools. Expect the question "is the fourth tool needed?".
- **The critic did not use "ambiguous"** until one paragraph was added to its prompt, about claims that say two documents agree while the passages word the item differently. P2 now carries three cautions, which may be one or two too many.
- **PydanticAI 2.67 refuses a run-level `output_type`** on an agent that has output validators. That is why the redaction has its own agent. Inside an output validator, `ctx.retry` counts the rejections so far and `ctx.max_retries` is the budget.
- **The proxy reports cached input tokens on some calls only.** The pipeline logs a warning when a role's cache hit rate falls by more than 0.25. The INFO usage lines do not reach the container log, because nothing configures logging.
- **The first full run hid a defect behind a green result.** All eleven questions had their expected sources, yet P2 had lost half its answer: the writer cited markers 8 to 10 with only 7 claims, and the last-resort repair dropped those sentences. Check `critic.marker_check` and read the answers, not only the sources.
- **The config is strict (DEC-014).** A quoted, missing, or misspelled variable makes `/ask` return 503. Run anything live with `uv run --locked --env-file .env ...`.
- **The proxy, in outline.** The SDK paths work on the base URL with no `/v1` suffix. Small chat calls take 1 to 5 seconds. The private brief has the details.
- **`GLOSSARY.md` uses Windows line ends.** The parser drops them, and the quote check compares text with whitespace normalized.
- **A flaky property test can be a false property.** Ask whether the property is true before changing code.

## How the work ran, for the next session's planning

- The main session wrote the type contract first, as signatures with no body, and pushed it. Two builders then worked in parallel worktrees against it with no merge conflict. A third builder made the fixes. A verifier agent reviewed the result.
- `isolation: "worktree"` branches from the remote default branch, so push before dispatching. A worktree has no `.env`, no brief, and no private notes, so a builder makes no live calls and the brief must carry any fact from those files.
- Say in each brief that commit messages end with the session link line. Three builders read "no co-author lines" as "no trailers" and left it out.
- Builders cannot run a long compound command with a heredoc inside a worktree. They write files with the Write tool and run one command per call.
- `setsid nohup uv run uvicorn ... & echo $!` records the launcher's PID, not the server's. Find the listener with `ss -ltnp` and kill that PID.
- A page check in a real browser needs no project dependency: `uv run --no-project --with playwright python <script>` with `channel="chrome"` drives the installed Chrome.
- The owner's plan has a 5-hour usage limit. Check the working tree before redoing a builder's work.
- After a merge, remove the worktree with `git worktree remove` and delete the branch.
- Before each commit, scan the staged diff for the key and the proxy hostname. Push after each verified step (DEC-020).
- Tracked docs follow pstack's `technical-writing` and `unslop` skills, and stay free of the proxy hostname and of the brief's own text. The four public questions are the one exception (DEC-027).
