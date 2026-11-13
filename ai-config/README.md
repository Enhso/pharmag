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
| `property-based-testing` | `skills/property-based-testing/` | The owner's installed agent skills | Not stated in installed copy | Reviewing `tests/PROPERTIES.md` | 2026-11-12 |
| `impeccable` | `skills/impeccable/`: the skill text and its reference files. Its launcher scripts and their data are not copied | [impeccable](https://github.com/pbakaus/impeccable), plugin cache version 4.9.0 | Apache 2.0, stated in the skill's front matter | The design pass for the page: the product record (`PRODUCT.md`), the surface brief under `.impeccable/`, the build checks, and the finish review | 2026-11-13 |
| `artifact-diagramming` | Not copied. The skill ships inside Claude Code and states no license that permits a copy | Claude Code, built in | Not stated | Layout rules for the system map in the presentation overview | 2026-11-12 |

The plugin registry lists pstack 0.9.135 as installed. The first session loaded the skills from the 0.9.134 cache folder, so the copies come from that folder. The session of 2026-11-12 loaded `poteto-mode` from the 0.9.136 cache folder; the copy here was not refreshed.

## MCP servers used

`mcp.json` in this folder holds the entry for each server, with credentials replaced by a variable reference.

| Server | Used for | First used |
|---|---|---|
| context7 | Current PydanticAI 2.0 docs, read before the architecture sketch. Current DeepEval docs, read before the eval step. Current uv and FastAPI docs, read by the builder subagent before the skeleton. Current bm25s and openai SDK docs, read by the builder subagent before the index. On 2026-11-12, current PydanticAI 2.67 docs, read by the planning session before the type contract and by the builders before the agents and the output validator. On 2026-11-13, current FastAPI docs on server-sent events, read by the builder before the stream endpoint | 2026-11-11 |

The sessions also used tools that are neither skills nor MCP servers: Claude Code's built-in web search, Docker, `curl`, and Claude Code's Artifact tool, which published the presentation overview as a private page.

## Agents and model routing

| File | What it is |
|---|---|
| `agents/builder.md` | Subagent that implements one scoped task and shows the proof |
| `agents/verifier.md` | Subagent that checks finished work against the plan |
| `pstack-models.md` | Which model and effort each pstack role runs on |

Five runs used the `builder` definition on 2026-11-11: the walking skeleton, the corpus parser, the search index, the four tools, and the retrieval eval script. The parser, the index, and the tools were each built in a separate git worktree and merged by the main session. Two runs ended before their report, one stopped by the session and one by a usage limit. In every case the main session read the diff and reran the checks before it merged. A web-fetch helper read one upstream license file. The `verifier` definition has not run.

Three more runs used it on 2026-11-12, each in its own worktree: the agents, grounding checks, and pipeline; the API wiring, page, config overrides, and README; and three fixes that the first live runs called for. The planning session wrote the type contract in `src/pharmag/models.py` first, so the first two could run at the same time, then reviewed each diff, reran the tests, merged, and ran the live checks.

One more run used the `builder` definition on 2026-11-13, in its own worktree: the streaming endpoint, its three new trace events, and their tests. The planning session read the diff, reran the tests, and merged. The same session wrote the page itself with the `impeccable` skill. Two agents that ship with the impeccable plugin then worked on it: `impeccable-finish-reviewer` reviewed the finished page from screenshots and returned eight fixes, and `impeccable-documenter` wrote `DESIGN.md` from the built page. A `verifier` run read the session's own trail for actions outside the brief. The plugin's agent definitions are not copied here.

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
| impeccable | 4.9.0 | Source of the `impeccable` skill above, used for the page's design pass on 2026-11-13. The registry listed 4.8.2 on 2026-11-11 |
| womm-skills | 07a94b5516d3 | Holds reusable specs that the session checks before coding against a library. On 2026-11-12 the planning session read the spec on JSON envelopes in LLM output and did not apply it, because PydanticAI returns typed output through a tool call. It passed the spec on patching module-level imports to the builder that wrote the API tests |
| claude-hud | 0.15.3 | Status line only |
| hegel-skill | 2.1.0 | Installed, not used |
| bootloops-protocols, bootloops-research | 1.0.0 | Installed, not used |
| code-review, pr-review-toolkit | 1.0.1 | Installed, not used |
| pyright-lsp, rust-analyzer-lsp, swift-lsp, typescript-lsp | 1.0.0 | Installed, not used |

## Session transcripts

`transcripts/` holds the terminal transcripts of the first three working sessions, published at the owner's request (DEC-036, DEC-039). The third is the morning session of 2026-11-13. An agent cleaned each file in place and left the line count unchanged. Every removal shows as a visible mark:

| Mark | What it replaces |
|---|---|
| `[redacted: proxy host]`, `[redacted: chat model]`, `[redacted: chat model detail]`, `[redacted: proxy detail]` | The values of the env file, and details of the key and of the proxy account |
| `[assignment text removed, p. N]` | A run of eight or more words shared with the assignment brief |
| `[redacted: private notes]` | Lines of the private interview notes that a tool call displayed |
| `[redacted: personal detail]` | A personal detail that is in no tracked file |
| `~` and "the owner" | The home path and the owner's name |

## Keeping this folder current

After a session uses a new skill or MCP server, copy it here and add its row. Regenerate the file count with `find ai-config -type f | wc -l`.
