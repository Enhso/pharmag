---
name: Pharmacology research assistant
description: A white page where the question is the page. One text field, then a four-step trace, then a cited answer typeset like a medicine leaflet.
colors:
  ground: "#ffffff"
  ink: "#14181b"
  ink-2: "#555d63"
  ink-3: "#6a7278"
  line: "#e4e8ea"
  accent: "#1d6570"
  wash: "#e8f1f2"
typography:
  question-field:
    fontFamily: "Inter, SF Pro Text, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(1.625rem, 1.15rem + 2vw, 2.375rem)"
    fontWeight: 400
    lineHeight: 1.22
    letterSpacing: "-0.02em"
  question-header:
    fontFamily: "Inter, SF Pro Text, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(1.25rem, 1.1rem + 0.7vw, 1.5rem)"
    fontWeight: 550
    lineHeight: 1.3
    letterSpacing: "-0.012em"
  answer:
    fontFamily: "Inter, SF Pro Text, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.65
  body:
    fontFamily: "Inter, SF Pro Text, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  step:
    fontFamily: "Inter, SF Pro Text, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, SF Pro Text, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 550
    lineHeight: 1.5
    letterSpacing: "0.01em"
  small:
    fontFamily: "Inter, SF Pro Text, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.55
  mono:
    fontFamily: "ui-monospace, SF Mono, SFMono-Regular, Menlo, Consolas, Liberation Mono, monospace"
    fontSize: "0.9375em"
    fontWeight: 400
rounded:
  quote: "3px"
  focus: "2px"
  badge: "1em"
  dot: "50%"
spacing:
  gutter: "clamp(1.25rem, 5vw, 3rem)"
  measure: "38rem"
  step-row-y: "0.4375rem"
  step-gap: "0.75rem"
  dot: "0.5rem"
  step-name: "4.5rem"
components:
  link:
    textColor: "{colors.accent}"
    typography: "{typography.label}"
  step-dot-active:
    backgroundColor: "{colors.accent}"
    size: "0.4375rem"
    rounded: "{rounded.dot}"
  step-dot-done:
    backgroundColor: "{colors.ink}"
    size: "0.4375rem"
    rounded: "{rounded.dot}"
  citation-numeral:
    textColor: "{colors.accent}"
  citation-caution:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.ground}"
    rounded: "{rounded.badge}"
  quote-cited:
    backgroundColor: "{colors.wash}"
    textColor: "{colors.ink}"
    rounded: "{rounded.quote}"
    typography: "{typography.step}"
---

# Design System: Pharmacology research assistant

## Overview

**Creative North Star: "The Package Leaflet"**

The question is the page. One line of text lives at two scales: a large field on a blank sheet, then the header above its answer. Everything else is typeset under it like a medicine leaflet. The owner's brief asks for a "blank pharmaceutical / high-end cosmetic" look, near-black text on a pure or off-white ground, one muted clinical accent at most, and a text cursor as the hero.

The page has no boxes, no cards, no thread and no shell. Hierarchy comes from size, weight and space. The page is one column, 38rem wide, left-aligned. It is light only (`color-scheme: light`).

**Key Characteristics:**
- White ground, cool near-black ink, two greys, one petrol accent, one pale wash.
- One sans family. Mono only for code spans (file names, tool names).
- Rows and rules, not containers. The only filled shapes are the caution badge and the cited quote.
- The text caret is the focus mark of the question field.
- Motion is one shared-element move, one slow pulse, and short fades. All of it stops under `prefers-reduced-motion`.

## Colors

Seven values. Six are neutral. The accent is rare on purpose.

