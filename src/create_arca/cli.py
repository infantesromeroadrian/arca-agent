"""Runtime-aware CLI over Copier: `create-arca [DEST]` renders ARCA.

Claude remains the canonical Copier layout. Codex and OpenCode reuse the same
rendered ARCA content, then adapt it in a staging directory into the runtime
shape each tool actually discovers. That keeps one prompt/skill source while
avoiding a fake "multi-runtime" install that only changes the destination path.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

# In a published wheel the template ships beside the package; in this repo it is
# two levels up. Resolve the first location that actually holds a copier.yml.
_CANDIDATES = (
    Path(__file__).resolve().parent / "template_src",       # packaged
    Path(__file__).resolve().parents[2],                     # dev checkout (repo root)
)
_RUNTIME_DESTINATIONS = {
    "claude": Path.home() / ".claude",
    "codex": Path.home() / ".codex",
    "opencode": Path.home() / ".config" / "opencode",
}
_RUNTIME_CHOICES = tuple(_RUNTIME_DESTINATIONS)
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


def _template_root() -> Path:
    for candidate in _CANDIDATES:
        if (candidate / "copier.yml").is_file():
            return candidate
    raise SystemExit("create-arca: could not locate the ARCA template (no copier.yml found)")


def _parse_data(values: list[str]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for item in values:
        if "=" not in item:
            raise SystemExit(f"create-arca: --data expects KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit("create-arca: --data key cannot be empty")
        data[key] = value
    return data


def _destination_for(runtime: str, destination: str | None) -> Path:
    raw = Path(destination) if destination else _RUNTIME_DESTINATIONS[runtime]
    return raw.expanduser()


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _parse_agent_markdown(text: str) -> tuple[dict[str, str], str]:
    metadata: dict[str, str] = {}
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return metadata, text.strip()

    for line in match.group(1).splitlines():
        if not line.strip() or line.startswith((" ", "\t")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, text[match.end():].strip()


def _codex_agent_name(raw_name: str) -> str:
    name = raw_name.strip().lower().replace("-", "_")
    name = re.sub(r"[^a-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "arca_agent"


def _codex_agent_toml(path: Path) -> tuple[str, str]:
    metadata, body = _parse_agent_markdown(path.read_text(encoding="utf-8"))
    name = _codex_agent_name(metadata.get("name", path.stem))
    description = metadata.get("description", f"ARCA specialist agent: {name}.")
    instructions = (
        "Port generado desde la definición Markdown ARCA. Mantén el contrato del agente original y "
        "adapta cualquier referencia específica de Claude Code al runtime Codex cuando sea necesario.\n\n"
        f"{body}"
    ).strip()
    toml = "\n".join(
        [
            f"name = {_toml_string(name)}",
            f"description = {_toml_string(description)}",
            "",
            'model = "gpt-5.5"',
            'model_reasoning_effort = "high"',
            'sandbox_mode = "workspace-write"',
            "",
            f"developer_instructions = {_toml_string(instructions)}",
            "",
        ]
    )
    return name, toml


def _runtime_constitution(source: Path, runtime: str) -> str:
    text = source.read_text(encoding="utf-8")
    if runtime == "codex":
        replacements = {
            "Claude Code": "Codex CLI",
            "CLAUDE.md": "AGENTS.md",
            "~/.claude": "~/.codex",
            ".claude": ".codex",
            "agents/": ".agents/codex-agents/",
            "commands/": "prompts/",
        }
        header = """# ARCA — Codex runtime

Generado por `create-arca --runtime codex`.

Layout esperado por Codex:
- `AGENTS.md`: instrucciones raíz.
- `.agents/codex-agents/*.toml`: subagentes Codex.
- `.agents/skills/*/SKILL.md`: skills portables.
- `prompts/*.md`: slash prompts.
- `config.toml`: configuración base sin secretos.

## Constitución ARCA

"""
    elif runtime == "opencode":
        replacements = {
            "Claude Code": "OpenCode",
            "CLAUDE.md": "AGENTS.md",
            "~/.claude": "~/.config/opencode",
            ".claude": ".opencode",
            "agents/": ".opencode/agents/",
            "commands/": ".opencode/commands/",
        }
        header = """# ARCA — OpenCode runtime

Generado por `create-arca --runtime opencode`.

Layout esperado por OpenCode:
- `AGENTS.md`: instrucciones raíz.
- `.opencode/agents/*.md`: agentes.
- `.opencode/commands/*.md`: comandos.
- `.opencode/skills/*/SKILL.md`: skills portables.
- `opencode.json`: configuración base sin secretos.

## Constitución ARCA

"""
    else:
        raise ValueError(f"unsupported runtime: {runtime}")

    for old, new in replacements.items():
        text = text.replace(old, new)
    return header + text


def _move_path(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    shutil.move(str(src), str(dst))


def _write_codex_config(stage: Path, destination: Path) -> None:
    hook_dir = destination / "scripts" / "codex-hooks"
    config = f"""model = "gpt-5.5"
model_reasoning_effort = "high"
sandbox_mode = "workspace-write"

[features]
hooks = true

[agents]
max_threads = 6
max_depth = 2
job_max_runtime_seconds = 1800

[[hooks.PreToolUse]]
matcher = "^Bash$"

