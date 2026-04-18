import unittest

from tests.benchmark_test_support import get_smoke_result


class FidelitySmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = get_smoke_result(device_mode="cpu")
        cls.records = {record["pair"]: record for record in cls.result.fidelity_records}

    def test_cpu_numpy_fidelity_passes_threshold(self) -> None:
        record = self.records["cpu_existing_vs_cpu_numpy"]
        self.assertEqual(record["status"], "pass")
        self.assertLessEqual(record["max_abs_delta"], record["threshold_max_abs_delta"])
        self.assertLessEqual(record["mean_abs_delta"], record["threshold_mean_abs_delta"])

    def test_gpu_fidelity_is_skipped_when_suite_is_forced_cpu(self) -> None:
        record = self.records["cpu_existing_vs_torch_accelerated"]
        self.assertEqual(record["status"], "skipped")
        self.assertIn("device_mode_cpu", str(record.get("detail", "")))
