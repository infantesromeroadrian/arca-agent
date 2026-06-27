"""Thin CLI over Copier: `create-arca [DEST]` runs the wizard and renders ARCA.

We intentionally do not reimplement a prompt wizard — Copier already asks the
copier.yml questions, validates them, supports `copier update`, and handles the
template engine. This entry point just resolves where the template lives (the
installed package, or this repo in dev) and where to write (default ~/.claude),
then hands off. Keeping it thin means there is exactly one source of questions.
"""

from __future__ import annotations

import sys
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


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="create-arca",
        description="Render the ARCA Claude Code harness from the bundled Copier template.",
    )
    parser.add_argument(
        "destination",
        nargs="?",
        default=str(Path.home() / ".claude"),
        help="Target directory to render into. Defaults to ~/.claude.",
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
    dest = Path(args.destination).expanduser()
    data = _parse_data(args.data)

    try:
        from copier import run_copy
    except ImportError:
        console.print("[red]create-arca requires `copier`. Install with: uvx create-arca[/red]")
        return 1

    console.rule("[bold]create-arca[/bold]")
    console.print(f"Rendering ARCA into [cyan]{dest}[/cyan]\n")
    # No unsafe=True: the template ships no Copier _tasks, so no code execution
    # is needed. Re-enable explicitly — and document it in the README — only if
    # a future template adds tasks, so users always consent to running code.
    run_copy(src_path=str(_template_root()), dst_path=str(dest), data=data or None, defaults=args.defaults)
    console.print("\n[green]Done.[/green] Open Claude Code in your destination and meet ARCA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
