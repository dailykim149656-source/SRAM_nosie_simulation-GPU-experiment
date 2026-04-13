# Model Selection Report (Phase 2)

- Generated: 2026-04-13T13:54:48.422333+00:00
- Data source: `predictive-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_freepdk45_openram_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `freepdk45_openram`
- Target Source: `spice_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
- Split mode: `group_pvt`
- Target clip quantile: `0.01`
- Target normalize: `True`
- Target prob-logit: `True`
- Fail aux split (`read_fail/write_fail` dedicated heads): `False`
- Fail aux profile (requested -> resolved): `auto -> freepdk45_openram`
- R2 clip range: `[-10.0, 1.0]`
- Target importance (weighted aggregation): `snm=1.00, ber=1.50, noise_sigma=1.30, hold_snm=1.00, read_snm=1.20, write_margin=1.20, read_fail=2.00, write_fail=2.00`
- Samples: `27`
- Features: `temp_k, vdd, corner_ff, corner_ss, corner_tt`
- Cross-validation folds used: `5`

## Leaderboard

| Rank | Model | Mean R2 | Mean MAE | Infer ms/sample | Params | Pareto |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Polynomial (deg=3) | 0.535392 | 5.249523 | 0.009302 | 56 | yes |
| 2 | Gradient Boosting | 0.514144 | 5.144427 | 0.015021 | 1540 | no |
| 3 | MLP 2-layer (Perceptron Gate) | 0.508645 | 5.612777 | 0.001356 | 141 | yes |
| 4 | Polynomial (deg=2) | 0.505505 | 6.045429 | 0.008486 | 21 | no |
| 5 | Random Forest | 0.498170 | 5.763988 | 0.637812 | 2516 | no |
| 6 | Linear Regression | 0.488063 | 5.552925 | 0.002678 | 6 | no |
| 7 | MLP 3-layer (sklearn) | 0.454925 | 6.525797 | 0.016937 | 457 | no |
| 8 | SVR (RBF) | 0.402277 | 7.428918 | 0.011271 | 0 | no |

## Recommendation

- Recommended model: **Polynomial (deg=3)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.515392` (best Pareto R2 `0.535392` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.018603` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.796332 | 4.445977 | 3.565055 |
| ber | 0.797050 | 0.005903 | 0.004731 |
| noise_sigma | 0.876429 | 0.004637 | 0.003538 |
| hold_snm | 0.796332 | 4.445977 | 3.565055 |
| read_snm | 0.845041 | 4.880158 | 3.898737 |
| write_margin | 0.563676 | 47.717594 | 39.145308 |
| read_fail | 0.189167 | 0.000001 | 0.000001 |
| write_fail | -0.000000 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 3.560058 | 2.653885 | 4.727888 |
| ber | 0.004731 | 0.003500 | 0.006129 |
| noise_sigma | 0.003396 | 0.002177 | 0.004717 |
| hold_snm | 3.560058 | 2.473036 | 4.671212 |
| read_snm | 3.889391 | 2.666718 | 4.821786 |
| write_margin | 38.962114 | 29.605199 | 49.973808 |
| read_fail | 0.000001 | 0.000001 | 0.000001 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -2.703560 |
| ber | 0.003537 |
| noise_sigma | -0.002109 |
| hold_snm | -2.703560 |
| read_snm | -2.387864 |
| write_margin | -28.527538 |
| read_fail | 0.000001 |
| write_fail | 0.000001 |

## OOD Guardrails

- Training temp envelope: `233.15` to `398.15` K
- Training VDD envelope: `0.9000` to `1.1000` V
- Corners present: `ff, ss, tt`
- PDK IDs present: `freepdk45_openram`
- Worst-corner rows covered: `1`
- Rule-based OOD flags should trigger when a deployment sample falls outside this temp/VDD/corner envelope.

## Monotonic Sanity (Dataset)

| Target | Violation Rate |
|---|---:|
| ber | 0.333333 |
| read_fail | 0.055556 |
| write_fail | 0.000000 |
| noise_sigma | 0.222222 |

- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.
