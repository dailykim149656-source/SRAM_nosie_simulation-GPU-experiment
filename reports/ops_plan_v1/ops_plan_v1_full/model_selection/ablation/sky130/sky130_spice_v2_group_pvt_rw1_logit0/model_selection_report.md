# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:04:03.632293+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `spice_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
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
| 1 | MLP 2-layer (Perceptron Gate) | 0.896453 | 6.182323 | 0.000655 | 181 | yes |
| 2 | Random Forest | 0.887211 | 6.220209 | 0.342623 | 3868 | no |
| 3 | Polynomial (deg=2) | 0.884055 | 7.200751 | 0.004225 | 36 | no |
| 4 | Linear Regression | 0.878427 | 6.429427 | 0.001218 | 8 | no |
| 5 | Polynomial (deg=3) | 0.876932 | 6.603557 | 0.004748 | 120 | no |
| 6 | Gradient Boosting | 0.876836 | 6.271022 | 0.007893 | 1540 | no |
| 7 | SVR (RBF) | 0.741192 | 8.558880 | 0.007722 | 0 | no |
| 8 | MLP 3-layer (sklearn) | -1.209007 | 7.024066 | 0.007280 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.876453` (best Pareto R2 `0.896453` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001311` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.816239 | 6.545204 | 5.278709 |
| ber | 0.823387 | 0.001566 | 0.001284 |
| noise_sigma | 0.972808 | 0.002173 | 0.001563 |
| hold_snm | 0.816239 | 6.545204 | 5.278709 |
| read_snm | 0.832241 | 6.769393 | 5.458922 |
| write_margin | 0.757945 | 56.072516 | 43.441608 |
| read_fail | 0.999979 | 0.000000 | 0.000000 |
| write_fail | 0.999941 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 5.278709 | 4.180137 | 6.492715 |
| ber | 0.001284 | 0.001006 | 0.001523 |
| noise_sigma | 0.001563 | 0.001204 | 0.002036 |
| hold_snm | 5.278709 | 4.156311 | 6.449471 |
| read_snm | 5.458922 | 4.284719 | 6.555327 |
| write_margin | 43.441608 | 32.282899 | 58.160984 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 2.840403 |
| ber | -0.000970 |
| noise_sigma | 0.000972 |
| hold_snm | 2.840403 |
| read_snm | 2.973942 |
| write_margin | 17.962883 |
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
| ber | 0.166667 |
| read_fail | 0.166667 |
| write_fail | 0.000000 |
| noise_sigma | 0.133333 |

- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.
