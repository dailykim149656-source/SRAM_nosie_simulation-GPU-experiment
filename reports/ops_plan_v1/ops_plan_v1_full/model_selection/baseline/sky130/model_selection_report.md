# Model Selection Report (Phase 2)

- Generated: 2026-04-13T13:53:22.508168+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `spice_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
- Split mode: `group_pvt`
- Target clip quantile: `0.01`
- Target normalize: `True`
- Target prob-logit: `True`
- Fail aux split (`read_fail/write_fail` dedicated heads): `False`
- Fail aux profile (requested -> resolved): `auto -> sky130`
- R2 clip range: `[-10.0, 1.0]`
- Target importance (weighted aggregation): `snm=1.00, ber=1.50, noise_sigma=1.30, hold_snm=1.00, read_snm=1.20, write_margin=1.20, read_fail=2.00, write_fail=2.00`
- Samples: `45`
- Features: `temp_k, vdd, corner_ff, corner_fs, corner_sf, corner_ss, corner_tt`
- Cross-validation folds used: `5`

## Leaderboard

| Rank | Model | Mean R2 | Mean MAE | Infer ms/sample | Params | Pareto |
|---:|---|---:|---:|---:|---:|---:|
| 1 | MLP 2-layer (Perceptron Gate) | 0.717861 | 6.182323 | 0.000762 | 181 | yes |
| 2 | Random Forest | 0.708615 | 6.220209 | 0.566414 | 3868 | no |
| 3 | Polynomial (deg=2) | 0.705426 | 7.200751 | 0.011565 | 36 | no |
| 4 | Linear Regression | 0.699859 | 6.429427 | 0.004240 | 8 | no |
| 5 | Gradient Boosting | 0.698484 | 6.271021 | 0.011027 | 1540 | no |
| 6 | Polynomial (deg=3) | 0.698241 | 6.603557 | 0.013167 | 120 | no |
| 7 | MLP 3-layer (sklearn) | 0.623195 | 6.888510 | 0.012738 | 505 | no |
| 8 | SVR (RBF) | 0.562629 | 8.558881 | 0.010512 | 0 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.697861` (best Pareto R2 `0.717861` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001525` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.816239 | 6.545204 | 5.278709 |
| ber | 0.823192 | 0.001566 | 0.001284 |
| noise_sigma | 0.972808 | 0.002173 | 0.001563 |
| hold_snm | 0.816239 | 6.545204 | 5.278709 |
| read_snm | 0.832241 | 6.769393 | 5.458922 |
| write_margin | 0.757945 | 56.072516 | 43.441608 |
| read_fail | 0.999950 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 5.278709 | 4.180137 | 6.492715 |
| ber | 0.001284 | 0.001006 | 0.001524 |
| noise_sigma | 0.001563 | 0.001204 | 0.002036 |
| hold_snm | 5.278709 | 4.156311 | 6.449471 |
| read_snm | 5.458922 | 4.284719 | 6.555327 |
| write_margin | 43.441608 | 32.282899 | 58.160984 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 2.840403 |
| ber | -0.000974 |
| noise_sigma | 0.000972 |
| hold_snm | 2.840403 |
| read_snm | 2.973942 |
| write_margin | 17.962883 |
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
