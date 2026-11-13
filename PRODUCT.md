# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **First: a work-test assessor.** They clone the repo, run the container, open the page cold, and try a few questions, most likely the four public ones. They judge whether the agent's work is visible and whether each statement can be traced to a document. Confirmed by the owner (DEC-037).
- **Second: the owner, presenting live.** The page is on a shared screen during a timed presentation, so the steps and the sources must read at a distance.

## Product Purpose

pharmag answers compound pharmacology questions from 21 local Markdown documents and from nothing else. An answer is a success when a reader can see how it was worked out (the plan, the tool calls, the review) and can check every sentence against a quoted passage with its file, section, and line range.

## Positioning

Every claim carries a verbatim quote that code has found in the cited passage, and a critic has judged each claim against that passage before the answer goes out. A claim that fails is removed and reported, and a claim that needs a clinical reading is kept with a caution. The page shows this trace as the real pipeline emits it; nothing on it is simulated.

## Operating Context

- One command builds and runs it: `docker build -t agent . && docker run -p 8000:8000 --env-file .env agent`. The page, the API, and every asset come from that one server on port 8000.
- `POST /ask` is the graders' contract and returns one JSON body. `POST /ask/stream` feeds the page with the same body after the trace events.
- An answer takes between a few seconds and about a minute.
- The corpus is ten medicines (acetaminophen, albuterol, amoxicillin, apixaban, aspirin, atorvastatin, ibuprofen, metformin, sertraline, warfarin), each with a DailyMed label and a MedlinePlus page, plus one glossary.

## Capabilities and Constraints

- The pipeline has four visible steps: Plan (sub-questions), Retrieve (tool calls and the passages they return), Write (a draft of numbered claims), Review (a quote check and a critic, with one retry round and a redaction when needed).
- Four local tools: `search_corpus`, `get_section`, `find_interactions`, `lookup_glossary`.
- The writer produces paragraphs, bullets, and `[n]` markers only. No headings, bold, or tables.
- An out-of-scope question gets a short refusal with status 200.
- No build step, no Node, and no file from another host (DEC-013). A test fails on any reference to another host in the static folder.
- One question at a time: no history, no accounts, no saved answers.

## Brand Commitments

- The owner's direction, binding: "blank pharmaceutical / high-end cosmetic", "serious, clinical, quiet, precise — like high-end apothecary packaging or a well-typeset medical information leaflet, never a hospital portal or startup landing page."
- System sans-serif only, with monospace for file and tool names. Near-black on white. One muted accent at most. No cards, gradients, or decorative lines.
- The name in the page's header is "PharmAg". The browser tab title is "Pharmacology research assistant".

## Evidence on Hand

- Real answers from the running container, such as the comparison of warfarin and apixaban (six claims, one removed, two review rounds, three source files).
- The eleven eval questions in `evals/questions.json`, four of them public.
- No testimonials, users, or benchmarks exist, and none may be invented.

## Product Principles

1. Show the work that happened, never a stand-in for it.
2. Every sentence leads to its passage in one step.
3. What the critic removed or doubted is reported, not hidden.
4. Quiet by default: detail is one click away, never in the way.
5. It is a research demonstration, and it says so on every answer.

## Accessibility & Inclusion

Semantic landmarks, full keyboard use, visible focus, live announcements of progress and of the answer, text contrast of at least 4.5 to 1, and no motion for a reader who asks for reduced motion.
