import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CpuOnlyAutoSmokeTests(unittest.TestCase):
    def test_auto_mode_succeeds_when_gpu_is_forced_off(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sram-cpu-auto-") as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            env = os.environ.copy()
            env["SRAM_FORCE_CPU"] = "1"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "benchmarks.cli",
                    "--suite",
                    "smoke",
                    "--artifact-root",
                    str(artifact_root),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stdout + completed.stderr)

            artifact_dirs = [path for path in artifact_root.iterdir() if path.is_dir()]
            self.assertEqual(len(artifact_dirs), 1)
            results_path = artifact_dirs[0] / "results.csv"
            with results_path.open("r", encoding="utf-8", newline="") as fp:
                rows = list(csv.DictReader(fp))

            gpu_rows = [row for row in rows if row["lane"] == "gpu_pytorch"]
            self.assertEqual(len(gpu_rows), 1)
            self.assertIn(gpu_rows[0]["status"], {"skipped", "unsupported"})
