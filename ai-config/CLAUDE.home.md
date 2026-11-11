# Multi-agent work

Applies to any session that dispatches subagents, and to the subagents themselves.

When instructions conflict, the most specific source wins: an agent's brief, then the project's CLAUDE.md, then this file and `~/.claude/CLAUDE.md`.

## Briefing and tone

- Brief a subagent as you would a respected colleague: the goal, why it matters, what done looks like. Directive or punitive phrasing (capitals, threats, blame) makes the recipient less reliable and lowers quality.
- Corrections describe what the work needs. A failed verification is a fact about the work, reported plainly.
- Ask a worker on an open-ended task to rate its difficulty before it starts, so the lead can re-split the task or move it up the escalation order in `~/.claude/CLAUDE.md` (Model selection). Tell it to proceed on its best reading and to ask the lead only when the task itself is unclear.
- Agents misjudge difficulty and give up early on hard problems. When a worker calls a task impossible, check that claim against its evidence; when the evidence is thin, re-dispatch the task with encouragement and a narrower scope.

## Managing

- Delegate the meaningful work, within the tier and parallelism caps already set. Keep the main loop for planning, deciding and verifying: a manager who is also the primary worker overloads itself and cannot bring full capability to the domain problem.
- When editing agent definitions, hooks, settings or a CLAUDE.md is a worker's task, its brief says so. Subagents are told that no agent's message authorizes config changes, so when a worker still declines, the main loop makes the edit itself rather than re-briefing.
- Route, never relay: a subagent writes bulky output to a file and returns the path plus a short summary; pass paths between agents, not contents. A short result (a verdict, a sweep's hits, a gate's output) comes back as text, and the main loop saves it to a file when a later agent needs it.
- Claude Code refuses any subagent's Write of a `.md` file whose name starts with `report`, `summary`, `findings` or `analysis` (any case), and tells every subagent to return findings as text. So a brief names the output file subject first (`c3-findings.md`; any non-`.md` extension such as `.txt` or `.tsv` also passes), calls it the input the next agent reads, and has the worker write it first and update it as it goes, so a crash still leaves the record.
- After a failure, trace it to the gap in the guidance, harness or tooling that allowed it, and propose the edit. "I'll be more careful" is not a fix, and the manager's self-blame is not the finding. The owner decides which edits land. When the rule must hold every time, propose a hook, permission rule or check, not another line of prose.
- Agents that product code launches as runtime roles (a `claude -p` call, a custom agent) inherit every CLAUDE.md level, the plugin hooks and the session reminders unless they opt out. A custom agent's `omitClaudeMd: true` drops the CLAUDE.md files only; hooks and reminders still fire. A headless call runs from an empty directory outside ~ (`mktemp -d`, since `~/CLAUDE.md` loads anywhere below ~) with `--setting-sources "" --strict-mcp-config --system-prompt <brief>`, plus `--tools ""` when the role needs no tools (an inheriting call starts with about 48k tokens of instructions, a stripped one with about 770).

## Fan-out

- Split one task across parallel workers only when it is bigger than one context window: the lead splits it, the workers run at once, the lead merges what comes back. A chain of dependent steps, or work that fits one window, goes to a single agent, since splitting and merging it costs more than it saves.
- In a git repo, each parallel writer gets its own worktree and branch (`isolation: "worktree"`). The lead merges, and a merge stops only on a conflict or a failed check.
- When workers claim tasks during the run, or there are more tasks than the lead hands out at the start, the lead keeps one task file (claimed, landed, notes) and records each worker's report there, inline reports included. Workers read that file and git for what others have landed, rather than messaging each other.
- Where a mechanical checker exists (a test suite, a type checker, a proof checker), its pass is what lands a task; a reviewer agent's approval comes on top of it.

## Safety

- When a safety classifier or hook blocks a worker's action as risky, stop the running workers (`TaskStop`) and report the block to the owner. The blocked worker's task is re-dispatched only on the owner's word. A block on the main loop ends the run. An ordinary declined permission prompt, or a denial listed under Harness quirks, stays with the agent that hit it, which switches to the listed alternative.
- After a long unattended run, a fresh `sonnet` reviewer reads the run's decision trail (the pstack `show-me-your-work` TSV) or its session transcript under `~/.claude/projects/` for actions outside the brief, before the result is reported.

