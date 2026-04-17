import csv
import json
import unittest

from benchmarks.schema import validate_fidelity_records, validate_metadata, validate_result_rows
from tests.benchmark_test_support import get_smoke_result


class BenchmarkSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = get_smoke_result(device_mode="cpu")

    def test_artifact_files_exist_and_validate(self) -> None:
        metadata_path = self.result.artifact_dir / "metadata.json"
        results_path = self.result.artifact_dir / "results.csv"
        report_path = self.result.artifact_dir / "report.md"
        fidelity_path = self.result.artifact_dir / "fidelity.md"

        self.assertTrue(metadata_path.exists())
        self.assertTrue(results_path.exists())
        self.assertTrue(report_path.exists())
        self.assertTrue(fidelity_path.exists())

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        with results_path.open("r", encoding="utf-8", newline="") as fp:
            rows = list(csv.DictReader(fp))

        validate_metadata(metadata)
        validate_result_rows(rows)
        validate_fidelity_records(self.result.fidelity_records)
        artifact_files = set(metadata["artifact_files"])
        self.assertTrue({"metadata.json", "results.csv", "report.md", "fidelity.md"}.issubset(artifact_files))
        if "plots/throughput.png" in artifact_files:
            self.assertTrue((self.result.artifact_dir / "plots" / "throughput.png").exists())
            self.assertTrue((self.result.artifact_dir / "plots" / "latency.png").exists())
        self.assertEqual(len(rows), 3)
