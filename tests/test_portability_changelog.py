import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from benchmarks.schema import contains_absolute_path


class PortabilityChangelogTests(unittest.TestCase):
    def test_changelog_script_builds_sanitized_markdown(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sram-changelog-") as tempdir:
            out_report = Path(tempdir) / "changelog.md"
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/generate_portability_changelog.py",
                    "--out-report",
                    str(out_report),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stdout + completed.stderr)
            text = out_report.read_text(encoding="utf-8")
            self.assertIn("Portability Changelog", text)
            self.assertIn("Validation Highlights", text)
            self.assertFalse(contains_absolute_path(text))
