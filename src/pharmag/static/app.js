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

function showAnswer(body) {
  const sources = body.sources.length ? list(body.sources) : node("p", "No sources.");
  result.replaceChildren(
    node("p", body.answer),
    node("h2", "Sources"),
    sources,
    node("p", body.disclaimer, "disclaimer"),
  );
}

function showConfigProblems(problems) {
  result.replaceChildren(
    node("p", "The server is not configured correctly, so it cannot answer yet.", "error"),
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
  result.replaceChildren(node("p", "Working..."));
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
    } else {
      result.replaceChildren(node("p", `The request failed (HTTP ${response.status}).`, "error"));
    }
  } catch {
    result.replaceChildren(node("p", "Could not reach the server.", "error"));
  } finally {
    button.disabled = false;
  }
});
