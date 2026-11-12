# pharmag

A work-test submission. `docs/scoping.md` holds the assignment's constraints and the open decisions.

## Working agreement

- The owner decides. State each assumption and get the owner's confirmation before you act on it. Settle a fact by running a check, and a preference by asking.
- Choose the most performant current tool that fits the assignment's constraints, and read its current docs before you code against it.
- Log each owner decision in `docs/decisions.md` in the turn it is made, then add the evidence behind it to `defense-brief.md`.
- After you use a skill or an MCP server, copy it into `ai-config/` and add its row to `ai-config/README.md`.
- The main session plans, decides and verifies. Subagents do the mechanical work.

## Session handoff

`docs/handoff.md` holds the current state, what waits on the owner, and the next steps with their checks. Read it at the start of a session and rewrite it before you stop.

## Public repo

This repo is public. Write the LLM proxy hostname, key details and the assignment's own text only in `defense-brief.md`, which `.gitignore` excludes. Tracked files paraphrase the assignment and cite its page numbers.
