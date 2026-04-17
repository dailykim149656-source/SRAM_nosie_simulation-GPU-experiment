# PRD Completion Matrix

This matrix ties the portability PRD acceptance criteria to concrete repository evidence.

## Acceptance Criteria Mapping

| Criterion | Status | Evidence |
|---|---|---|
| AC-1 | complete | `python -m benchmarks.cli --suite smoke` plus forced CPU smoke verification in `scripts/verify_portability_prd.py` |
| AC-2 | complete | `scripts/run_gpu_analytical_benchmark.py` wrapper plus standard artifact generation in `benchmarks/runner.py` |
| AC-3 | complete | forced CPU smoke and `tests/test_cpu_only_auto_smoke.py` |
| AC-4 | complete | `results.csv` lane set includes `cpu_existing`, `cpu_numpy`, `gpu_pytorch` |
| AC-5 | complete | `fidelity.md` thresholds and pair checks, plus `tests/test_fidelity_smoke.py` |
| AC-6 | complete | `benchmarks/schema.py` path sanitization checks and `tests/test_report_generation.py` |
| AC-7 | complete | `README.md` validated scope, limitations, CPU/CUDA usage, HIP plan link |
| AC-8 | complete | `docs/hip_porting_plan.md` |
| AC-9 | complete | `.github/workflows/cpu-smoke.yml` |

## Functional Requirement Coverage

| Requirement | Evidence |
|---|---|
| FR-1 Backend registry | `backends/registry.py` |
| FR-2 CPU baseline lane | `backends/cpu_existing.py`, `backends/cpu_numpy.py` |
| FR-3 GPU lane | `backends/cuda_lane.py` |
| FR-4 Portable torch lane | `backends/torch_portable.py` |
| FR-5 Benchmark suite CLI | `benchmarks/cli.py`, `benchmarks/run_suite.py` |
| FR-6 Artifact schema | `benchmarks/schema.py`, `benchmarks/validate.py` |
| FR-7 Environment metadata capture | `benchmarks/env.py` |
| FR-8 Fidelity validation | `benchmarks/runner.py`, `tests/test_fidelity_smoke.py` |
| FR-9 Report generation | `benchmarks/reports.py` |
| FR-10 Path sanitization | `benchmarks/schema.py`, `tests/test_report_generation.py` |
| FR-11 Requirements split | `requirements-base.txt`, `requirements-benchmark.txt`, `requirements-ui.txt`, `requirements-dev.txt` |
| FR-12 Docs bundle | `docs/benchmark_methodology.md`, `docs/backend_portability.md`, `docs/hip_porting_plan.md`, `docs/limitations_and_claims.md` |
| FR-13 CPU-only CI | `.github/workflows/cpu-smoke.yml` |

## Extended Scope Coverage

| Item | Evidence |
|---|---|
| HIP porting inventory | `docs/hip_porting_plan.md` |
| Linux quickstart | `README.md` |
| Optional plots | `benchmarks/reports.py` |
| Native portability inventory | `docs/native_backend_portability_inventory.md` |
| Optional Docker recipe | `Dockerfile.portability`, `docker/README.md` |
| Benchmark dashboard summary | `scripts/build_portability_dashboard.py`, `reports/portability/dashboard.md` |
| Release checklist | `docs/portability_release_checklist.md` |
| Issue backlog | `docs/portability_issue_backlog.md` |
| Changelog automation | `scripts/generate_portability_changelog.py`, `reports/portability/changelog.md` |
| Release workflow automation | `.github/workflows/portability-release.yml` |
| Minimal packaging metadata | `pyproject.toml` |
