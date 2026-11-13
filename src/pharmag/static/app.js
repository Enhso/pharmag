// The page for POST /ask/stream. Server text reaches the DOM as text nodes only, never as HTML.

const $ = (id) => document.getElementById(id);
const form = $("ask");
const input = $("question");
const answer = $("answer");
const problem = $("problem");
const reduced = matchMedia("(prefers-reduced-motion: reduce)");

// Which row each pipeline stage belongs to, and what the row says while the stage runs.
const ROW = { plan: "plan", research: "retrieve", write: "write", quote_check: "review", review: "review", retry: "review", redact: "review" };
const RUNNING = {
  plan: "Reading the question",
  research: "Searching the documents",
  write: "Drafting from the passages found",
  quote_check: "Checking each quote against its passage",
  review: "The critic is reading the cited passages",
  retry: "Second round: searching again for what lacked support",
  redact: "Removing what the passages do not support",
};
const SPOKEN = {
  plan: "Planning.",
  research: "Retrieving passages.",
  write: "Writing the draft.",
  quote_check: "Reviewing the draft.",
  retry: "Second review round.",
};
const VERDICT = { supported: "Supported", ambiguous: "Caution", unsupported: "Removed" };
// A failed stage, named the way the rows name it.
const FAILED = { plan: "planning", research: "retrieval", write: "writing", quote_check: "review", review: "review", retry: "review", redact: "review" };

let view = "empty"; // empty | working | answered | failed
let hasAnswer = false; // a finished answer is still on the page, behind the question field
let controller = null;
let clock = null;
let run = { question: "", plan: null, calls: [], reviewed: "" };

const rows = {};
for (const li of document.querySelectorAll(".step")) {
  rows[li.dataset.step] = {
    li,
    sum: li.querySelector(".sum"),
    time: li.querySelector(".time"),
    detail: li.querySelector(".detail"),
    began: null,
    spent: 0,
  };
}

// Children may be nested arrays or empty values (a condition that did not hold); only real content is kept.
const kept = (children) => children.flat(Infinity).filter((child) => child != null && child !== false && child !== "");
const put = (node, ...children) => node.replaceChildren(...kept(children));

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value != null && value !== false) node.setAttribute(name, value);
  }
  node.append(...kept(children));
  return node;
}

const count = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const number = (n) => n.toLocaleString("en-US");
const seconds = (s) => `${s < 10 ? s.toFixed(1) : Math.round(s)} s`;
const say = (text) => ($("status").textContent = text);

// Views

function setView(next) {
  view = next;
  document.body.dataset.view = next;
  const label = next === "working" ? "Cancel" : next !== "empty" ? "New question" : hasAnswer ? "Back to answer" : "";
  $("back").hidden = !label;
  $("back-label").textContent = label;
}

// The question moves between the field and the header as one element where the browser can do it.
function move(change) {
  if (document.startViewTransition && !reduced.matches) document.startViewTransition(change);
  else change();
}

function fit() {
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
}

function toQuestion() {
  if (view === "working") controller.abort();
  stopClock();
  move(() => {
    setView("empty");
    fit();
    input.focus();
    input.select();
  });
}

function toggle() {
  if (view !== "empty") toQuestion();
  else if (hasAnswer) {
    move(() => {
      setView("answered");
      answer.focus({ preventScroll: true });
    });
  }
}

// Steps

function setState(name, state) {
  const row = rows[name];
  if (state === "active" && row.began === null) row.began = performance.now();
  if (state !== "active" && row.began !== null) {
    row.spent += performance.now() - row.began;
    row.began = null;
    row.time.textContent = seconds(row.spent / 1000);
  }
  row.li.dataset.state = state;
}

const setSum = (name, ...nodes) => put(rows[name].sum, ...nodes);

function resetSteps() {
  for (const row of Object.values(rows)) {
    row.began = null;
    row.spent = 0;
    row.li.dataset.state = "pending";
    row.sum.replaceChildren();
    row.time.textContent = "";
    if (row.detail) {
      row.detail.replaceChildren();
      row.detail.parentElement.open = false;
    }
  }
}

function startClock() {
  clock = setInterval(() => {
    for (const row of Object.values(rows)) {
      if (row.began !== null) row.time.textContent = `${Math.floor((row.spent + performance.now() - row.began) / 1000)} s`;
    }
  }, 1000);
}

function stopClock() {
  clearInterval(clock);
}

