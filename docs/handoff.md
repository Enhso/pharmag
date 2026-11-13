# Handoff

Rewritten on 2026-11-13 at the end of the design session, which built the streaming endpoint and the page. Rewrite this file before the next session stops.

The deadline is 2026-11-13 at 23:59 Casablanca time. That is 23:59 UTC: the machine's time zone data has Morocco on UTC+0 today. The graders assess the last commit pushed before it.

## Where things stand

`main` is pushed and is the submission as it stands. It meets the brief's hard constraints H1 to H12. 132 tests pass with no network (`uv run --locked pytest -q`).

Built this session (DEC-037):

- **`POST /ask/stream`.** Server-sent events: one `trace` frame per pipeline event, then one `answer` frame equal to the `/ask` body, or one `error` frame with the stage. `/ask` is unchanged. The pipeline emits three new events: `planned`, `drafted`, `reviewed`. A client that disconnects cancels the run.
- **The page** (`src/pharmag/static/`). An empty page with one large question field and the four public questions as samples. After a question is sent: the question as a header, four step rows (Plan, Retrieve, Write, Review) fed live by the stream, the cited answer, the cautions, the sources with their quotes, and the disclaimer pinned to the bottom. No build step and nothing from another host.

Checked on the container rebuilt from this tree:

| Check | Result |
|---|---|
| The four public questions, asked through the page in Chrome | All four answered: 29.9, 56.4, 68.5, and 10.8 seconds |
| Hosts the browser contacted during those runs | One, the container itself |
| Console errors or warnings | None |
| `curl -N` on `/ask/stream` with the out-of-scope question | Three `trace` frames, then the `answer` frame |
| Eight scripted behaviours at 1440 and 390 pixels wide | All pass, no horizontal overflow |
| Esc during a run | The server cancels the run; the question stays in the field, selected |

The working, failed, and cancel states were checked through the real endpoint with a replayed pipeline, not with live model runs. A caution was seen on a live run of P4. Only Chrome on Linux was used.

A reviewer agent that saw only the brief and the screenshots returned eight fixes, and all eight are in. Its verdict on those eight was ship. It did not review the whole page again after the fixes.

## Read these first

| File | Why |
|---|---|
| `CLAUDE.md` | The working agreement. The owner decides, and every ruling is logged |
| `docs/decisions.md` | The authority on what is decided, DEC-001 to DEC-037. Do not reopen a ruling |
| `docs/architecture.md` | The design of the core, matching what is built |
| `src/pharmag/models.py` | `AskResponse` and `TraceEvent`, the two shapes the page reads |
| `PRODUCT.md` | Who the page is for and what it must show |
| `.impeccable/surfaces/src-pharmag-static-index-html.md` | The page's brief and its direction: palette, type, states |
| `DESIGN.md` | The page's design system as built: colours, type, layout, components, and what not to add. `.impeccable/design.json` holds the same tokens for tools |
| `defense-brief.md` | Private and gitignored. Evidence E1 to E18. Add to it with every decision and measurement |
| `ai-config/README.md` | Manifest of skills, MCP servers, agents, and plugins. Add a row when a session first uses one |

## How to run things

- Container: `docker build -t agent . && docker run -p 8000:8000 --env-file .env agent`. A container named `pharmag-poc` runs the current `main` on port 8000. Remove it with `docker rm -f pharmag-poc` before starting another on that port.
- Eleven questions against a running server: `python3 evals/live_check.py http://localhost:8000 <out_dir>`.
- Anything live outside the container: `uv run --locked --env-file .env ...`. The config check is strict (DEC-014), so a quoted or misspelled variable makes `/ask` return 503.
- A browser check without a project dependency: `uv run --no-project --with playwright python <script>` with `channel="chrome"`.
- To see the page's states without spending tokens, start the real app with `pharmag.api.answer` and `pharmag.api.build_engine` replaced by a replay of a saved `/ask` body. This session's replay server and capture scripts were in the session scratchpad and are not in the repo.

## What waits on the owner

Each item has a date the owner is as likely to miss as to meet.

