import csv
import json
import tempfile
import unittest
from pathlib import Path

import gpu_analytical_adapter
from benchmarks.validate import validate_artifact_dir
from tests.benchmark_test_support import get_smoke_result


class BenchmarkValidateSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fresh_result = get_smoke_result(device_mode="cpu")

    def test_validate_artifact_dir_accepts_fresh_extended_artifact(self) -> None:
        validate_artifact_dir(self.fresh_result.artifact_dir)

    def test_validate_artifact_dir_accepts_legacy_minimal_artifact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sram-legacy-artifact-") as tempdir:
            artifact_dir = Path(tempdir)
            metadata = {
                "suite": "smoke",
                "device_mode": "cpu",
                "seed": 20260310,
                "artifact_files": ["metadata.json", "results.csv", "report.md", "fidelity.md"],
                "backend_capabilities": [
                    {
                        "name": "cpu_existing",
                        "device": "cpu",
                        "available": True,
                        "reason": "always-available",
                        "fallback_allowed": False,
                        "precision": "float64",
                    },
                    {
                        "name": "cpu_numpy",
                        "device": "cpu",
                        "available": True,
                        "reason": "always-available",
                        "fallback_allowed": False,
                        "precision": "float64",
                    },
                    {
                        "name": "gpu_pytorch",
                        "device": "cuda",
                        "available": False,
                        "reason": "device_mode_cpu",
                        "fallback_allowed": True,
                        "precision": "float32",
                    },
                ],
                "cases": [{"case_id": "1024x64", "n_samples": 1024, "variability_samples": 64}],
                "env": {
                    "python_version": "3.11.9",
                    "platform": "test-platform",
                    "implementation": "CPython",
                    "executable_name": "python",
                    "argv0": "python",
                    "torch_version": "2.6.0+cu124",
                },
            }
            (artifact_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            result_rows = [
                {
                    "case_id": "1024x64",
                    "lane": "cpu_existing",
                    "status": "pass",
                    "selected_engine": "cpu",
                    "selection_reason": "forced_cpu",
                    "work_size": "65536",
                    "gpu_detected": "False",
                    "device_name": "cpu",
                    "wall_clock_sec": "0.1",
                    "throughput_samples_per_sec": "10240.0",
                    "mean_prediction": "0.05",
                },
                {
                    "case_id": "1024x64",
                    "lane": "cpu_numpy",
                    "status": "pass",
                    "selected_engine": "cpu",
                    "selection_reason": "forced_cpu",
                    "work_size": "65536",
                    "gpu_detected": "False",
                    "device_name": "cpu",
                    "wall_clock_sec": "0.1",
                    "throughput_samples_per_sec": "10240.0",
                    "mean_prediction": "0.05",
                },
                {
                    "case_id": "1024x64",
                    "lane": "gpu_pytorch",
                    "status": "skipped",
                    "selected_engine": "cpu",
                    "selection_reason": "forced_cpu",
                    "work_size": "65536",
                    "gpu_detected": "False",
                    "device_name": "device_mode_cpu",
                    "wall_clock_sec": "0.0",
                    "throughput_samples_per_sec": "0.0",
                    "mean_prediction": "0.0",
                },
            ]
            with (artifact_dir / "results.csv").open("w", encoding="utf-8", newline="") as fp:
                writer = csv.DictWriter(fp, fieldnames=list(result_rows[0].keys()))
                writer.writeheader()
                writer.writerows(result_rows)

            (artifact_dir / "report.md").write_text("# Legacy Report\n", encoding="utf-8")
            (artifact_dir / "fidelity.md").write_text(
                "\n".join(
                    [
                        "# Legacy Fidelity",
                        "",
                        "| Pair | Status | Max Abs Delta | Mean Abs Delta | RMSE | Threshold Max | Threshold Mean |",
                        "|---|---|---:|---:|---:|---:|---:|",
                        "| cpu_existing_vs_gpu_pytorch | skipped | 0.0 | 0.0 | 0.0 | 1e-3 | 1e-4 |",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            validate_artifact_dir(artifact_dir)

    def test_validate_artifact_dir_rejects_malformed_fresh_artifact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sram-malformed-artifact-") as tempdir:
            artifact_dir = Path(tempdir)
            for source_name in ("metadata.json", "results.csv", "report.md", "fidelity.md"):
                source_path = self.fresh_result.artifact_dir / source_name
                target_path = artifact_dir / source_name
                target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

            metadata_path = artifact_dir / "metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata.pop("validation_scope", None)
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "fresh artifact missing top-level extended metadata keys"):
                validate_artifact_dir(artifact_dir)

    def test_compatibility_facade_exports_runtime_helpers(self) -> None:
        self.assertIn("get_torch_runtime_metadata", gpu_analytical_adapter.__all__)
        self.assertIn("resolve_torch_runtime", gpu_analytical_adapter.__all__)
        self.assertTrue(callable(gpu_analytical_adapter.get_torch_runtime_metadata))
        self.assertTrue(callable(gpu_analytical_adapter.resolve_torch_runtime))
