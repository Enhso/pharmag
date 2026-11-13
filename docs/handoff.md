# Handoff

Rewritten on 2026-11-13 at the end of the third working session, which checked readiness and fixed what the checks found. The next session is the design session. Rewrite this file before that session stops.

The deadline is 2026-11-13 at 23:59 Casablanca time. That is 23:59 UTC: the machine's time zone data has Morocco on UTC+0 today. The graders assess the last commit pushed before it.

## Where things stand

`main` is pushed and is the fallback submission. It meets the brief's hard constraints H1 to H12. 120 tests pass with no network (`uv run --locked pytest -q`).

Checked this session, before any change: a clone of the public repo with no credentials builds and answers, and the key and the proxy host are in no tracked file and no commit.

Six fixes then went in (DEC-033), each with a test that fails without it:

- The quote check compares whole words and whole numbers in order. It ignores punctuation, Markdown marks, and case, and it no longer accepts "5 mg" inside "0.5 mg".
- A worker gets a failing quote back inside its own call.
- The critic sees each cited passage's section heading.
- The writer's prompt rules out remarks on what a document lacks or how it is organized.
- A failed second review, or a failed redaction call, ships the draft in hand.
- The token usage lines reach the container log.

One run of the eleven eval questions against the rebuilt container, compared with the last run before the fixes:

| Measure | Before | After |
|---|---|---|
| 200 with every expected source | 11 of 11 | 11 of 11 |
| Claims removed | 3 | 0 |
| Questions that took the retry round | 5 | 1 |
| Median seconds | 29 | 29 |
| Slowest, seconds | 99 | 59 |

Each side is one run per question, and the variance between runs is large.

## Read these first

| File | Why |
|---|---|
| `CLAUDE.md` | The working agreement. The owner decides, and every ruling is logged |
| `docs/decisions.md` | The authority on what is decided, DEC-001 to DEC-036. Do not reopen a ruling |
| `docs/architecture.md` | The design of the core, matching what is built |
| `src/pharmag/models.py` | `AskResponse` and `TraceEvent`, the two shapes the page reads |
| `src/pharmag/static/` | The page as it is: `index.html`, `app.js`, `style.css` |
| `defense-brief.md` | Private and gitignored. Evidence E1 to E16. Add to it with every decision and measurement |
| `ai-config/README.md` | Manifest of skills, MCP servers, agents, and plugins. Add a row when a session first uses one |

## The design session, in order

The rulings are DEC-012 (a streaming endpoint feeds the page, and `/ask` stays plain JSON) and DEC-013 (a static page with every asset vendored, and the `impeccable` skill for the design pass). Each step names its check.

1. **`POST /ask/stream`.** Same body as `/ask`. The response is `text/event-stream`: one `data:` line of JSON per `TraceEvent`, then one last event that holds the full `AskResponse`, or an error with the stage and the detail.
   - `pipeline.answer(question, engine, emit)` already calls `emit` for each event.
   - Three of the four tools are synchronous, so the framework runs them in worker threads and `emit` is called off the event loop. Hand each event to an `asyncio.Queue` with `loop.call_soon_threadsafe`.
   - A config error and a failed index build answer 503 before the stream starts. A `PipelineError` after that becomes the error event, because the status is already 200.
   - Events that exist today: `started` and `finished` for each stage (`plan`, `research`, `write`, `quote_check`, `review`, `retry`, `redact`, `respond`), and `tool_call` with the worker's sub-question, the tool, its arguments, and its hits. No event carries the plan or the verdicts. Add one if the page should show the plan before the answer exists.
   - Check: a test with a scripted engine that asserts the order of the events and the last payload, then `curl -N` against the container.
2. **The page.** It shows progress per stage while the user waits (answers took 2 to 59 seconds in the last run), then the answer, the cautions, the sources with file, section, lines, and quote, and the trace (plan, tool calls, critic) folded away.
   - The `answer` string already ends with the cautions, a numbered source list, and the disclaimer as plain text, for a reader of the API. Decide whether the page prints `answer` whole or builds those parts from `citations`, `critic.cautions`, and `disclaimer`. It must not show them twice.
   - No build step and no file from another host. The test for property 12 fails on any reference to another host.
   - `/favicon.ico` returns 404 today.
3. **The design pass** with the `impeccable` skill. Copy the skill into `ai-config/` and add its row to the manifest when it is first used.
4. **Check on the real artifact.** Rebuild the container, open the page in a real browser, ask the four public questions, and confirm that no request goes to another host. `uv run --no-project --with playwright python <script>` with `channel="chrome"` drives the installed Chrome without a project dependency.

## How to run things