1. **The new properties.** `tests/PROPERTIES.md` adds 67 to 75 (the stream, the three new events, and two on the page). Property 25 as restated and 59 to 66 from the session before also wait. The owner's rule is to confirm each one. By 2026-11-13, 14:00.
2. **The assistant's choices in DEC-037.** A third new event (`drafted`), retrieval and tool use shown as one row, and no table rendering, dark theme, or fallback from the stream to `/ask`. Each stands unless the owner vetoes it. By 2026-11-13, 14:00.
3. **The fourth sample question** ends "and what is the threshold" with no question mark, because the public question is tracked that way (DEC-027). Keep it word for word, or complete it on the page. By 2026-11-13, 14:00.
4. **The time cap per request (DEC-012).** No cap is set. P3 took 68.5 seconds today, 54 of them in retrieval. Recommended: a timeout of 60 seconds per model call, and no retry round once 60 seconds have passed. By 2026-11-13, 15:00.
5. **One more fix for P3.** No run so far states that the warfarin label names sertraline's drug class in its interaction table (section 7.3). Recommended: print the matched terms with each passage `find_interactions` returns, then run P3 three times. By 2026-11-13, 15:00.
6. **The rehearsal and the summary email** are the owner's own tasks. Rehearse against a timer by 2026-11-13, 19:00. Send the email with the repo link by 2026-11-13, 21:30.

## Next steps

1. **Answer eval with DeepEval (DEC-015).** `evals/live_check.py` compares sources only. Add key-fact coverage, the DeepEval metrics, latency, and tokens per question. The expected answers are confirmed (DEC-034). Check: a results file, the limits of each number stated beside it, and the numbers in the README.
2. **Submission polish.** The presentation outline, a draft of the summary email, a secret scan of the whole tree, a clean clone that builds and answers, and this file rewritten as a note on the state at submission.
3. **Deferred.** The property-review follow-ups F01 to F16 in [`tests/PROPERTIES_findings.md`](../tests/PROPERTIES_findings.md) (DEC-034).

## Open findings

| ID | Finding | Status |
|---|---|---|
| V13 | A marker written as a range, such as `[1-3]`, is not read as a marker | Documented limit (DEC-034). The page prints such a marker as plain text |
| V14 | A redactor that renumbers markers would attach a sentence to the wrong source | Documented limit (DEC-034). The prompt forbids it |
| V15 | The cancel on disconnect in `/ask/stream` has no automated test | Open, low. The test client cannot drop a connection mid-stream. Checked by hand through the page |
| V16 | The page was checked in Chrome on Linux only | Open. No Safari, Firefox, or real phone |
| V17 | The stream sends no keep-alive between events | Open, low. The longest silent stretch seen was about 20 seconds, the write stage. A proxy with a shorter idle timeout would cut the stream; none sits in front of the container |
| Tests | Two behaviours have no test: the cache-drop warning, and the `asyncio.shield` around the engine build | Open, low |

V12 (events emitted off the event loop) is closed: the stream hands them over with `call_soon_threadsafe`, and a test emits from a worker thread.

## Facts the code does not show

- **The page reads `answer` and cuts its tail.** `answer` ends with the cautions, the source list, and the disclaimer as plain text for API readers. The page builds those parts from `critic.cautions`, `citations`, and `disclaimer`, and removes the tail by its headings (`Sources:`, `Cautions:`). A change to `_answer_text` in `pipeline.py` needs the same change in `proseOf` in `app.js`.
- **Review time on the page** is the sum of `quote_check`, `review`, `retry`, and `redact` from `timings`. Tool calls of the retry round are listed under Retrieve as a follow-up.
- **The test for property 12 reads every file in the static folder as text** and fails on `http://`, `https://`, or `//` followed by a letter. So the favicon is an inline SVG with its slashes percent-encoded, a binary file in that folder would break the test, and a JavaScript comment needs a space after `//`.
- **The page test for the label** looks for the exact string `<label for="question">`, so that tag carries no class.
- **What started the retry round before the fixes.** In 15 traced answers, 7 took it. The causes recorded were a quote that failed on punctuation, a writer's remark about what a document lacks, and the critic not seeing a section heading. Where the critic's flags were recorded, none was an unsupported medical statement.
- **Quotes of two words are real.** "Malignant hypertension" is a whole list item, so the quote check has no minimum length.
- **Sources vary between runs.** C5 cited both aspirin files in three runs and only the MedlinePlus file in a fourth. P2 often cites `medlineplus-apixaban.md` beside the two labels. P3 cites `medlineplus-warfarin.md` as well.
- **`lookup_glossary` was not called** in any of the eleven eval questions. A question about a glossary term does cite `GLOSSARY.md`.
- **PydanticAI 2.67.** A run-level `output_type` is refused on an agent that has output validators, which is why the redaction has its own agent. Inside an output validator, `ctx.retry` counts the rejections so far and `ctx.max_retries` is the budget.
- **FastAPI 0.162.** Its built-in server-sent-event response works only when the route itself is a generator, which cannot answer 503 before the stream starts. The stream endpoint uses `StreamingResponse` and writes the frames itself.
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
- A full-page browser capture repeats a pinned footer in the middle of the image. Grow the viewport to the document's height and capture the viewport.
