# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:10:13.537296+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `delta_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
- Split mode: `group_pvt`
- Target clip quantile: `0.01`
- Target normalize: `True`
- Target prob-logit: `False`
- Fail aux split (`read_fail/write_fail` dedicated heads): `False`
- Fail aux profile (requested -> resolved): `sky130 -> sky130`
- R2 clip range: `[-10.0, 1.0]`
- Target importance (weighted aggregation): `snm=1.00, ber=1.50, noise_sigma=1.30, hold_snm=1.00, read_snm=1.20, write_margin=1.20, read_fail=2.00, write_fail=2.00`
- Samples: `45`
- Features: `temp_k, vdd, corner_ff, corner_fs, corner_sf, corner_ss, corner_tt`
- Cross-validation folds used: `5`

## Leaderboard

| Rank | Model | Mean R2 | Mean MAE | Infer ms/sample | Params | Pareto |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Linear Regression | 0.122491 | 6.290072 | 0.001537 | 8 | yes |
| 2 | SVR (RBF) | 0.110902 | 4.883607 | 0.006344 | 0 | no |
| 3 | MLP 2-layer (Perceptron Gate) | 0.107581 | 6.187576 | 0.000696 | 181 | yes |
| 4 | Polynomial (deg=2) | 0.089131 | 6.267189 | 0.005770 | 36 | no |
| 5 | Random Forest | -0.104320 | 6.125893 | 0.378852 | 4382 | no |
| 6 | Polynomial (deg=3) | -0.156173 | 5.749474 | 0.012244 | 120 | no |
| 7 | Gradient Boosting | -0.390842 | 6.248260 | 0.009697 | 1540 | no |
| 8 | MLP 3-layer (sklearn) | -1.690143 | 4.860927 | 0.007366 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.102491` (best Pareto R2 `0.122491` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001392` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.067938 | 6.106607 | 4.813165 |
| ber | 0.075882 | 0.001480 | 0.001159 |
| noise_sigma | -0.537114 | 0.001954 | 0.001420 |
| hold_snm | 0.067938 | 6.106607 | 4.813165 |
| read_snm | 0.070714 | 6.316378 | 4.975512 |
| write_margin | -2.026023 | 58.588924 | 44.750265 |
| read_fail | 0.999977 | 0.000000 | 0.000000 |
| write_fail | 0.999934 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 4.813165 | 3.763972 | 5.826757 |
| ber | 0.001159 | 0.000902 | 0.001432 |
| noise_sigma | 0.001420 | 0.001041 | 0.001871 |
| hold_snm | 4.813165 | 3.659134 | 5.936812 |
| read_snm | 4.975512 | 3.865755 | 5.968423 |
| write_margin | 44.750265 | 33.863606 | 58.795826 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -3.456767 |
| ber | 0.001145 |
| noise_sigma | 0.000905 |
| hold_snm | -3.456767 |
| read_snm | -3.549631 |
| write_margin | -32.523557 |
| read_fail | 0.000000 |
| write_fail | 0.000000 |

## OOD Guardrails

- Training temp envelope: `233.15` to `373.15` K
- Training VDD envelope: `1.6000` to `1.9500` V
- Corners present: `ff, fs, sf, ss, tt`
- PDK IDs present: `sky130`
- Worst-corner rows covered: `1`
- Rule-based OOD flags should trigger when a deployment sample falls outside this temp/VDD/corner envelope.

## Monotonic Sanity (Dataset)

| Target | Violation Rate |
|---|---:|
| ber | 0.400000 |
| read_fail | 0.466667 |
| write_fail | 0.000000 |
| noise_sigma | 0.433333 |

- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.
