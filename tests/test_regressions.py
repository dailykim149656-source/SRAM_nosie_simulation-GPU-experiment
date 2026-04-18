import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import main
import lifetime_service
import main_advanced
import native_backend
from reliability_model import LifetimePredictor, ReliabilityAwareSRAMCell
from workload_model import CircuitToSystemTranslator, WorkloadScenarios


class ReliabilityRegressionTests(unittest.TestCase):
    def test_stress_cell_matches_total_stress_time(self) -> None:
        two_step = ReliabilityAwareSRAMCell(width=1.0)
        two_step.stress_cell(temperature=330, vgs=1.0, vds=1.0, stress_duration=1e6)
        two_step.stress_cell(temperature=330, vgs=1.0, vds=1.0, stress_duration=1e6)

        single_step = ReliabilityAwareSRAMCell(width=1.0)
        single_step.stress_cell(temperature=330, vgs=1.0, vds=1.0, stress_duration=2e6)

        self.assertAlmostEqual(two_step.vth_nmos, single_step.vth_nmos, delta=1e-12)
        self.assertAlmostEqual(two_step.vth_pmos, single_step.vth_pmos, delta=1e-12)

    def test_lifetime_predictor_uses_duty_cycle_and_failure_rate(self) -> None:
        predictor = LifetimePredictor(num_cells=4, width=1.0)

        nominal = predictor.predict_array_lifetime(temperature=330, duty_cycle=1.0, failure_rate=0.01)
        low_duty = predictor.predict_array_lifetime(temperature=330, duty_cycle=0.25, failure_rate=0.01)
        relaxed = predictor.predict_array_lifetime(temperature=330, duty_cycle=1.0, failure_rate=0.10)

        self.assertAlmostEqual(low_duty["mean_lifetime"], nominal["mean_lifetime"] * 4.0, delta=1e-9)
        self.assertAlmostEqual(nominal["lifetime_at_failure_rate"], nominal["t_99pct"], delta=1e-12)
        self.assertAlmostEqual(relaxed["lifetime_at_failure_rate"], relaxed["t_90pct"], delta=1e-12)
        self.assertLess(nominal["lifetime_at_failure_rate"], relaxed["lifetime_at_failure_rate"])
        self.assertEqual(nominal["duty_cycle"], 1.0)
        self.assertEqual(relaxed["accepted_failure_rate"], 0.10)


class SimulationRegressionTests(unittest.TestCase):
    def test_main_array_bit_error_rate_uses_processed_cells(self) -> None:
        array = main.SRAMArray(num_cells=8)
        for cell in array.cells[:2]:
            cell.write_cell = lambda *args, **kwargs: True
            cell.read_cell = lambda *args, **kwargs: (0.0, 0.0)

        result = array.simulate(temperature=310, voltage=1.0, input_data=[1, 1], noise_enable=False)
        self.assertEqual(result["bit_errors"], 2)
        self.assertEqual(result["bit_error_rate"], 1.0)

    def test_main_advanced_array_bit_error_rate_uses_processed_cells(self) -> None:
        array = main_advanced.AdvancedSRAMArray(num_cells=8, width=1.0, length=1.0)
        for cell in array.cells[:2]:
            cell.write_cell = lambda *args, **kwargs: True
            cell.read_cell = lambda *args, **kwargs: (0.0, 0.0, {})

        result = array.simulate(
            temperature=310,
            voltage=1.0,
            input_data=[1, 1],
            noise_enable=False,
            variability_enable=False,
            monte_carlo_runs=1,
        )
        self.assertEqual(result["bit_errors"], 2)
        self.assertEqual(result["bit_error_rate"], 1.0)


class WorkloadRegressionTests(unittest.TestCase):
    def test_acceptability_matches_verdict(self) -> None:
        translator = CircuitToSystemTranslator(WorkloadScenarios.llama_7b_online())
        result = translator.translate_to_system_kpis(175, 0.70, 2.0, 25)

        self.assertTrue(result["is_acceptable"])
        self.assertTrue(result["verdict"].startswith("ACCEPTABLE"))


