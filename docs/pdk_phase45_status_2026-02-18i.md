# Phase N4/N5 Status (`20260218i`)

## Snapshot

- Mixed-matrix coverage snapshot: `PASS=4`, `BLOCKED=1`, `HARD_FAIL=0`
- Runnable-PDK Gate B snapshot: `4/4 pass`
- Current stabilized tag: `n27_xyce_contractfix_20260309`
- Remaining blocker: `ihp_sg13g2` with PSP runtime/model compatibility issues

## N4 Status

Current state: `open`

Key outcome:
- `asap7` reached a runnable state in the mixed matrix
- `ihp_sg13g2` remains blocked

Public source files retained for this area:
- `spice_validation/run_spice_validation.py`
- `scripts/run_pdk_matrix.py`
- `spice_validation/configs/`
- `spice_validation/netlists/`

## N5 Status

Current state: `in_progress`

Representative public evidence retained in this repository:
- `docs/research_evidence_pack.md`
- `docs/phase23_pass_subset_execution_2026-03-09_n27_contractfix.md`
- `reports/gate_b_summary_n27_xyce_contractfix_20260309.md`
- `reports/matrix_parallel_benchmark_20260218c.md`
- `reports/raw_metric_span_audit_n27_xyce_contractfix_20260309.md`

## Claim Boundary

- `sky130`, `gf180mcu`: `foundry-pdk-pre-silicon`
- `freepdk45_openram`, `asap7`: `predictive-pdk-pre-silicon`
- current public snapshot remains `4/5 coverage` and `4/4 runnable Gate B pass`
- signoff replacement and silicon-correlation claims remain out of scope

## Public Snapshot Note

The full raw matrix reports and blocked-probe archives are not bundled in this trimmed public repository. This file summarizes the current state using the included representative evidence set.
