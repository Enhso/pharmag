# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- When coding against a third-party library, the main loop lists `~/.womm-skills/golden-specs/` once, reads a spec only if its filename names that library or problem, and passes that spec's path in any brief that needs it. Subagents read only the specs their brief names. Writing, research and other non-code work skip it.
- State your assumptions explicitly.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- Ask when the answer would change what you build and neither the request, the code nor a sensible default settles it; name what is unclear. Otherwise state the assumption and proceed.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, name the check that proves each step before you start it.

Prefer property-based tests wherever a property holds across an input domain. List every property in plain words in `tests/PROPERTIES.md`, one line each, naming the test that encodes it, then ask the user to confirm each property holds.

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## Deadlines

When a plan includes tasks the user does, give each one a P50 deadline: a concrete date the user is as likely to miss as to meet. Set it at the median of your duration estimate, with no buffer.

## Model selection

The main loop plans, decides and verifies. Subagents are dispatched with a tier alias, never a pinned model ID. A small model gets only work whose mistakes are cheap to spot; code edits and judgment calls go to `sonnet` or larger.

- **Main loop: `opus`**, the `settings.json` default. At the start of a major refactor or migration, architecture planning, a run that leads many subagents, a long unattended run, or deep research or quantitative analysis, suggest the user switch the session to `fable` with `/model`. When Fable runs out mid-session, suggest `/compact` before switching back to `opus`: the switch drops Fable's thinking and re-writes the whole cache.
- **`fable` takes the hardest delegated piece:** a cross-cutting design, a major refactor or migration step, a subtle algorithm, deep quantitative analysis. At most 1 at once, on `opus` too when it falls back.
- **`sonnet` is the default subagent:** builder and verifier work, well-scoped coding (a fix whose cause is known, feature iteration, mechanical edits from a written spec), and repeated review, investigation or drafting. At most 2 at once.
- **`haiku` takes cheap-to-check tasks:** searches and file sweeps, reading logs, summarizing, running a gate and reporting its output. At most 4 at once.
- The caps are separate: 1 `fable`, 2 `sonnet` and 4 `haiku` may run together.
- A panel skill the user invokes by name (Council, RedTeam, WorldThreatModel above Fast) may run the panel it defines beyond these caps. Never start one of those panels on your own.
- Verification never runs on `haiku`, and the main loop still re-runs the gates itself on any subagent's work.
- **Effort:** dispatch each subagent with `effort: medium` unless its role names a level. When its result falls short, escalate in this order: give the agent a way to check its own work (a test, a build, a script); raise effort one level; move to the next model up at a lower effort than the smaller one used. Past `high`, try the next model up before `xhigh` or `max`. For a batch with automatic checks, run at `low` and re-run only the failures at `high`.
- **Fable fallback:** Fable is available on this account only some of the time. Wherever a model choice names `fable` (a tier here, a `pstack-models.md` line, a pstack skill default or panel seat), use `opus @high` once `fable` is missing from the `Agent` tool's model list, a call with it is rejected, or a `fable` subagent stops on an access, rate-limit or usage-limit error. Re-dispatch that work fresh on `opus @high` with the same brief, fill a panel seat with `opus @high` in place of dropping it, say so in the report, and stay on `opus` for the rest of the session.
- For pstack roles, the overrides in `pstack-models.md` (below) take precedence over these tiers, with two exceptions: the Fable fallback applies, and verification never runs on `haiku`. Where pstack sends verification to the `swarm workers` model and that line names `haiku`, verify on `sonnet`.
- `haiku` means Haiku 5.5 only because `settings.json` sets `ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku-5-5`.
<!-- Source: Anthropic, "Which Claude model should you build with?" (claude.dev/blog, 2026-11-09). Fable cap of 1 and the `opus @high` fallback level are local choices, not from the article. -->

## Workflows

Run only when the user types `/lifecycle <cmd>`. The entry skill `~/.claude/skills/lifecycle/SKILL.md` loads only the one contract it routes to.

- [review](skills/lifecycle/workflows/review/SKILL.md): check a diff against the repo's hard rules
- [thermo-nuclear-code-quality-review](skills/lifecycle/workflows/thermo-nuclear-code-quality-review/SKILL.md): strict maintainability audit
- [radioactive](skills/lifecycle/workflows/radioactive/SKILL.md): 11-phase feature lifecycle

## Commits

Write commit messages without `Co-Authored-By: Claude` or `Generated with Claude Code` lines. The potion-hooks coauthor-scrubber denies any commit that carries them, and `settings.json` sets `attribution` to empty strings so the harness no longer asks for them.

## pstack

@~/.claude/pstack-models.md

<!--
Maintenance notes for the owner. Block comments are stripped before this file loads, so they cost no context.
- Loads into every session and every non-Explore/Plan subagent, in any directory. Keep only what an agent cannot learn from the repo.
- Target: under 200 lines. A rule that must hold every time belongs in a hook or permission rule; prose here only steers.
- Run `/doctor prompt-audit` (Claude Code 2.1.283+) in a fresh session after edits, or when ~/snags.md logs the same conflict twice.
- Last reviewed 2026-11-05: golden-specs pointer made conditional, lifecycle made opt-in, commit-trailer rule added (snags.md).
- Sections 1-4 are working if: fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
-->

