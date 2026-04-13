# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:00:27.722367+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `spice_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
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
| 1 | Random Forest | 0.677061 | 6.331672 | 0.404816 | 3670 | yes |
| 2 | MLP 2-layer (Perceptron Gate) | 0.653545 | 7.058925 | 0.000679 | 181 | yes |
| 3 | MLP 3-layer (sklearn) | 0.647086 | 7.708968 | 0.006296 | 505 | no |
| 4 | Polynomial (deg=3) | 0.628506 | 6.805193 | 0.005971 | 120 | no |
| 5 | Polynomial (deg=2) | 0.609753 | 8.572574 | 0.006295 | 36 | no |
| 6 | Linear Regression | 0.591999 | 7.661526 | 0.001348 | 8 | no |
| 7 | Gradient Boosting | 0.562548 | 7.870270 | 0.008049 | 1540 | no |
| 8 | SVR (RBF) | 0.370888 | 9.997970 | 0.008400 | 0 | no |

## Recommendation

- Recommended model: **Random Forest**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.657061` (best Pareto R2 `0.677061` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.809631` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.744597 | 7.077386 | 5.814576 |
| ber | 0.745024 | 0.001710 | 0.001401 |
| noise_sigma | 0.941254 | 0.002299 | 0.001641 |
| hold_snm | 0.744597 | 7.077386 | 5.814576 |
| read_snm | 0.730767 | 7.621066 | 6.216815 |
| write_margin | 0.729917 | 61.356825 | 43.184296 |
| read_fail | 0.999950 | 0.000000 | 0.000000 |
| write_fail | -0.000000 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 5.814576 | 4.631882 | 6.989265 |
| ber | 0.001401 | 0.001116 | 0.001752 |
| noise_sigma | 0.001641 | 0.001071 | 0.002242 |
| hold_snm | 5.814576 | 4.735210 | 7.176161 |
| read_snm | 6.216815 | 4.959995 | 7.433723 |
| write_margin | 43.184296 | 31.208571 | 55.054950 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 3.538829 |
| ber | -0.000864 |
| noise_sigma | -0.000783 |
| hold_snm | 3.538829 |
| read_snm | 3.819110 |
| write_margin | 14.380022 |
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