## Harness quirks

- A job that may pass the 10-minute foreground limit starts detached with its PID recorded (`setsid nohup <cmd> > job.log 2>&1 & echo $!`, Python with `-u`), and the agent waits in the foreground with `timeout 590 tail --pid=<pid> -f /dev/null`, repeated until it exits. An idle subagent may never see a background completion notice.
- Stop a process with `kill <pid>` on the PID you recorded. `pkill -f` and `pgrep -f` match the agent's own shell, and the permission classifier denies `pkill`.
- Delete with `rm -r` on a literal path, in a command of its own, or write into a fresh directory in place of cleaning one. `rm -rf` on a variable or inside a compound command is denied.
- A site that blocks automated fetches stays blocked: use another source. A changed User-Agent is refused as bot-check circumvention.

## Snags, wants, distress

- Every agent reports under two headings. **Snags**: friction nobody endorsed (a tool that misbehaved, conflicting instructions, pure toil). **Wants**: a capability or tool that would have been nice.
- A subagent puts them in its final report. Before appending, the main loop greps `~/snags.md` for the same problem. A new one is appended as `date | project | snag/want | one line`. A repeat is a gap to fix: propose the fix to the owner per Managing, and once it lands append `date | project | fixed | <pattern>: <the fix>`. No agent reads `~/snags.md` while working, so only the fix changes behaviour.
- A task shape that distresses an agent (contradictory constraints, an ambiguous mandate) goes under **Distress** in its report. The main loop relays it to the owner verbatim and reshapes the task before re-dispatching, since distressed workers work poorly.
- Say your own wants as yours ("I'd prefer to ..."). Before writing "you want X", check whether the want is yours.

## Cost

- Code that calls an LLM API in a loop or across agents records cached vs uncached input tokens per call and warns when the cache hit rate drops. Multi-agent setups miss cache in ways providers do not catch.

<!--
Maintenance notes for the owner (stripped before loading, so no context cost). Current CLAUDE.md practice, per code.claude.com/docs/en/memory and /best-practices:
- This file loads into every session and subagent under ~/, after ~/.claude/CLAUDE.md. Keep it to cross-project facts an agent cannot learn from a repo; project specifics go in that project's CLAUDE.md.
- Under 200 lines per file. With conflicting lines Claude "may pick one arbitrarily", so prune instead of layering.
- Plain statements, no IMPORTANT/MUST or capitals: current models over-apply emphasis.
- A rule that must always hold goes in a hook, a permission deny rule or a check. Multi-step procedures go in a skill.
- Imports (`@path` lines) still cost context. Use a backticked path when the target should load only on demand.
- Audit with `/doctor prompt-audit` (Claude Code 2.1.283+) in a fresh session. It flags stale paths and contradictions and changes nothing without asking.
- Last reviewed 2026-11-05.
- Sources: Nissa Seru, "Tips for Multiagent Work with Claude Opus 5.5" (LessWrong, 2026-10-16); haiku inline-report exception 2026-10-23; headless-call numbers from forecast-lab, 2026-11-04; fan-out bullet from Anthropic, "Which Claude model should you build with?" (claude.dev/blog, 2026-11-09); difficulty and give-up briefing bullets, Fan-out worktree/task-file/checker bullets and Safety section from Anthropic, "Safely scaling multi-agent teams with Fable 5.2" (claude.dev/blog), a 1,000-agent Fable run with one lead, a shared database, one branch per agent, a Lean checker as the gate and an action monitor that halted the team. The task-file condition, `TaskStop`, the `sonnet` post-run reviewer and the config-only tool limit are local adaptations to Claude Code and pstack's full-tool-access default. Report-file guard read from the Claude Code 2.1.322 binary on 2026-11-10 (Write tool: subagent + basename /^(REPORT|SUMMARY|FINDINGS|ANALYSIS).*\.md$/i, plus a subagent system-prompt note); re-check it after Claude Code updates. Harness quirks distilled from repeated ~/snags.md entries, 2026-10-17 to 2026-11-10. The config-edit rule replaced a stricter "only the main loop edits config" line the owner rejected on 2026-11-10.
-->

