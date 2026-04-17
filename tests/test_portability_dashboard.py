import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from benchmarks.runner import run_suite
from benchmarks.schema import contains_absolute_path


class PortabilityDashboardTests(unittest.TestCase):
    def test_dashboard_script_builds_sanitized_markdown(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sram-dashboard-") as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            out_report = Path(tempdir) / "dashboard.md"
            run_suite(suite="smoke", device_mode="cpu", artifact_root=artifact_root, seed=20260310)
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/build_portability_dashboard.py",
                    "--artifact-root",
                    str(artifact_root),
                    "--out-report",
                    str(out_report),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stdout + completed.stderr)
            text = out_report.read_text(encoding="utf-8")
            self.assertIn("Portability Benchmark Dashboard", text)
            self.assertFalse(contains_absolute_path(text))
