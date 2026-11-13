---
version: 1
slug: "src-pharmag-static-index-html"
primary_target: "src/pharmag/static/index.html"
related_targets: ["src/pharmag/static/style.css","src/pharmag/static/app.js"]
---

# The page (`/`)

Mode: Operate, with a Read passage where the answer sits. Code-led. A redesign of the plain first page; its content and behaviour are product truth, its look was a placeholder.

## Job

An assessor opens the page cold, asks one compound question, and must see how the agent worked and where every sentence comes from. The owner also presents it live on a shared screen.

## States

Empty, working (live trace from `POST /ask/stream`), answered, refused (out of scope), failed (retry keeps the question), cancelled (Esc returns to the question, selected).

## Content

- Four step rows fed by real events: Plan, Retrieve, Write, Review. Retrieval is tool use here, so Retrieve names the tools and counts passages and files.
- The answer is the prose part of `answer`; cautions, sources, and the disclaimer are built from the response's own fields.
- Sample questions: the four public questions, word for word.
- Pinned line: "For research and technical demonstration only." then the API's `disclaimer`.

## Not built

Tables, history, dark theme, a fallback from the stream to `/ask`.

## Direction contract

THESIS: The question is the page. One line of text lives at two scales, the centred field on a blank sheet and the header above its answer, and everything else is typeset beneath it like a medicine leaflet. Refuses the chat thread, the card grid, and the dashboard shell.

OWN-WORLD: White carton ground (#FFFFFF). Near-black cool ink (#14181B), two greys for secondary text (#555D63, #6A7278). One petrol accent (#1D6570) for the caret, the active step, citation numerals, and caution badges, with a pale wash (#E8F1F2) for selection and the cited passage. System sans throughout; monospace only for file names, tool names, and line ranges. No boxes: hierarchy comes from size, weight, and space. The corpus is listed like an ingredients line.

STORY: The reader sees what the corpus covers, asks, watches four steps resolve with real sub-questions, tool calls, and verdicts, reads a cited answer, and follows any numeral to its quoted passage.

FIRST VIEWPORT: Small name top left. One large left-aligned text field in a centred column about a third of the way down, caret blinking in petrol. Four sample questions beneath in quiet grey. The ten medicines as a small line at the foot. Nothing else.

FORM: seed: none (pinned). The owner's brief pins it: "blank pharmaceutical / high-end cosmetic", "Near-black text on pure or off-white background", "one muted clinical accent at most", "the text cursor is the hero", "After submit, the input transitions to a secondary header/reference state and the screen reveals the agent's step progression and final cited monograph-style answer."

Signature interaction: on submit the typed question settles from the field into the header, and the four steps resolve in order beneath it. Motion grammar: one shared-element move for the question, a slow pulse on the active step, short opacity fades elsewhere; none under reduced motion.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
