# create-arca

**Mint your own ARCA harness for Claude Code, Codex CLI, or OpenCode in one command.**

```bash
uvx create-arca
```

Default runtime is Claude Code. Use `--runtime codex` or `--runtime opencode` to render the same ARCA identity, agents, skills and commands into the layout each tool actually discovers.

---

## What is ARCA?

Most "AI agents" are one big prompt. ARCA is a **system**: a main loop that does not execute domain work itself — it *routes* every task to the right specialist, runs it through blocking quality gates, and refuses to ship until the work is right.

- **59 specialist subagents** — ML, deep learning, RL, data, MLOps, RAG, cloud, Kubernetes, security/red-team, frontend, and the critics that police them.
- **Runtime-native layout** — Claude gets `CLAUDE.md`, `agents/`, `commands/`, `skills/`; Codex gets `AGENTS.md`, `config.toml`, `.agents/codex-agents/`, `.agents/skills/`, `prompts/`; OpenCode gets `AGENTS.md`, `opencode.json`, `.opencode/{agents,commands,skills}`.
- **Guardrails where the runtime supports them** — Claude keeps the full hook harness; Codex gets a base `config.toml` with destructive-command, commit and secret gates; OpenCode gets the portable agent/command/skill surface and a secret-free config.
- **Three pipelines** — a 14-cycle ML lifecycle, a CVE-first HTB/CTF flow, and a 9-phase AI red-team pipeline.
- **A character** — ARCA is a severe architect: dry, demanding, allergic to AI slop. You can keep that voice or dial it to "professional" — but it speaks as *you*, to *you*.

## Quickstart

```bash
# Render ARCA into ~/.claude (the default)
uvx create-arca

# Render ARCA into ~/.codex
uvx create-arca --runtime codex

# Render ARCA into ~/.config/opencode
uvx create-arca --runtime opencode

# ...or into a specific directory
uvx create-arca --runtime codex ./my-arca-codex
```

The wizard asks for your name, how the agent should address you, machine context, and **which domains you want** — so a data scientist doesn't get handed 14 penetration-testing agents.

## Runtime Outputs

| Runtime | Default destination | Main files |
|---|---|---|
| Claude Code | `~/.claude` | `CLAUDE.md`, `settings.json`, `agents/`, `commands/`, `skills/`, `hooks/` |
| Codex CLI | `~/.codex` | `AGENTS.md`, `config.toml`, `.agents/codex-agents/*.toml`, `.agents/skills/`, `prompts/`, `scripts/codex-hooks/` |
| OpenCode | `~/.config/opencode` | `AGENTS.md`, `opencode.json`, `.opencode/agents/`, `.opencode/commands/`, `.opencode/skills/`, `hooks/` |

## Profiles — install only what you need

| Profile    | Adds on top of `core`                                              |
|------------|-------------------------------------------------------------------|
| `core`     | Orchestration spine, critics, architecture, utility, quality *(always)* |
| `ml`       | Data, training, MLOps, RAG, evals + the 14-cycle ML pipeline       |
| `security` | HTB/CTF, AI red-team, bug bounty + HTB & ART pipelines             |
| `infra`    | Cloud, Kubernetes, serving, monitoring, networking                |
| `web`      | Frontend AI, API contracts, low-level systems                     |
| `all`      | Everything — all 59 agents and every pipeline                     |

## It's a living harness, not a one-shot scaffold

ARCA is shipped as a [Copier](https://copier.readthedocs.io) template. Claude uses the template layout directly, so `copier update` works there:

```bash
copier update
```

Codex and OpenCode use a CLI adaptation step after Copier render. For those runtimes, re-run `create-arca --runtime <runtime> <destination>` until runtime-native update support is promoted. Your answers are still rendered by Copier; the final directory layout is adapted by the CLI.

## How it works

`create-arca` renders a [Copier](https://copier.readthedocs.io) template (`template/`) with your answers. Claude receives that layout directly. Codex/OpenCode render into a temporary staging directory first, then the CLI maps the common ARCA content into runtime-native folders. Every personal detail is a variable, so you install *ARCA-the-architect* but the harness knows *you*.

## Security

ARCA was extracted from a private, personal harness. The published template is **derived**, never copied: a maintainer-side scrubber replaces every identity marker with a variable and strips hard secrets, and CI re-scans every commit — for leftover markers, for any bare UUID (org-id shape), and with `gitleaks` for generic secret material. A leak fails the build. See [`scrub/patterns.toml`](scrub/patterns.toml).

## Contributing

The agents, skills, hooks and commands live in `template/` as plain Markdown and Bash — edit those, never the engine. `scrub/` and `scripts/scrub.py` are maintainer tooling for re-deriving the template from upstream.

## License

MIT — see [LICENSE](LICENSE).
