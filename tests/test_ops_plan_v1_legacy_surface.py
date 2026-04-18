import unittest
from unittest import mock

from scripts.check_ops_plan_v1_env import collect_torch_runtime_check_records
from scripts.verify_ops_plan_v1_outputs import validate_ops_plan_accelerator_rows


class OpsPlanV1LegacySurfaceTests(unittest.TestCase):
    def test_collect_torch_runtime_check_records_uses_accelerator_labels(self) -> None:
        runtime = mock.Mock(
            accelerator_available=True,
            device_display_name="NVIDIA GeForce RTX 4060 Ti",
            reason="cuda-ready",
            backend_kind="cuda",
            runtime_kind="cuda",
            torch_build_tag="cu124",
            cuda_version="12.4",
            hip_version=None,
        )
        with (
            mock.patch("scripts.check_ops_plan_v1_env.check_python_module", return_value=(True, "ok")),
            mock.patch("scripts.check_ops_plan_v1_env.get_torch_runtime_metadata", return_value=runtime),
        ):
            records = collect_torch_runtime_check_records()

        names = [str(entry["name"]) for entry in records]
        self.assertEqual(
            names,
            ["python_module:torch", "accelerator:torch", "accelerator_runtime:torch"],
        )
        self.assertTrue(bool(records[1]["ok"]))
        self.assertIn("backend_kind=cuda", str(records[2]["detail"]))

    def test_collect_torch_runtime_check_records_handles_missing_torch(self) -> None:
        with mock.patch("scripts.check_ops_plan_v1_env.check_python_module", return_value=(False, "torch-unavailable")):
            records = collect_torch_runtime_check_records()

        self.assertEqual(str(records[1]["name"]), "accelerator:torch")
        self.assertFalse(bool(records[1]["ok"]))
        self.assertEqual(str(records[1]["detail"]), "torch-unavailable")

    def test_validate_ops_plan_accelerator_rows_accepts_legacy_alias(self) -> None:
        rows = [
            {"lane": "cpu_existing", "status": "pass", "selected_engine": "cpu"},
            {"lane": "cpu_numpy", "status": "pass", "selected_engine": "cpu"},
            {"lane": "gpu_pytorch", "status": "pass", "selected_engine": "gpu"},
            {"lane": "cpu_existing", "status": "pass", "selected_engine": "cpu"},
            {"lane": "cpu_numpy", "status": "pass", "selected_engine": "cpu"},
            {"lane": "gpu_pytorch", "status": "pass", "selected_engine": "gpu"},
            {"lane": "cpu_existing", "status": "pass", "selected_engine": "cpu"},
            {"lane": "cpu_numpy", "status": "pass", "selected_engine": "cpu"},
            {"lane": "gpu_pytorch", "status": "pass", "selected_engine": "gpu"},
        ]

        validate_ops_plan_accelerator_rows(rows)

    def test_validate_ops_plan_accelerator_rows_rejects_bad_accelerator_engine(self) -> None:
        rows = [
            {"lane": "cpu_existing", "status": "pass", "selected_engine": "cpu"},
            {"lane": "cpu_numpy", "status": "pass", "selected_engine": "cpu"},
            {"lane": "torch_accelerated", "status": "pass", "selected_engine": "cpu"},
            {"lane": "cpu_existing", "status": "pass", "selected_engine": "cpu"},
            {"lane": "cpu_numpy", "status": "pass", "selected_engine": "cpu"},
            {"lane": "torch_accelerated", "status": "pass", "selected_engine": "gpu"},
            {"lane": "cpu_existing", "status": "pass", "selected_engine": "cpu"},
            {"lane": "cpu_numpy", "status": "pass", "selected_engine": "cpu"},
            {"lane": "torch_accelerated", "status": "pass", "selected_engine": "gpu"},
        ]

        with self.assertRaisesRegex(AssertionError, "accelerator row passed without gpu engine selection"):
            validate_ops_plan_accelerator_rows(rows)
