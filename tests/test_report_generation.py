import json
import unittest
from pathlib import Path

from benchmarks.schema import contains_absolute_path
from tests.benchmark_test_support import get_smoke_result


class ReportGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = get_smoke_result(device_mode="cpu")

    def test_new_artifacts_do_not_include_absolute_paths(self) -> None:
        for filename in ("metadata.json", "results.csv", "report.md", "fidelity.md"):
            text = (self.result.artifact_dir / filename).read_text(encoding="utf-8")
            self.assertFalse(contains_absolute_path(text), msg=f"absolute path found in {filename}")
            if filename == "metadata.json":
                json.loads(text)
        for plot_name in ("throughput.png", "latency.png"):
            plot_path = self.result.artifact_dir / "plots" / plot_name
            if plot_path.exists():
                self.assertGreater(plot_path.stat().st_size, 0)

    def test_new_docs_do_not_include_absolute_paths(self) -> None:
        doc_paths = [
            Path("README.md"),
            Path("docs/benchmark_baseline_inventory.md"),
            Path("docs/benchmark_methodology.md"),
            Path("docs/backend_portability.md"),
            Path("docs/hip_porting_plan.md"),
            Path("docs/rocm_validation_matrix.md"),
            Path("docs/instinct_target_profile.md"),
            Path("docs/hipify_preflight_inventory.md"),
            Path("docs/rocm_manual_checklist.md"),
            Path("docs/native_backend_rocm_migration_plan.md"),
            Path("docs/ci_future_rocm_runner_note.md"),
            Path("docs/limitations_and_claims.md"),
            Path("docs/native_backend_portability_inventory.md"),
            Path("docs/portability_issue_backlog.md"),
            Path("docs/prd_completion_matrix.md"),
            Path("docs/portability_release_checklist.md"),
            Path("docs/results_interpretation_guide.md"),
            Path("docker/README.md"),
            Path("reports/portability/README.md"),
            Path("reports/portability/dashboard.md"),
        ]
        for path in doc_paths:
            text = path.read_text(encoding="utf-8")
            self.assertFalse(contains_absolute_path(text), msg=f"absolute path found in {path}")

    def test_new_artifact_metadata_uses_canonical_lane_and_extended_fields(self) -> None:
        lane_names = {row["lane"] for row in self.result.rows}
        self.assertEqual(lane_names, {"cpu_existing", "cpu_numpy", "torch_accelerated"})
        self.assertEqual(self.result.metadata["validation_scope"], "cpu_validated")
        self.assertEqual(self.result.metadata["claim_level"], "measured")
        env = self.result.metadata["env"]
        for key in (
            "accelerator_available",
            "accelerator_backend_kind",
            "accelerator_runtime_kind",
            "accelerator_device_display_name",
            "torch_build_tag",
            "cuda_version",
            "hip_version",
        ):
            self.assertIn(key, env)
        for capability in self.result.metadata["backend_capabilities"]:
            self.assertIn("backend_kind", capability)
            self.assertIn("runtime_kind", capability)
            self.assertIn("device_display_name", capability)