class NativeBackendRegressionTests(unittest.TestCase):
    def test_simulate_array_python_fallback_includes_runtime_capabilities(self) -> None:
        python_response = {"backend": "standard-python", "bit_error_rate": 0.0}

        with (
            mock.patch.object(native_backend, "_resolve_engine", return_value=("gpu", "forced_gpu", 1, True)),
            mock.patch.object(native_backend, "_json_call", return_value=None),
            mock.patch.object(native_backend, "_simulate_array_torch_gpu", return_value=None),
            mock.patch.object(native_backend, "_simulate_array_python", return_value=python_response),
        ):
            result = native_backend.simulate_array({"compute_mode": "gpu", "num_cells": 4})

        self.assertEqual(result["backend"], "standard-python")
        self.assertTrue(result["_exec"]["fallback"])
        capability_names = {cap["name"] for cap in result["_exec"]["capabilities"]}
        self.assertIn("simulate_python_fallback", capability_names)

    def test_predict_lifetime_uses_shared_torch_runtime_reason_labels(self) -> None:
        torch_runtime_response = {
            "backend": "torch-gpu",
            "accelerator_backend": "hip",
            "mean_lifetime": 10.0,
            "std_lifetime": 1.0,
            "min_lifetime": 9.0,
            "max_lifetime": 11.0,
            "t_90pct": 4.0,
            "t_99pct": 1.0,
            "failure_rate_fit": 42.0,
            "cell_lifetimes": [10.0, 10.0],
        }

        with (
            mock.patch.object(native_backend, "_resolve_engine", return_value=("gpu", "forced_gpu", 1, True)),
            mock.patch.object(native_backend, "_json_call", return_value=None),
            mock.patch.object(native_backend, "_predict_lifetime_torch_gpu", return_value=torch_runtime_response),
        ):
            result = native_backend.predict_lifetime({"compute_mode": "gpu", "failure_rate": 0.01})

        self.assertEqual(result["_exec"]["selected"], "gpu")
        self.assertIn("torch_rocm_backend", result["_exec"]["reason"])
        capability_names = {cap["name"] for cap in result["_exec"]["capabilities"]}
        self.assertIn("lifetime_torch_accelerated", capability_names)

    def test_predict_lifetime_adds_backend_label_for_native_response(self) -> None:
        native_response = {
            "mean_lifetime": 12.0,
            "std_lifetime": 1.0,
            "min_lifetime": 10.0,
            "max_lifetime": 14.0,
            "t_90pct": 4.0,
            "t_99pct": 1.0,
            "failure_rate_fit": 100.0,
            "cell_lifetimes": [12.0, 12.0],
        }

        with (
            mock.patch.object(native_backend, "_resolve_engine", return_value=("cpu", "forced_cpu", 1, False)),
            mock.patch.object(native_backend, "_json_call", return_value=native_response),
        ):
            result = native_backend.predict_lifetime({"compute_mode": "cpu", "duty_cycle": 0.5, "failure_rate": 0.01})

        self.assertEqual(result["backend"], "lifetime-native")
        self.assertEqual(result["duty_cycle"], 0.5)
        self.assertEqual(result["accepted_failure_rate"], 0.01)
        self.assertIn("lifetime_at_failure_rate", result)
        self.assertEqual(result["_exec"]["selected"], "cpu")


