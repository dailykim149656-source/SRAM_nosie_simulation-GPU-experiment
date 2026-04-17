import subprocess
import sys
import unittest

from tests.benchmark_test_support import get_smoke_result


class BenchmarkValidateCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = get_smoke_result(device_mode="cpu")

    def test_validate_cli_accepts_smoke_artifact(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "benchmarks.validate",
                "--artifact-dir",
                str(self.result.artifact_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stdout + completed.stderr)
        self.assertIn("validated artifact", completed.stdout)
