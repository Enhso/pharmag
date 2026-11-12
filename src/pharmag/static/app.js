const form = document.getElementById("ask-form");
const input = document.getElementById("question");
const button = form.querySelector("button");
const result = document.getElementById("result");

// textContent only: the answer and the problem texts are never parsed as HTML.
function node(tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

function list(items) {
  const ul = document.createElement("ul");
  ul.append(...items.map((item) => node("li", item)));
  return ul;
}

function details(title, ...children) {
  const element = document.createElement("details");
  element.append(node("summary", title), ...children);
  return element;
}

function evidence(citations) {
  if (!citations.length) return node("p", "No citations.");
  return list(
    citations.map(
      (c) =>
        `[${c.marker}] ${c.claim} (${c.kind}, ${c.status}) ${c.file}, ${c.section}, ` +
        `lines ${c.line_start}-${c.line_end}: "${c.quote}"`,
    ),
  );
}

function plan(p) {
  const scope = p.in_scope ? "In scope." : "Out of scope.";
  return [
    node("p", `${scope} ${p.reason}`),
    list(p.sub_questions.map((q) => `${q.text} (drugs: ${q.drugs.join(", ") || "none"})`)),
  ];
}

function toolCalls(calls) {
  if (!calls.length) return node("p", "No tool calls.");
  return list(
    calls.map(
      (c) =>
        `Sub-question: ${c.worker}. Tool: ${c.tool}. Arguments: ${JSON.stringify(c.args)}. ` +
        `Hits: ${c.hits.map((h) => h.chunk_id).join(", ") || "none"}. Note: ${c.note}`,
    ),
  );
}

function critic(c) {
  return [
    node("p", `Review rounds: ${c.review_rounds}. Marker check: ${c.marker_check}.`),
    node("p", "Removed claims"),
    c.removed.length ? list(c.removed.map((r) => `${r.text} (${r.reason})`)) : node("p", "None."),
    node("p", "Cautions"),
    c.cautions.length
      ? list(c.cautions.map((x) => `[${x.marker}] ${x.text} (${x.reason})`))
      : node("p", "None."),
    node("p", "Unmarked statements"),
    c.unmarked.length ? list(c.unmarked) : node("p", "None."),
  ];
}

function showAnswer(body) {
  const u = body.usage;
  const stats =
    `Total time ${body.timings.total.toFixed(1)} s. Tokens: ${u.input_tokens} in ` +
    `(${u.cached_input_tokens} cached), ${u.output_tokens} out, ${u.requests} requests.`;
  result.replaceChildren(
    node("p", body.answer, "answer"),
    node("h2", "Sources"),
    body.sources.length ? list(body.sources) : node("p", "No sources."),
    details("Evidence", evidence(body.citations)),
    details("Plan", ...plan(body.plan)),
    details("Tool calls", toolCalls(body.tool_calls)),
    details("Critic", ...critic(body.critic)),
    node("p", stats, "stats"),
  );
}

function showProblem(message, detail) {
  result.replaceChildren(node("p", message, "error"), ...(detail ? [detail] : []));
}

function showConfigProblems(problems) {
  showProblem(
    "The server is not configured correctly, so it cannot answer yet.",
    list(problems.map((p) => `${p.variable} ${p.problem}`)),
  );
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) {
    result.replaceChildren(node("p", "Type a question first.", "error"));
    input.focus();
    return;
  }
  button.disabled = true;
  const started = Date.now();
  const waiting = node("p", "");
  const tick = () => {
    const seconds = Math.floor((Date.now() - started) / 1000);
    waiting.textContent = `Working. An answer can take a minute or more. ${seconds} s elapsed.`;
  };
  tick();
  result.replaceChildren(waiting);
  const timer = setInterval(tick, 1000);
  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const body = await response.json().catch(() => null);
    if (response.ok && body) {
      showAnswer(body);
    } else if (response.status === 503 && body && body.config_problems) {
      showConfigProblems(body.config_problems);
    } else if (response.status === 503 && body && body.error === "index") {
      showProblem(`The documents could not be indexed: ${body.detail}`);
    } else if (response.status === 502 && body && body.error === "pipeline") {
      showProblem(`The answer failed at the ${body.stage} stage: ${body.detail}`);
    } else {
      result.replaceChildren(node("p", `The request failed (HTTP ${response.status}).`, "error"));
    }
  } catch {
    result.replaceChildren(node("p", "Could not reach the server.", "error"));
  } finally {
    clearInterval(timer);
    button.disabled = false;
  }
});
