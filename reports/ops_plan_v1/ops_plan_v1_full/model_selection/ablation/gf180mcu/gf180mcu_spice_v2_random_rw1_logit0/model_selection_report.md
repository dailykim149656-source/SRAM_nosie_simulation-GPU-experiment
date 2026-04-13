# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:11:23.454180+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `spice_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
- Split mode: `random`
- Target clip quantile: `0.01`
- Target normalize: `True`
- Target prob-logit: `False`
- Fail aux split (`read_fail/write_fail` dedicated heads): `False`
- Fail aux profile (requested -> resolved): `gf180mcu -> gf180mcu`
- R2 clip range: `[-10.0, 1.0]`
- Target importance (weighted aggregation): `snm=1.00, ber=1.50, noise_sigma=1.30, hold_snm=1.00, read_snm=1.20, write_margin=1.20, read_fail=2.00, write_fail=2.00`
- Samples: `45`
- Features: `temp_k, vdd, corner_ff, corner_fs, corner_sf, corner_ss, corner_tt`
- Cross-validation folds used: `5`

## Leaderboard

| Rank | Model | Mean R2 | Mean MAE | Infer ms/sample | Params | Pareto |
|---:|---|---:|---:|---:|---:|---:|
| 1 | MLP 2-layer (Perceptron Gate) | 0.774320 | 10.295264 | 0.000795 | 181 | yes |
| 2 | Random Forest | 0.744167 | 10.246927 | 0.338220 | 3970 | no |
| 3 | Linear Regression | 0.739862 | 10.459406 | 0.001470 | 8 | no |
| 4 | Polynomial (deg=2) | 0.709730 | 11.522999 | 0.004599 | 36 | no |
| 5 | Gradient Boosting | 0.618483 | 13.139574 | 0.007997 | 1540 | no |
| 6 | Polynomial (deg=3) | 0.579937 | 12.881707 | 0.004643 | 120 | no |
| 7 | SVR (RBF) | 0.357421 | 14.205169 | 0.005983 | 0 | no |
| 8 | MLP 3-layer (sklearn) | -1.239873 | 11.112485 | 0.008579 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.754320` (best Pareto R2 `0.774320` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001590` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.618404 | 8.356954 | 7.411396 |
| ber | 0.627499 | 0.002253 | 0.002012 |
| noise_sigma | 0.966259 | 0.002470 | 0.001798 |
| hold_snm | 0.618404 | 8.356954 | 7.411396 |
| read_snm | 0.641491 | 8.993635 | 8.184924 |
| write_margin | 0.390421 | 86.033734 | 75.547419 |
| read_fail | 0.999983 | 0.000000 | 0.000000 |
| write_fail | 0.999966 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 7.411396 | 6.366223 | 8.558583 |
| ber | 0.002012 | 0.001647 | 0.002344 |
| noise_sigma | 0.001798 | 0.001346 | 0.002283 |
| hold_snm | 7.411396 | 6.118690 | 8.534263 |
| read_snm | 8.184924 | 6.986742 | 9.236113 |
| write_margin | 75.547419 | 65.590614 | 88.718599 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -5.979529 |
| ber | 0.001431 |
| noise_sigma | 0.000315 |
| hold_snm | -5.979529 |
| read_snm | 5.373977 |
| write_margin | 30.668652 |
| read_fail | 0.000000 |
| write_fail | 0.000000 |

## OOD Guardrails

- Training temp envelope: `233.15` to `398.15` K
- Training VDD envelope: `1.6200` to `1.9800` V
- Corners present: `ff, fs, sf, ss, tt`
- PDK IDs present: `gf180mcu`
- Worst-corner rows covered: `1`
- Rule-based OOD flags should trigger when a deployment sample falls outside this temp/VDD/corner envelope.

## Monotonic Sanity (Dataset)

| Target | Violation Rate |
|---|---:|
| ber | 0.300000 |
| read_fail | 0.266667 |
| write_fail | 0.000000 |
| noise_sigma | 0.266667 |

- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.