function onTrace({ stage, kind, data }) {
  if (kind === "started" && stage === "respond") setState("review", "done");
  else if (kind === "started") {
    setState(ROW[stage], "active");
    setSum(ROW[stage], stage === "retry" && run.reviewed ? `${run.reviewed}. ${RUNNING.retry}` : RUNNING[stage]);
    if (SPOKEN[stage]) say(SPOKEN[stage]);
  } else if (kind === "finished" && ["plan", "research", "write"].includes(stage)) setState(ROW[stage], "done");
  else if (kind === "planned") showPlan((run.plan = data));
  else if (kind === "tool_call") showCalls(run.calls.push(data) && run.calls, run.plan);
  else if (kind === "drafted") setSum("write", count(data.claims, "claim") + (stage === "retry" ? ", revised" : ""));
  else if (kind === "reviewed") {
    run.reviewed =
      [
        data.supported && `${data.supported} supported`,
        data.ambiguous && `${data.ambiguous} with a caution`,
        data.unsupported && `${data.unsupported} unsupported`,
        data.unmarked && `${data.unmarked} without a marker`,
      ]
        .filter(Boolean)
        .join(", ") || "No claim to review";
    setSum("review", run.reviewed);
  }
}

function showPlan(plan) {
  const subs = plan.sub_questions;
  setSum("plan", !plan.in_scope ? "Out of scope" : subs.length ? count(subs.length, "sub-question") : "Researched as asked");
  put(
    rows.plan.detail,
    el("p", {}, plan.reason),
    subs.length > 0 && el("ol", { class: "subs" }, subs.map((q) => el("li", {}, el("div", {}, q.text, el("span", { class: "aside" }, q.drugs.join(", ")))))),
  );
}

