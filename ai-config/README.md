# AI coding configuration

This folder holds the AI coding configuration behind this repo, as the assignment requests. Claude Code does not load this folder. The files are copies for review, not live configuration. The one live file is `CLAUDE.md` at the repo root.

The work runs in Claude Code. The planning session uses Claude Fable 5.2 at the `xhigh` effort setting.

## Skills used

Each skill is a verbatim copy, taken on the day of first use.

| Skill | Copy | Origin | License | Used for | First used |
|---|---|---|---|---|---|
| `pstack:poteto-mode` | `skills/pstack/poteto-mode/` | [pstack-claude](https://github.com/michael-denyer/pstack-claude), plugin cache version 0.9.134 | MIT, see `skills/pstack/LICENSE` | Working style for the session. Its Investigation playbook shaped the scoping pass | 2026-11-11 |
| `pstack:unslop` | `skills/pstack/unslop/` | Same plugin | MIT | Prose rules for replies and docs | 2026-11-11 |
| `pstack:technical-writing` | `skills/pstack/technical-writing/` | Same plugin | MIT | Style for `docs/scoping.md` and `docs/decisions.md` | 2026-11-11 |
| `writing-for-agents` | `skills/mattpocock/writing-for-agents/` | The owner's user-level skills folder. Upstream is [mattpocock/skills](https://github.com/mattpocock/skills) | MIT, see `skills/mattpocock/LICENSE`. The upstream LICENSE file was read on 2026-11-11 | Wording of the root `CLAUDE.md` | 2026-11-11 |

The plugin registry lists pstack 0.9.135 as installed. The session loaded the skills from the 0.9.134 cache folder, so the copies come from that folder.

## MCP servers used

`mcp.json` in this folder holds the entry for each server, with credentials replaced by a variable reference.

| Server | Used for | First used |
|---|---|---|
| context7 | Current PydanticAI 2.0 docs, read before the architecture sketch. Current DeepEval docs, read before the eval step. Current uv and FastAPI docs, read by the builder subagent before the skeleton. Current bm25s and openai SDK docs, read by the builder subagent before the index | 2026-11-11 |

The sessions also used tools that are neither skills nor MCP servers: Claude Code's built-in web search, Docker, and `curl`.

## Agents and model routing

| File | What it is |
|---|---|
| `agents/builder.md` | Subagent that implements one scoped task and shows the proof |
| `agents/verifier.md` | Subagent that checks finished work against the plan |
| `pstack-models.md` | Which model and effort each pstack role runs on |

Five runs used the `builder` definition on 2026-11-11: the walking skeleton, the corpus parser, the search index, the four tools, and the retrieval eval script. The parser, the index, and the tools were each built in a separate git worktree and merged by the main session. Two runs ended before their report, one stopped by the session and one by a usage limit. In every case the main session read the diff and reran the checks before it merged. A web-fetch helper read one upstream license file. The `verifier` definition has not run.

## CLAUDE.md files

| File | What it is |
|---|---|
| `../CLAUDE.md` | Live project rules, written for this repo |
| `CLAUDE.global.md` | Copy of the owner's user-level `~/.claude/CLAUDE.md`, with the owner's name and home paths replaced |
| `CLAUDE.home.md` | Copy of the owner's `~/CLAUDE.md` (multi-agent rules), with the owner's name and home paths replaced |

## Plugins and hooks active in the sessions

Versions come from the Claude Code plugin registry on 2026-11-11. No plugin files are copied here except the skills listed above.

| Plugin | Version | Role in this project |
|---|---|---|
| pstack | 0.9.135 | Session-start hook that routes design tasks through `poteto-mode`. Source of three skills above |
| ponytail | 5.3.3 | Session-start hook that sets a "smallest complete change" working mode, level `full` |
| potion-hooks (local) | 1.0.0 | Hook that rejects commits carrying AI co-author lines |
| impeccable | 4.8.2 | Planned for the frontend design pass. Not used yet |
| womm-skills | 07a94b5516d3 | Holds reusable specs that the session checks before coding against a library. Not used yet |
| claude-hud | 0.15.3 | Status line only |
| hegel-skill | 2.1.0 | Installed, not used |
| bootloops-protocols, bootloops-research | 1.0.0 | Installed, not used |
| code-review, pr-review-toolkit | 1.0.1 | Installed, not used |
| pyright-lsp, rust-analyzer-lsp, swift-lsp, typescript-lsp | 1.0.0 | Installed, not used |

## Keeping this folder current

After a session uses a new skill or MCP server, copy it here and add its row. Regenerate the file count with `find ai-config -type f | wc -l`.
