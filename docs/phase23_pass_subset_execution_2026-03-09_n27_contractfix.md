# Phase 2/3 Execution Status (`n27_xyce_contractfix_20260309`)

## Scope

- Source matrix family: `matrix_fullpvt_xyce_mixed`
- Stabilized evidence tag: `matrix_fullpvt_xyce_mixed_contractfix_20260309`
- Runnable PDK subset:
  - `sky130`
  - `gf180mcu`
  - `freepdk45_openram`
  - `asap7`
- Blocked PDK:
  - `ihp_sg13g2`

## Stabilized Results

### Contract Source Selection

- `sky130`: primary SNM contract source switched to `spice_read_snm_mv_raw`
- `freepdk45_openram`: primary SNM contract source switched to `spice_read_snm_mv_raw`
- `gf180mcu`: primary SNM contract source remained `spice_snm_mv_raw`
- `asap7`: primary SNM contract source remained `spice_snm_mv_raw`

### Representative Model Selection Snapshot

Bundled public example:
- `reports/pdk_phase2_n27_xyce_contractfix_20260309/model_selection_sky130_spice_v2_n27_xyce_contractfix_20260309.md`

Representative recommendation in the bundled snapshot:
- `sky130`: `MLP 2-layer (Perceptron Gate)`

### Gate B

- bundled summary: `reports/gate_b_summary_n27_xyce_contractfix_20260309.md`
- runnable subset result: `4/4 pass`

### Node Scaling

- bundled summary: `reports/node_scaling_report_n27_xyce_20260218.md`
- retained as a representative proxy-node trend snapshot

## Interpretation

- `n27_xyce_20260218` remains the historical failing baseline
- `n27_xyce_contractfix_20260309` is the current stabilized evidence tag
- this supports `pre-silicon`, `pre-signoff acceleration`
- this does not support full 5/5 closure or signoff-replacement claims

## Public Snapshot Note

Only representative public snapshots are bundled here. The full Phase 2 family, raw mixed-matrix reruns, and large report archives are intentionally excluded from this public repository.