[[hooks.PreToolUse.hooks]]
type = "command"
command = {_toml_string(str(hook_dir / "block-dangerous.sh"))}
timeout = 5
statusMessage = "Validando comando bash"

[[hooks.PreToolUse]]
matcher = "^Bash$"

[[hooks.PreToolUse.hooks]]
type = "command"
command = {_toml_string(str(hook_dir / "git-commit-validator.sh"))}
timeout = 5
statusMessage = "Validando conventional commit"

[[hooks.PreToolUse]]
matcher = "^(Write|Edit|apply_patch)$"

[[hooks.PreToolUse.hooks]]
type = "command"
command = {_toml_string(str(hook_dir / "detect-secrets.sh"))}
timeout = 10
statusMessage = "Escaneando secrets"
"""
    (stage / "config.toml").write_text(config, encoding="utf-8")


def _write_opencode_config(stage: Path) -> None:
    config = {
        "$schema": "https://opencode.ai/config.json",
        "instructions": ["AGENTS.md"],
        "permission": {
            "bash": "allow",
            "edit": "allow",
            "webfetch": "allow",
        },
    }
    (stage / "opencode.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _adapt_codex(stage: Path, destination: Path) -> None:
    claude_md = stage / "CLAUDE.md"
    if claude_md.exists():
        (stage / "AGENTS.md").write_text(_runtime_constitution(claude_md, "codex"), encoding="utf-8")
        claude_md.unlink()

    settings = stage / "settings.json"
    if settings.exists():
        settings.unlink()

    _move_path(stage / "commands", stage / "prompts")
    _move_path(stage / "skills", stage / ".agents" / "skills")
    _move_path(stage / "hooks", stage / "scripts" / "codex-hooks")

    source_agents = stage / "agents"
    target_agents = stage / ".agents" / "codex-agents"
    if source_agents.exists():
        target_agents.mkdir(parents=True, exist_ok=True)
        for agent_file in sorted(source_agents.glob("*.md")):
            name, toml = _codex_agent_toml(agent_file)
            (target_agents / f"{name}.toml").write_text(toml, encoding="utf-8")
        shutil.rmtree(source_agents)

    _write_codex_config(stage, destination)


def _adapt_opencode(stage: Path) -> None:
    claude_md = stage / "CLAUDE.md"
    if claude_md.exists():
        (stage / "AGENTS.md").write_text(_runtime_constitution(claude_md, "opencode"), encoding="utf-8")
        claude_md.unlink()

    settings = stage / "settings.json"
    if settings.exists():
        settings.unlink()

    _move_path(stage / "agents", stage / ".opencode" / "agents")
    _move_path(stage / "commands", stage / ".opencode" / "commands")
    _move_path(stage / "skills", stage / ".opencode" / "skills")
    _write_opencode_config(stage)


def _copy_tree_contents(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="create-arca",
        description="Render the ARCA harness for Claude Code, Codex CLI, or OpenCode.",
    )
    parser.add_argument(
        "--runtime",
        choices=_RUNTIME_CHOICES,
        default="claude",
        help="Target agent runtime. Defaults to claude.",
    )
    parser.add_argument(
        "destination",
        nargs="?",
        default=None,
        help="Target directory. Defaults to ~/.claude, ~/.codex, or ~/.config/opencode by runtime.",
    )
    parser.add_argument(
        "--defaults",
        action="store_true",
        help="Run Copier with default answers, useful for CI or non-interactive installs.",
    )
    parser.add_argument(
        "-d",
        "--data",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Pass one Copier answer. Repeat for multiple values, e.g. -d profile=core.",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> Namespace:
    return build_parser().parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the ARCA generator. Optional first arg is the destination directory."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    dest = _destination_for(args.runtime, args.destination)
    data = _parse_data(args.data)

    try:
        from copier import run_copy
    except ImportError:
        console.print("[red]create-arca requires `copier`. Install with: uvx create-arca[/red]")
        return 1

    console.rule("[bold]create-arca[/bold]")
    console.print(f"Rendering ARCA for [bold]{args.runtime}[/bold] into [cyan]{dest}[/cyan]\n")
    # No unsafe=True: the template ships no Copier _tasks, so no code execution
    # is needed. Re-enable explicitly — and document it in the README — only if
    # a future template adds tasks, so users always consent to running code.
    if args.runtime == "claude":
        run_copy(
            src_path=str(_template_root()),
            dst_path=str(dest),
            data=data or None,
            defaults=args.defaults,
        )
    else:
        with tempfile.TemporaryDirectory(prefix=f"create-arca-{args.runtime}-") as tmp:
            stage = Path(tmp) / "render"
            run_copy(
                src_path=str(_template_root()),
                dst_path=str(stage),
                data=data or None,
                defaults=args.defaults,
                quiet=True,
            )
            if args.runtime == "codex":
                _adapt_codex(stage, dest)
            elif args.runtime == "opencode":
                _adapt_opencode(stage)
            else:  # argparse prevents this; keep a hard fail for direct callers.
                raise SystemExit(f"create-arca: unsupported runtime {args.runtime!r}")
            _copy_tree_contents(stage, dest)

    console.print(f"\n[green]Done.[/green] Open {args.runtime} in your destination and meet ARCA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
