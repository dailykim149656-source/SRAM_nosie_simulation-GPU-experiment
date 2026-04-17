import unittest

from backends.registry import (
    get_backend_capabilities,
    get_gpu_backend_capability,
    get_runtime_backend_capabilities,
)


class BackendRegistryTests(unittest.TestCase):
    def test_cpu_lanes_are_always_available(self) -> None:
        capabilities = {cap.name: cap for cap in get_backend_capabilities(device_mode="auto")}
        self.assertTrue(capabilities["cpu_existing"].available)
        self.assertTrue(capabilities["cpu_numpy"].available)
        self.assertEqual(capabilities["cpu_existing"].device, "cpu")
        self.assertEqual(capabilities["cpu_numpy"].device, "cpu")

    def test_gpu_lane_can_be_forced_off_by_device_mode(self) -> None:
        gpu_capability = get_gpu_backend_capability(device_mode="cpu")
        self.assertFalse(gpu_capability.available)
        self.assertEqual(gpu_capability.reason, "device_mode_cpu")
        self.assertTrue(gpu_capability.fallback_allowed)

    def test_gpu_lane_reports_availability_or_known_skip_reason(self) -> None:
        gpu_capability = get_gpu_backend_capability(device_mode="auto")
        self.assertIn(gpu_capability.reason, {"cuda-ready", "torch-unavailable", "cuda-unavailable"})

    def test_runtime_capabilities_include_python_fallback(self) -> None:
        capabilities = {cap.name: cap for cap in get_runtime_backend_capabilities("simulate", native_module=None)}
        self.assertIn("simulate_python_fallback", capabilities)
        self.assertTrue(capabilities["simulate_python_fallback"].available)
        self.assertIn("simulate_torch_accelerated", capabilities)
