# Model Selection Report (Phase 2)

- Generated: 2026-04-13T13:55:58.955197+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `spice_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
- Split mode: `random`
- Target clip quantile: `0.01`
- Target normalize: `True`
- Target prob-logit: `True`
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
| 1 | Random Forest | 0.678402 | 6.213308 | 0.398540 | 3676 | yes |
| 2 | MLP 3-layer (sklearn) | 0.645861 | 8.126238 | 0.008228 | 505 | yes |
| 3 | MLP 2-layer (Perceptron Gate) | 0.639751 | 7.089530 | 0.000846 | 181 | yes |
| 4 | Polynomial (deg=3) | 0.623100 | 6.990466 | 0.006005 | 120 | no |
| 5 | Linear Regression | 0.591843 | 7.761446 | 0.001563 | 8 | no |
| 6 | Polynomial (deg=2) | 0.591073 | 8.833454 | 0.005378 | 36 | no |
| 7 | Gradient Boosting | 0.568427 | 7.832004 | 0.008672 | 1540 | no |
| 8 | SVR (RBF) | 0.371500 | 10.048004 | 0.006476 | 0 | no |

## Recommendation

- Recommended model: **Random Forest**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.658402` (best Pareto R2 `0.678402` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.797080` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.744915 | 6.936077 | 5.578287 |
| ber | 0.745652 | 0.001676 | 0.001348 |
| noise_sigma | 0.941931 | 0.002266 | 0.001608 |
| hold_snm | 0.744915 | 6.936077 | 5.578287 |
| read_snm | 0.740687 | 7.329694 | 5.872241 |
| write_margin | 0.730469 | 61.105781 | 42.818057 |
| read_fail | 0.999950 | 0.000000 | 0.000000 |
| write_fail | -0.000000 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 5.578287 | 4.365133 | 6.692109 |
| ber | 0.001348 | 0.001063 | 0.001712 |
| noise_sigma | 0.001608 | 0.001030 | 0.002193 |
| hold_snm | 5.578287 | 4.512499 | 6.955291 |
| read_snm | 5.872241 | 4.646023 | 7.167812 |
| write_margin | 42.818057 | 31.140226 | 54.948940 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 3.214805 |
| ber | -0.000780 |
| noise_sigma | -0.000718 |
| hold_snm | 3.214805 |
| read_snm | 3.585483 |
| write_margin | 15.712500 |
| read_fail | 0.000000 |
| write_fail | 0.000001 |

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
| read_fail | 0.000000 |
| write_fail | 0.000000 |
| noise_sigma | 0.133333 |

- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.