### Primary
- **Petrol** (#1d6570): the one accent. Used for the caret, the active step dot, the hollow ring of a failed step, citation numerals, the "ambiguous" status word, the `.flag` text in step summaries, links, the focus ring, and the fill of caution badges. 6.7:1 on the ground. 5.8:1 on the wash.

### Neutral
- **Ground** (#ffffff): page and footer background. The footer has its own ground so the sticky disclaimer covers the text that scrolls under it.
- **Ink** (#14181b): primary text, the done dot, active step summary, verdicts.
- **Ink 2** (#555d63): secondary text. Step summaries, step details, the disclaimer, notes. 6.7:1 on the ground.
- **Ink 3** (#6a7278): quietest text. Placeholder, sample questions, times, line ranges, the corpus line, pending step names, chevrons, dot outlines. 4.9:1 on the ground. Below 4.5:1 on the wash (about 4.25:1), so it is not used inside a cited quote.
- **Line** (#e4e8ea): one hairline above the sticky footer, and the underline of the "technical detail" summary in the failure view. Decorative, not text.
- **Wash** (#e8f1f2): text selection and the cited quote.

### Named Rules
**The One Voice Rule.** Petrol marks only three things: where the reader is (caret, focus, active step), where a claim comes from (citation numerals), and where to take care (caution badges, "ambiguous", `.flag`). It is not used for decoration or for buttons as fills.

**The No Second Accent Rule.** Failure, refusal and caution use petrol, not red or amber. A failed step is a hollow petrol ring. The cue is carried by text as well as colour.

## Typography

**Sans:** Inter, then SF Pro Text, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif.
**Mono:** ui-monospace, SF Mono, SFMono-Regular, Menlo, Consolas, Liberation Mono, monospace.

Inter is first in the stack but the page loads no font file, so most readers see their system sans. The direction contract says "system sans throughout"; the stack and the build agree in effect, but the CSS does name Inter.

**Character:** a plain reading face at modest sizes. Weight 550 (not 500 or 600) is the working emphasis; 600 is used only for numerals and small headings.

### Hierarchy
- **Question field** (400, clamp(1.625rem, 1.15rem + 2vw, 2.375rem), 1.22, -0.02em): the empty-state textarea. Auto-grows. Placeholder is Ink 3.
- **Question header** (550, clamp(1.25rem, 1.1rem + 0.7vw, 1.5rem), 1.3, -0.012em, `text-wrap: balance`): the same question after submit.
- **Answer** (400, 1.0625rem desktop, 1rem under 34rem, line-height 1.65 desktop and 1.6 narrow, `text-wrap: pretty`): the prose.
- **Body** (400, 1rem, 1.6): page default.
- **Step** (400, 0.875rem, 1.5): step rows, quote text, passage rows.
- **Label** (550, 0.8125rem, 0.01em): brand, links, step names are 550 at 0.875rem. Section headings (`h3`, "Cautions", "Sources") are 600 at 0.8125rem, not uppercase.
- **Small** (400, 0.75rem, 1.55): footer, line ranges, the meta line.
- **Mono** (0.9375em): code spans only. Tabular numerals (`tabular-nums`) are on for times, counts, numerals and line ranges.

### Named Rules
**The Weight 550 Rule.** Emphasis is weight 550 against 400. No bold (700) anywhere; 600 is reserved for numerals and the small section headings.

**The Mono Is Data Rule.** Monospace marks a file name, a tool name or a line range. It is never used for mood.

## Layout

One centred column. `main` is `38rem` plus a gutter on each side (`--measure`, `--gutter: clamp(1.25rem, 5vw, 3rem)`). Text is left-aligned. Prose lines run at the 38rem measure.

- **Empty view:** the field starts at `clamp(4rem, 26vh, 15rem)` from the top, so it sits about a third of the way down. Sample questions are below it in Ink 3. The corpus line is at the foot.
- **Asked view:** the question header sits `clamp(2.5rem, 9vh, 5rem)` from the top (1.75rem under 34rem). The steps follow (2rem, 1.25rem narrow). The answer follows (2.5rem, 1.5rem narrow).
- **Step grid:** five columns, `dot 0.5rem | name 4.5rem | summary 1fr | time auto | chevron 0.5rem`, with a `0.75rem` column gap and `0.4375rem` row padding. Details indent to the summary column. Under 34rem the grid becomes four columns and each step takes two lines: name and time, then summary at full width. Details indent to the name column.
- **Spacing:** no fixed scale. Values are rem steps used in place: 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.125, 1.25, 1.75, 2, 2.5, 2.75.
- **Sticky footer:** in the answered view the disclaimer is pinned to the bottom with a `--line` top rule, so it stays in sight with the answer.
- **Breakpoints:** one, `max-width: 34rem`. Key hints (`kbd`, `.keys`) are hidden under it and on `hover: none`.
- **Page height:** `min-height: 100dvh`, footer at the bottom by flex.

## Elevation & Depth

None. The page is flat. There are no shadows, no blur and no layered surfaces. Depth is order and space. The sticky footer is separated by one `--line` hairline and its own white ground.

## Shapes

Mostly square and open. The shapes in use:

- **Dot:** a 0.4375rem circle (50%) with a 1px outline.
- **Caution badge:** a pill (`border-radius: 1em`) filled with petrol.
- **Cited quote row:** a 3px radius on a wash fill.
- **Focus ring:** 2px solid petrol, 3px offset, 2px radius.
- **Chevron:** two 1px hairlines on a 0.375rem square, rotated 45deg. No icon font or glyph.
- **Hairlines:** 1px `--line` only.

## Components

### Question field
A borderless, backgroundless textarea. No outline: the petrol caret is the focus mark. Placeholder "Ask about a medicine" in Ink 3. An "Ask" link and key hints fade in below it once text is present (`.filled`); the sample questions fade out at the same time (0.25s, `--ease`).

### Sample questions
A grid of plain buttons, `0.75rem` apart, 0.9375rem, Ink 3, turning Ink on hover (0.15s). No border, no chip.

### Link
Petrol, 0.8125rem, weight 550, underline on hover with a 0.25em offset. In the top bar the link is Ink 2 and turns Ink on hover.

### Step row (signature)
A `details` row for Plan, Retrieve and Review, and a plain row for Write. Each row has a dot, a name, a one-line summary, a time and a chevron. The state is carried by `data-state`:
- **pending / skipped:** hollow Ink 3 dot; name in Ink 3 at weight 400.
- **active:** petrol-filled dot that pulses to 0.3 opacity (1.5s, alternate, infinite); summary in Ink.
- **done:** Ink-filled dot; summary in Ink 2.
- **failed:** hollow petrol dot.

A row whose detail is empty shows no chevron and has a default cursor. Details hold numbered sub-questions (Ink 3 numerals in a 1.25rem column), tool calls (bold name in Ink, arguments in Ink 2, 0.8125rem), hit counts (Ink 3, tabular), and verdicts (petrol numeral, status word in 550). An "unsupported" claim is struck through in Ink 2.

### Citation numeral
A superscript-style petrol number (0.6875em, weight 600, raised 0.45em, tabular). A pseudo-element widens the hit area by 0.6rem by 0.5rem. Hover underlines it.

### Caution badge
The citation numeral inverted: white on a petrol pill (`padding: 0.14em 0.42em`). In the Cautions list it sits in a 1.75rem column at 0.75rem with no raise.

### Sources and passages
A file name (mono, 0.8125rem, weight 500) over a list of passage rows. Each passage row is a summary: section name (Ink 2), line range (Ink 3, 0.75rem), reference count (petrol, 0.75rem, weight 600), chevron. Opened, it lists quotes in typographic quotes. A quote that a clicked numeral points to takes the wash fill (0.4s fade); the list bleeds -0.5rem so the fill reaches past the text edge.

### Failure view
Said plainly under the steps. The first line in weight 550, the reason in Ink 2, a "Try again" link, and a "technical detail" summary underlined in `--line` that opens a mono block. It takes focus so that Try again is the next tab stop.

### Answer prose
Lists use an en dash that hangs in the page margin (`list-style-type: "\2013\00a0"`), so text starts on the column edge. Ordered lists indent 1.5em. List markers are Ink 3. Paragraphs are 1em apart; list items 0.7em.

### Motion
- `--ease: cubic-bezier(0.16, 1, 0.3, 1)`.
- The question moves from field to header with a view transition named `question` (0.45s, `--ease`). The root cross-fade is 0.25s.
- The answer fades in over 0.5s.
- Chevrons turn over 0.2s. Cited-quote wash 0.4s. Send and sample fades 0.25s.
- Under `prefers-reduced-motion: reduce`, all transitions and animations are off.

## Do's and Don'ts

### Do:
- **Do** use one column at 38rem and left-align everything.
- **Do** make hierarchy with size, weight (400 / 550) and space.
- **Do** use petrol only for position, provenance and care (see The One Voice Rule).
- **Do** keep Ink 3 off the wash fill.
- **Do** pair state colour with a text cue, as the step rows do with their summary text.
- **Do** keep a visible focus ring (2px petrol, 3px offset) on every control except the question field, whose caret is the focus mark.
- **Do** switch views by `data-view` on `body` and state by `data-state` on the step.

### Don't:
- **Don't** wrap content in cards, panels, bordered boxes or a chat thread.
- **Don't** add a second accent colour, or a red for errors.
- **Don't** add shadows, gradients or blur.
- **Don't** use bold (700) or all-caps small labels above headings.
- **Don't** use mono for anything but data.
- **Don't** add a dark theme or a fallback from the stream to `/ask` (both listed as not built in the surface brief).

## Not canonized, and notes on the build

- `scrollbar-color: #c5ccd0 transparent` on `html` is a one-off grey outside the palette. It is not a token.
- The favicon inlines the accent as `%231d6570`, so it must be changed by hand if the accent changes.
- `.quotes li` sets `outline: 0` for the cited-quote jump target. It is a script-focused row, not a control.
- The CSS names Inter first but ships no font file. The contract says "system sans".
- The contract names the caution marker a "badge"; the build uses a petrol pill on the citation numeral. The pill and the 3px wash row are the only filled shapes, which is a slight softening of "No boxes".
