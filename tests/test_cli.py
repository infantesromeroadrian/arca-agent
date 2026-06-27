from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from create_arca.cli import _codex_agent_toml, _destination_for, _parse_data, parse_args


class CreateArcaCliTest(unittest.TestCase):
    def test_help_exits_before_rendering(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            parse_args(["--help"])

        self.assertEqual(raised.exception.code, 0)

    def test_destination_defaults_to_claude_runtime(self) -> None:
        args = parse_args([])

        self.assertEqual(args.runtime, "claude")
        self.assertIsNone(args.destination)
        self.assertFalse(args.defaults)
        self.assertEqual(args.data, [])
        self.assertTrue(str(_destination_for(args.runtime, args.destination)).endswith(".claude"))

    def test_destination_defaults_to_codex_runtime(self) -> None:
        args = parse_args(["--runtime", "codex"])

        self.assertEqual(args.runtime, "codex")
        self.assertTrue(str(_destination_for(args.runtime, args.destination)).endswith(".codex"))

    def test_destination_defaults_to_opencode_runtime(self) -> None:
        args = parse_args(["--runtime", "opencode"])

        self.assertEqual(args.runtime, "opencode")
        self.assertTrue(str(_destination_for(args.runtime, args.destination)).endswith(".config/opencode"))

    def test_destination_accepts_positional_path(self) -> None:
        args = parse_args(["/tmp/arca-out"])

        self.assertEqual(args.destination, "/tmp/arca-out")
        self.assertEqual(_destination_for(args.runtime, args.destination), Path("/tmp/arca-out"))

    def test_parse_data_repeated_key_values(self) -> None:
        data = _parse_data(["profile=core", "user_name=CI User", "enable_llm_judge=false"])

        self.assertEqual(
            data,
            {
                "profile": "core",
                "user_name": "CI User",
                "enable_llm_judge": "false",
            },
        )

    def test_parse_data_rejects_malformed_values(self) -> None:
        with self.assertRaises(SystemExit):
            _parse_data(["profile"])

    def test_codex_agent_toml_converts_markdown_frontmatter(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "code-critic.md"
            path.write_text(
                """---
name: code-critic
description: Quality gate.
model: opus
tools: Bash, Read
---

## Contract

Break weak code.
""",
                encoding="utf-8",
            )

            name, toml = _codex_agent_toml(path)

        self.assertEqual(name, "code_critic")
        self.assertIn('name = "code_critic"', toml)
        self.assertIn('description = "Quality gate."', toml)
        self.assertIn('model = "gpt-5.5"', toml)
        self.assertIn("Break weak code.", toml)


if __name__ == "__main__":
    unittest.main()
