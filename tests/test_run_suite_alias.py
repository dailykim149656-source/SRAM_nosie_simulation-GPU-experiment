import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class RunSuiteAliasTests(unittest.TestCase):
    def test_run_suite_module_alias_executes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sram-run-suite-") as tempdir:
            artifact_root = Path(tempdir) / "artifacts"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "benchmarks.run_suite",
                    "--suite",
                    "smoke",
                    "--device",
                    "cpu",
                    "--artifact-root",
                    str(artifact_root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stdout + completed.stderr)
            artifact_dirs = [path for path in artifact_root.iterdir() if path.is_dir()]
            self.assertEqual(len(artifact_dirs), 1)
