# Portability Release Checklist

Use this checklist before publishing a portability-focused update of the repository.

## Code And Tests

- `python -m compileall backends benchmarks tests gpu_analytical_adapter.py execution_policy.py scripts/run_gpu_analytical_benchmark.py`
- `python -m unittest discover -s tests -p "test_*.py"`
- `python -m benchmarks.cli --suite smoke --device cpu`
- `python scripts/run_gpu_analytical_benchmark.py --cases 1024x64`

## Artifact Review

- Confirm `metadata.json`, `results.csv`, `report.md`, and `fidelity.md` are generated.
- Confirm fresh metadata includes `validation_scope`, `claim_level`, and accelerator runtime fields.
- Validate the latest artifact with `python -m benchmarks.validate --artifact-dir <artifact_dir>`.
- Regenerate dashboard with `python scripts/build_portability_dashboard.py`.
- Regenerate changelog with `python scripts/generate_portability_changelog.py`.
- Confirm new reports do not contain absolute local filesystem paths.
- If cutting a tagged release, use the `portability-v*` tag convention so the release workflow can publish the evidence bundle.

## Messaging Review

- README states what is validated today.
- README states what is not validated today.
- README includes CPU-only execution.
- README includes optional CUDA execution.
- README links to the HIP porting plan.
- README links to the ROCm validation and migration-note documents.

## Scope Honesty

- No AMD/ROCm validation claim without real hardware evidence.
- No `fully portable` language.
- No `AMD-validated`, `ROCm-ready`, or `HIP-complete` language.
- Any retained legacy snapshots with old paths are clearly treated as historical artifacts, not new portability outputs.