class LifetimeServiceRegressionTests(unittest.TestCase):
    def test_native_first_helper_uses_native_response_when_available(self) -> None:
        native_response = {
            "backend": "lifetime-native",
            "mean_lifetime": 24.0,
            "std_lifetime": 2.0,
            "min_lifetime": 20.0,
            "max_lifetime": 28.0,
            "t_90pct": 8.0,
            "t_99pct": 2.0,
            "lifetime_at_failure_rate": 2.0,
            "failure_rate_fit": 50.0,
            "cell_lifetimes": [24.0, 24.0],
            "duty_cycle": 0.5,
            "accepted_failure_rate": 0.01,
            "_exec": {"selected": "gpu", "reason": "forced_gpu", "fallback": False},
        }
        with mock.patch.object(lifetime_service, "native_predict_lifetime", return_value=native_response):
            result = lifetime_service.predict_lifetime_native_first(
                temperature=330,
                width=1.0,
                num_cells=4,
                duty_cycle=0.5,
                failure_rate=0.01,
            )

        self.assertEqual(result["backend"], "lifetime-native")
        self.assertEqual(result["runtime_engine"], "gpu")
        self.assertFalse(result["_exec"]["fallback"])

    def test_native_first_helper_falls_back_to_python_with_same_contract(self) -> None:
        with mock.patch.object(lifetime_service, "native_predict_lifetime", side_effect=RuntimeError("boom")):
            result = lifetime_service.predict_lifetime_native_first(
                temperature=330,
                width=1.0,
                num_cells=4,
                duty_cycle=0.5,
                failure_rate=0.01,
            )

        self.assertEqual(result["backend"], "lifetime-python-fallback")
        self.assertEqual(result["runtime_engine"], "cpu")
        self.assertTrue(result["_exec"]["fallback"])
        self.assertIn("lifetime_at_failure_rate", result)
        self.assertEqual(result["accepted_failure_rate"], 0.01)

    def test_runtime_summary_mentions_fallback_status(self) -> None:
        summary = lifetime_service.summarize_lifetime_runtime(
            {
                "backend": "lifetime-python-fallback",
                "runtime_engine": "cpu",
                "_exec": {"selected": "cpu", "reason": "native_failed:RuntimeError", "fallback": True},
            }
        )
        self.assertIn("backend=lifetime-python-fallback", summary)
        self.assertIn("fallback=yes", summary)

    def test_lifetime_result_text_includes_target_lifetime_and_runtime_source(self) -> None:
        result_text = lifetime_service.build_lifetime_result_text(
            temperature=330.0,
            vgs=1.0,
            vth=0.4,
            width=1.2,
            num_cells=16,
            duty_cycle=0.25,
            failure_rate=0.02,
            lifetime_result={
                "backend": "lifetime-native",
                "runtime_engine": "gpu",
                "mean_lifetime": 40.0,
                "std_lifetime": 2.0,
                "min_lifetime": 35.0,
                "max_lifetime": 45.0,
                "t_90pct": 10.0,
                "t_99pct": 3.0,
                "lifetime_at_failure_rate": 5.0,
                "failure_rate_fit": 77.0,
                "accepted_failure_rate": 0.02,
                "_exec": {"selected": "gpu", "reason": "forced_gpu", "fallback": False},
            },
            nbti_shift_10y_mv=12.5,
            hci_shift_10y_mv=4.0,
            total_shift_10y_mv=8.5,
        )
        self.assertIn("Duty Cycle:   0.25", result_text)
        self.assertIn("Fail Rate:    0.020", result_text)
        self.assertIn("Target Lifetime (98.0% survival): 5.00 years", result_text)
        self.assertIn("Backend:           lifetime-native", result_text)
        self.assertIn("Engine:            gpu", result_text)

    def test_lifetime_result_text_marks_fallback_source(self) -> None:
        result_text = lifetime_service.build_lifetime_result_text(
            temperature=330.0,
            vgs=1.0,
            vth=0.4,
            width=1.0,
            num_cells=8,
            duty_cycle=0.5,
            failure_rate=0.01,
            lifetime_result={
                "backend": "lifetime-python-fallback",
                "runtime_engine": "cpu",
                "mean_lifetime": 20.0,
                "std_lifetime": 1.0,
                "min_lifetime": 18.0,
                "max_lifetime": 22.0,
                "t_90pct": 6.0,
                "t_99pct": 2.0,
                "lifetime_at_failure_rate": 2.0,
                "failure_rate_fit": 90.0,
                "accepted_failure_rate": 0.01,
                "_exec": {"selected": "cpu", "reason": "native_failed:RuntimeError", "fallback": True},
            },
            nbti_shift_10y_mv=10.0,
            hci_shift_10y_mv=3.0,
            total_shift_10y_mv=7.0,
        )
        self.assertIn("Fallback Used:     True", result_text)
        self.assertIn("Summary:           backend=lifetime-python-fallback | engine=cpu | fallback=yes", result_text)


if __name__ == "__main__":
    unittest.main()
