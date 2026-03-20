# Open-Source Reliability Roadmap

## Goal

Strengthen the public SRAM surrogate flow from a useful pre-signoff screening engine into a more defensible pre-silicon accelerator using open-source resources only.

## Current Baseline

- open-source runtime coverage: `4/5 PDK`
- runnable Gate B snapshot: `4/4 pass`
- current stabilized tag: `n27_xyce_contractfix_20260309`
- remaining blocker: `ihp_sg13g2` PSP/runtime compatibility

Representative bundled references:
- `docs/phase23_pass_subset_execution_2026-03-09_n27_contractfix.md`
- `docs/pdk_phase45_status_2026-02-18i.md`
- `docs/research_evidence_pack.md`
- `reports/gate_b_summary_n27_xyce_contractfix_20260309.md`
- `reports/matrix_parallel_benchmark_20260218c.md`
- `reports/raw_metric_span_audit_n27_xyce_contractfix_20260309.md`

## Roadmap Themes

### 1. Raw Metric Quality

Focus:
- reduce dependence on fallback-driven SNM interpretation
- improve source-level metric quality for runnable PDKs

Primary code areas:
- `spice_validation/run_spice_validation.py`
- `spice_validation/netlists/`
- `spice_validation/README.md`

### 2. Determinism and Reproducibility

Focus:
- bound repeat-run drift
- make runtime and metric behavior reproducible enough for engineering use

Primary code areas:
- `scripts/run_pdk_matrix.py`
- `scripts/run_model_selection.py`
- `scripts/run_node_scaling.py`

### 3. Safer Surrogate Use

Focus:
- uncertainty-aware prediction
- better split policies
- clearer claim boundaries around what the surrogate does and does not replace

Primary code areas:
- `ml_benchmark.py`
- `scripts/run_model_selection.py`

## Success Criteria

The roadmap is moving in the right direction when:

1. raw SNM-like metrics are no longer mostly fallback-driven on runnable PDKs
2. repeat runs are deterministic or explicitly bounded
3. representative reports remain reproducible from scripts included in this repository
4. claim wording stays inside `pre-signoff acceleration` boundaries

## Public Snapshot Note

This public repository keeps only representative report snapshots and selected docs. It does not attempt to ship the full experimental archive.
