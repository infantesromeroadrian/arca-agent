from __future__ import annotations

import unittest

from create_arca.cli import _parse_data, parse_args


class CreateArcaCliTest(unittest.TestCase):
    def test_help_exits_before_rendering(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            parse_args(["--help"])

        self.assertEqual(raised.exception.code, 0)

    def test_destination_defaults_to_claude_runtime(self) -> None:
        args = parse_args([])

        self.assertTrue(args.destination.endswith(".claude"))
        self.assertFalse(args.defaults)
        self.assertEqual(args.data, [])

    def test_destination_accepts_positional_path(self) -> None:
        args = parse_args(["/tmp/arca-out"])

        self.assertEqual(args.destination, "/tmp/arca-out")

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


if __name__ == "__main__":
    unittest.main()