const where = (chunkId) => chunkId.replace(/#L(\d+)-(\d+)$/, " $1–$2");

function showCalls(calls, plan) {
  if (!calls.length) return setSum("retrieve", "No tool call");
  const tools = [...new Set(calls.map((c) => c.tool))];
  const passages = new Set(calls.flatMap((c) => c.hits.map((h) => h.chunk_id)));
  const files = new Set([...passages].map((id) => id.split("#")[0]));
  setSum(
    "retrieve",
    ...tools.flatMap((tool, i) => [i ? ", " : "", el("code", {}, tool)]),
    ` · ${count(passages.size, "passage")} from ${count(files.size, "document")}`,
  );
  const planned = new Set((plan?.sub_questions ?? []).map((q) => q.text));
  const groups = new Map();
  for (const call of calls) groups.set(call.worker, [...(groups.get(call.worker) ?? []), call]);
  put(
    rows.retrieve.detail,
    [...groups].map(([worker, list]) =>
      el(
        "section",
        { class: "group" },
        el("p", { class: "worker" }, planned.size > 0 && !planned.has(worker) && el("span", { class: "aside" }, "Follow-up after review: "), worker),
        el(
          "ul",
          { class: "calls" },
          list.map((call) => {
            const args = Object.entries(call.args).filter(([, value]) => value != null && value !== "");
            return el(
              "li",
              {},
              el("code", { class: "call" }, el("b", {}, call.tool), args.map(([key, value]) => [" ", el("span", {}, `${key}: ${value}`)])),
              el("span", { class: "hits" }, call.hits.length ? call.hits.map((h) => el("code", {}, where(h.chunk_id))) : "No passage returned"),
              call.note && el("span", { class: "aside" }, call.note),
            );
          }),
        ),
      ),
    ),
  );
}

function showReview(response) {
  const critic = response.critic;
  const tally = (status) => critic.verdicts.filter((v) => v.status === status).length;
  // Only the counts that are not zero: "1 caution" reads better than "0 supported, 1 caution".
  const parts = [
    tally("supported") > 0 && `${tally("supported")} supported`,
    critic.cautions.length > 0 && el("span", { class: "flag" }, count(critic.cautions.length, "caution")),
    critic.removed.length > 0 && `${critic.removed.length} removed`,
    critic.review_rounds > 1 && `${critic.review_rounds} rounds`,
  ].filter(Boolean);
  setSum("review", parts.length ? parts.map((part, i) => [i ? " · " : "", part]) : "No claim to review");
  const kept = new Map(response.citations.map((c) => [c.marker, c.claim]));
  const removed = [...critic.removed]; // in the order of the unsupported verdicts
  put(
    rows.review.detail,
    el(
      "p",
      {},
      `${count(critic.review_rounds, "review round")}. Code looked for every quote in its cited passage, then the critic judged each claim against those passages.`,
      critic.marker_check === "repaired" && " Code also dropped a sentence that still carried a removed claim.",
    ),
    el(
      "ol",
      { class: "verdicts" },
      critic.verdicts.map((v) => {
        const text = v.status === "unsupported" ? removed.shift()?.text : kept.get(v.claim);
        return el(
          "li",
          { "data-status": v.status },
          el("span", { class: "num" }, String(v.claim)),
          el(
            "div",
            {},
            el("p", { class: "verdict" }, el("span", { class: "status" }, VERDICT[v.status]), text && el("span", { class: "claim" }, text)),
            el("p", { class: "aside" }, v.reason),
          ),
        );
      }),
    ),
    critic.unmarked.length > 0 && [
      el("p", {}, "Statements the critic found without a source marker, taken out of the answer:"),
      el("ul", { class: "plain" }, critic.unmarked.map((text) => el("li", {}, text))),
    ],
  );
}

// Answer

// `answer` ends with the cautions, the source list and the disclaimer as plain text for API readers.
// The page builds those from the response's own fields, so it cuts that tail off the prose.
function proseOf(response) {
  let text = response.answer;
  if (text.endsWith(response.disclaimer)) text = text.slice(0, -response.disclaimer.length);
  for (const [present, heading] of [
    [response.citations.length, "\n\nSources:\n"],
    [response.critic.cautions.length, "\n\nCautions:\n"],
  ]) {
    const at = text.lastIndexOf(heading);
    if (present && at !== -1) text = text.slice(0, at);
  }
  return text.trim();
}

function cite(marker, cited, cautioned) {
  const first = cited.get(marker);
  if (!first) return `[${marker}]`;
  const place = `${first.file}, ${first.section}, lines ${first.line_start}–${first.line_end}`;
  return el(
    "a",
    {
      class: cautioned.has(marker) ? "cite caution" : "cite",
      href: `#source-${marker}`,
      "data-marker": marker,
      title: place,
      "aria-label": `Source ${marker}${cautioned.has(marker) ? ", with a caution" : ""}: ${place}`,
    },
    String(marker),
  );
}

// The writer's whole vocabulary: paragraphs, bullets, [n] markers. Bold and code are tolerated.
function inline(text, cited, cautioned) {
  const nodes = [];
  let last = 0;
  for (const match of text.matchAll(/\[(\d+(?:\s*,\s*\d+)*)\]|\*\*([^*\n]+)\*\*|`([^`\n]+)`/g)) {
    const before = text.slice(last, match.index);
    nodes.push(match[1] ? before.trimEnd() : before);
    if (match[1]) nodes.push(match[1].split(",").map((n) => cite(Number(n), cited, cautioned)));
    else if (match[2]) nodes.push(el("strong", {}, match[2]));
    else nodes.push(el("code", {}, match[3]));
    last = match.index + match[0].length;
  }
  nodes.push(text.slice(last));
  return nodes;
}

function blocks(text, cited, cautioned) {
  const out = [];
  let list = null;
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    const item = /^(?:[-*•]|(\d+)[.)])\s+(.*)$/.exec(line);
    if (!item) list = null;
    if (!line) continue;
    if (!item) {
      out.push(el("p", {}, inline(line, cited, cautioned)));
      continue;
    }
    const tag = item[1] ? "ol" : "ul";
    if (list?.localName !== tag) out.push((list = el(tag)));
    list.append(el("li", {}, inline(item[2], cited, cautioned)));
  }
  return out;
}

function showSources(response) {
  const files = new Map(); // file -> passage key -> { section, lines, quotes }
  for (const c of response.citations) {
    if (!files.has(c.file)) files.set(c.file, new Map());
    const passages = files.get(c.file);
    const key = `${c.section}|${c.line_start}|${c.line_end}`;
    if (!passages.has(key)) passages.set(key, { section: c.section, lines: `${c.line_start}–${c.line_end}`, quotes: [] });
    const quotes = passages.get(key).quotes;
    if (!quotes.some((q) => q.marker === c.marker && q.quote === c.quote)) quotes.push({ marker: c.marker, quote: c.quote });
  }
  const anchored = new Set(); // the first quote of each marker carries the id its numeral links to
  $("sources").hidden = !files.size;
  put(
    $("sources").querySelector(".files"),
    [...files].map(([file, passages]) =>
      el(
        "li",
        {},
        el("code", { class: "filename" }, file),
        el(
          "ul",
          { class: "passages" },
          [...passages.values()].map((passage) => {
            const markers = [...new Set(passage.quotes.map((q) => q.marker))];
            return el(
              "li",
              {},
              el(
                "details",
                {},
                el(
                  "summary",
                  {},
                  el("span", { class: "section" }, passage.section.replaceAll(" > ", " › ")),
                  el("code", { class: "lines" }, `lines ${passage.lines}`),
                  el("span", { class: "refs", "aria-label": `cited by ${markers.join(", ")}` }, markers.join(" ")),
                ),
                el(
                  "ul",
                  { class: "quotes" },
                  passage.quotes.map((q) => {
                    const id = !anchored.has(q.marker) && anchored.add(q.marker) && `source-${q.marker}`;
                    return el("li", { id, "data-marker": q.marker, tabindex: "-1" }, el("span", { class: "num" }, String(q.marker)), el("q", {}, q.quote));
                  }),
                ),
              ),
            );
          }),
        ),
      ),
    ),
  );
}

function showAnswer(response) {
  stopClock();
  const { critic, timings, usage } = response;
  showPlan(response.plan);
  setState("plan", "done");
  if (response.plan.in_scope) {
    showCalls(response.tool_calls, response.plan);
    setSum("write", count(critic.verdicts.length, "claim") + (critic.review_rounds > 1 ? ", revised once" : ""));
    showReview(response);
  }
  for (const name of ["retrieve", "write", "review"]) {
    setState(name, response.plan.in_scope ? "done" : "skipped");
    if (!response.plan.in_scope) setSum(name, "Not run");
  }
  // The server's own timings replace the page's stopwatch. Review covers the checks, the retry and the redaction.
  const spent = {
    plan: timings.plan,
    retrieve: timings.research,
    write: timings.write,
    review: ["quote_check", "review", "retry", "redact"].reduce((sum, stage) => sum + (timings[stage] ?? 0), 0),
  };
  for (const [name, row] of Object.entries(rows)) row.time.textContent = spent[name] ? seconds(spent[name]) : "";

  const cited = new Map();
  for (const c of response.citations) if (!cited.has(c.marker)) cited.set(c.marker, c);
  const cautioned = new Set(critic.cautions.map((c) => c.marker));
  put($("prose"), blocks(proseOf(response), cited, cautioned));
  const gone = critic.verdicts.filter((v) => v.status === "unsupported").map((v) => v.claim);
  $("removed").hidden = !gone.length;
  $("removed").textContent =
    gone.length === 1
      ? `Claim ${gone[0]} was drafted and then removed: it did not pass the check against its cited passage. The Review step has the reason.`
      : `Claims ${gone.slice(0, -1).join(", ")} and ${gone.at(-1)} were drafted and then removed: they did not pass the check against their cited passages. The Review step has the reasons.`;
  $("cautions").hidden = !critic.cautions.length;
  put(
    $("cautions").querySelector("ul"),
    critic.cautions.map((c) => el("li", {}, cite(c.marker, cited, cautioned), el("span", {}, c.reason))),
  );
  showSources(response);
  $("meta").textContent =
    `${seconds(timings.total)} in total · ${count(usage.requests, "model request")} · ` +
    `${number(usage.input_tokens)} input tokens (${number(usage.cached_input_tokens)} cached) · ${number(usage.output_tokens)} output tokens`;
  $("disclaimer").textContent = `For research and technical demonstration only. ${response.disclaimer}`;

  answer.hidden = false;
  hasAnswer = true;
  setView("answered");
  say(response.sources.length ? `Answer ready, from ${count(response.sources.length, "document")}.` : "Answer ready.");
  answer.focus({ preventScroll: true });
}

// Failure

function fail({ what, why, items, raw }) {
  stopClock();
  for (const [name, row] of Object.entries(rows)) {
    if (row.li.dataset.state !== "active") continue;
    setState(name, "failed");
    setSum(name, "Did not finish");
  }
  // Rows that never started say nothing about a request the server turned away.
  $("steps").hidden = Object.values(rows).every((row) => row.li.dataset.state === "pending");
  put(
    problem,
    el("p", { class: "what" }, what),
    why && el("p", { class: "why" }, why),
    items && el("ul", {}, items.map((item) => el("li", {}, item))),
    el("button", { type: "button", class: "link" }, "Try again"),
    raw && el("details", {}, el("summary", {}, "Technical detail"), el("code", {}, raw)),
  );
  problem.hidden = false;
  setView("failed");
  problem.focus({ preventScroll: true });
}

async function refusalOf(response) {
  const body = await response.json().catch(() => null);
  if (body?.error === "configuration") {
    return {
      what: "The server is not configured, so it cannot answer yet.",
      why: "Correct these variables in .env, restart the container, then try again.",
      items: body.config_problems.map((p) => [el("code", {}, p.variable), ` ${p.problem}`]),
    };
  }
  if (body?.error === "index") {
    return { what: "The documents could not be indexed, so the server cannot answer yet.", why: "Trying again starts the indexing again.", raw: body.detail };
  }
  return { what: `The server turned the request away (HTTP ${response.status}).`, why: "Your question is kept. Try again." };
}

// Request

async function* frames(body) {
  const reader = body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += value;
    for (let end; (end = buffer.indexOf("\n\n")) !== -1; buffer = buffer.slice(end + 2)) {
      const frame = buffer.slice(0, end);
      const name = /^event: (.*)$/m.exec(frame)?.[1];
      const data = /^data: (.*)$/m.exec(frame)?.[1];
      if (name && data) yield [name, JSON.parse(data)];
    }
  }
}

async function ask(question) {
  controller?.abort();
  const mine = (controller = new AbortController());
  run = { question, plan: null, calls: [], reviewed: "" };
  hasAnswer = false;
  stopClock();
  resetSteps();
  $("steps").hidden = false;
  answer.hidden = true;
  problem.hidden = true;
  $("asked").textContent = question;
  move(() => setView("working"));
  startClock();
  say("Working on your question.");
  try {
    const response = await fetch("/ask/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal: mine.signal,
    });
    if (!response.ok) return fail(await refusalOf(response));
    for await (const [name, data] of frames(response.body)) {
      if (name === "trace") onTrace(data);
      else if (name === "answer") return showAnswer(data);
      else if (name === "error") {
        return fail({
          what: data.error === "pipeline" ? `The ${FAILED[data.stage] ?? data.stage} step failed, so there is no answer.` : "The server hit an unexpected error, so there is no answer.",
          why: "Your question is kept. Try again, or go back and change it.",
          raw: data.detail,
        });
      }
    }
    fail({ what: "The connection closed before the answer arrived.", why: "Your question is kept. Try again." });
  } catch {
    if (!mine.signal.aborted) fail({ what: "Could not reach the server.", why: "Check that the container is running, then try again." });
  }
}

// Wiring

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (question) ask(question);
  else input.focus();
});

input.addEventListener("input", () => {
  fit();
  form.classList.toggle("filled", input.value.trim() !== "");
});

input.addEventListener("keydown", (event) => {
  // keyCode 229: some browsers report the Enter that confirms an IME composition this way.
  if (event.key !== "Enter" || event.shiftKey || event.isComposing || event.keyCode === 229) return;
  event.preventDefault();
  form.requestSubmit();
});

$("samples").addEventListener("click", (event) => {
  const sample = event.target.closest("button");
  if (!sample) return;
  input.value = sample.textContent;
  input.dispatchEvent(new Event("input"));
  input.focus();
});

// On the empty page any click lands in the question. Once an answer is shown, clicks are the reader's own.
document.addEventListener("click", (event) => {
  if (view !== "empty" || event.target.closest("button, a, summary, textarea, label")) return;
  if (getSelection().isCollapsed) input.focus();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !event.isComposing) toggle();
});

$("back").addEventListener("click", toggle);

problem.addEventListener("click", (event) => {
  if (event.target.closest("button")) ask(run.question);
});

// A step with nothing to show yet does not open.
$("steps").addEventListener("click", (event) => {
  const summary = event.target.closest("summary");
  if (summary && !summary.nextElementSibling.hasChildNodes()) event.preventDefault();
});

// A numeral in the answer opens its quotes under Sources and marks them.
answer.addEventListener("click", (event) => {
  const numeral = event.target.closest("a.cite");
  if (!numeral) return;
  event.preventDefault();
  const quotes = [...$("sources").querySelectorAll(".quotes li")];
  const mine = quotes.filter((li) => li.dataset.marker === numeral.dataset.marker);
  for (const li of quotes) li.classList.toggle("cited", mine.includes(li));
  for (const li of mine) li.closest("details").open = true;
  mine[0]?.focus({ preventScroll: true });
  mine[0]?.scrollIntoView({ block: "center", behavior: reduced.matches ? "auto" : "smooth" });
});

fit();
// The caret opens the page where a pointer can hover. On a touch screen it would raise the keyboard over the samples.
if (matchMedia("(hover: hover)").matches) input.focus();
