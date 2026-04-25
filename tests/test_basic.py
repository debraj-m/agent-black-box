import sys
import tempfile
import unittest
from pathlib import Path

from agent_black_box.cli import (
    list_runs,
    record,
    redact,
    resolve_command,
    show_run,
    summarize_diff,
)


class AgentBlackBoxTests(unittest.TestCase):
    def test_records_command_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, outdir = record(
                [sys.executable, "-c", "print(123)"],
                directory,
                label="demo",
            )

            self.assertEqual(manifest["exit_code"], 0)
            self.assertTrue((outdir / "stdout.txt").exists())
            self.assertTrue((outdir / "stderr.txt").exists())
            self.assertTrue((outdir / "manifest.json").exists())
            self.assertTrue((outdir / "summary.md").exists())

    def test_redacts_common_secrets_from_output(self):
        with tempfile.TemporaryDirectory() as directory:
            secret = "sk-" + "a" * 24
            _, outdir = record(
                [sys.executable, "-c", f"print('{secret}')"],
                directory,
            )

            stdout = (outdir / "stdout.txt").read_text(encoding="utf-8")

            self.assertIn("[REDACTED]", stdout)
            self.assertNotIn(secret, stdout)

    def test_list_and_show_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, _ = record([sys.executable, "-c", "print('ok')"], directory)

            self.assertEqual(list_runs(directory)[0]["id"], manifest["id"])
            self.assertEqual(show_run(manifest["id"], directory)["id"], manifest["id"])

    def test_summarizes_diff(self):
        diff = "\n".join(
            [
                "diff --git a/a.py b/a.py",
                "--- a/a.py",
                "+++ b/a.py",
                "+print('hi')",
                "-print('bye')",
            ]
        )

        self.assertEqual(
            summarize_diff(diff),
            {"files_changed": 1, "lines_added": 1, "lines_removed": 1},
        )

    def test_redact_helper(self):
        self.assertEqual(redact("token=secret-value"), "[REDACTED]")

    def test_resolves_python_when_missing(self):
        resolved = resolve_command(["python", "-c", "print(1)"])

        self.assertEqual(resolved[-2:], ["-c", "print(1)"])


if __name__ == "__main__":
    unittest.main()