- Container: `docker build -t agent . && docker run -p 8000:8000 --env-file .env agent`. A container named `pharmag-poc` already runs the current `main` on port 8000. Remove it with `docker rm -f pharmag-poc` before starting another on that port.
- Eleven questions against a running server: `python3 evals/live_check.py http://localhost:8000 <out_dir>`. It saves each response and prints one line per question with the missing and extra sources, the review rounds, and the tokens.
- Anything live outside the container: `uv run --locked --env-file .env ...`. The config check is strict (DEC-014), so a quoted or misspelled variable makes `/ask` return 503.
- To see why a retry round fired, run `pipeline.answer` in a script that wraps `pipeline._check` and prints the verdicts and the unmarked statements of each round.

## What waits on the owner

Each item has a date the owner is as likely to miss as to meet.

1. **The new and changed properties.** `tests/PROPERTIES.md` restates property 25 and adds 59 to 66. The owner's rule is to confirm each one. By 2026-11-13, 12:00.
2. **The time cap per request (DEC-012).** No cap is set. The slowest answers are now slow in the research stage, which a cap on the retry round would not shorten. The model client's own timeout is 600 seconds per call. Recommended: a timeout of 60 seconds per model call, and no retry round once 60 seconds have passed. By 2026-11-13, 12:00.
3. **One more fix for P3.** No run so far states that the warfarin label names sertraline's drug class in its interaction table (section 7.3). `find_interactions` returns that passage, and the tool's output does not tell the worker which terms matched in it. Recommended: print the matched terms with each passage, then run P3 three times. By 2026-11-13, 12:00.
4. **The rehearsal and the summary email** are the owner's own tasks. Rehearse against a timer by 2026-11-13, 19:00. Send the email with the repo link by 2026-11-13, 21:30.

## After the design session

1. **Answer eval with DeepEval (DEC-015).** `evals/live_check.py` compares sources only. Add key-fact coverage, the DeepEval metrics, latency, and tokens per question. The expected answers are confirmed (DEC-034). Check: a results file, the limits of each number stated beside it, and the numbers in the README.
2. **Submission polish.** The presentation outline, a draft of the summary email, a secret scan of the whole tree, a clean clone that builds and answers, and this file rewritten as a note on the state at submission.
3. **Deferred.** The property-review follow-ups F01 to F16 in [`tests/PROPERTIES_findings.md`](../tests/PROPERTIES_findings.md) (DEC-034).

## Open findings

| ID | Finding | Status |
|---|---|---|
| V12 | `emit` is called off the event loop by the synchronous tools | Open. Step 1 above handles it |
| V13 | A marker written as a range, such as `[1-3]`, is not read as a marker | Documented limit (DEC-034). No saved answer shows one |
| V14 | A redactor that renumbers markers would attach a sentence to the wrong source | Documented limit (DEC-034). The prompt forbids it |
| Tests | Two behaviours have no test: the cache-drop warning, and the `asyncio.shield` around the engine build | Open, low |

V8 (how strict the quote check is) and V11 (the usage lines) are closed by DEC-033.

## Facts the code does not show

- **What started the retry round before the fixes.** In 15 traced answers, 7 took it. The causes recorded were a quote that failed on punctuation, a writer's remark about what a document lacks, and the critic not seeing a section heading. Where the critic's flags were recorded, none was an unsupported medical statement.
- **Quotes of two words are real.** "Malignant hypertension" is a whole list item, so the quote check has no minimum length.
- **Sources vary between runs.** C5 cited both aspirin files in three runs and only the MedlinePlus file in a fourth. P2 often cites `medlineplus-apixaban.md` beside the two labels. P3 now cites the two MedlinePlus files as well.
- **`lookup_glossary` was not called** in any of the eleven eval questions. A question about a glossary term does cite `GLOSSARY.md`.
- **PydanticAI 2.67.** A run-level `output_type` is refused on an agent that has output validators, which is why the redaction has its own agent. Inside an output validator, `ctx.retry` counts the rejections so far and `ctx.max_retries` is the budget.
- **The proxy reports cached input tokens on some calls only.** The log warns when a role's cache hit rate falls by more than 0.25.
- **`GLOSSARY.md` uses Windows line ends.** The parser drops them.
- **A flaky property test can be a false property.** Ask whether the property is true before changing code.

## How the work ran, for the next session's planning

- A builder agent works in its own worktree against a written brief, and the main session reads the diff, reruns the tests, and checks the result on the container.
- `isolation: "worktree"` branches from the remote default branch, so push before dispatching. A worktree has no `.env`, no brief, and no private notes, so a builder makes no live calls and the brief must carry any fact from those files.
- Say in each brief that commit messages end with the session link line, and carry no co-author line.
- Builders write files with the Write tool and run one command per call inside a worktree.
- After a merge, remove the worktree with `git worktree remove` and delete the branch.
- Before each commit, scan the staged diff for the key and the proxy hostname. Push after each verified step (DEC-020).
- The owner's plan has a usage limit. Check the working tree before redoing a builder's work, and keep live runs to what a decision needs.
- Tracked docs stay free of the proxy hostname and of the brief's own text. The four public questions are the one exception (DEC-027).
