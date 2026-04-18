import unittest

from benchmarks.schema import normalize_fidelity_pair_name, normalize_lane_name


class BenchmarkAliasTests(unittest.TestCase):
    def test_legacy_lane_alias_normalizes(self) -> None:
        self.assertEqual(normalize_lane_name("gpu_pytorch"), "torch_accelerated")
        self.assertEqual(normalize_lane_name("torch_accelerated"), "torch_accelerated")

    def test_legacy_fidelity_alias_normalizes(self) -> None:
        self.assertEqual(
            normalize_fidelity_pair_name("cpu_existing_vs_gpu_pytorch"),
            "cpu_existing_vs_torch_accelerated",
        )
        self.assertEqual(
            normalize_fidelity_pair_name("cpu_existing_vs_torch_accelerated"),
            "cpu_existing_vs_torch_accelerated",
        )
