# pstack model configuration

Per-role model overrides for pstack skills. Each pstack SKILL.md names its defaults in a Models section; the values here override those defaults. Delete a line to fall back to the skill default. A value of `inherit-parent` or `auto` runs that role on the parent session's model (the `Agent` call omits `model`); an alias entry in a panel list still counts toward that panel's fan-out. A model may carry a reasoning effort, as in `opus @xhigh` (levels: low, medium, high, xhigh, max); the role then runs through the pstack effort agent of that level, each entry of a panel list on its own. `default effort` sets the level for a value without one; `session` keeps the parent session's effort. `session hook: off` stops the Claude Code or Codex SessionStart hook, or the pstack Pi extension, from injecting the poteto-mode mandate; any other value, or no line, leaves it on.

feature, refactoring: sonnet
bug-fix: opus @high
perf-issue: opus @high
hillclimb: opus @high
judgment and prose: sonnet
strongest judgment: fable
how explorer: haiku
how explainer: sonnet
why investigators: haiku
why synthesizer: sonnet
reflect tooling: sonnet
reflect judgment, divergent, synthesizer: sonnet
arena runners: sonnet, haiku
arena cross-judge pool: sonnet
swarm workers: haiku
architect runners: fable, sonnet
interrogate reviewers: opus, sonnet
thermos reviewers: opus
no-comments reviewer: opus

default effort: medium
session hook: on
