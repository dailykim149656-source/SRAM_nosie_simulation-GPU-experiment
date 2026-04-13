# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:22:11.196593+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `delta_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
- Split mode: `group_pvt`
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
| 1 | Polynomial (deg=2) | 0.454965 | 8.791597 | 0.005260 | 36 | yes |
| 2 | MLP 2-layer (Perceptron Gate) | 0.445606 | 9.104740 | 0.000810 | 181 | yes |
| 3 | Linear Regression | 0.431856 | 9.006264 | 0.001450 | 8 | no |
| 4 | Random Forest | 0.405615 | 9.951399 | 0.460435 | 4386 | no |
| 5 | Gradient Boosting | 0.270611 | 10.608948 | 0.009925 | 1540 | no |
| 6 | Polynomial (deg=3) | 0.164373 | 11.799467 | 0.005864 | 120 | no |
| 7 | SVR (RBF) | 0.156960 | 11.619382 | 0.009881 | 0 | no |
| 8 | MLP 3-layer (sklearn) | -1.629242 | 9.453007 | 0.010513 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.434965` (best Pareto R2 `0.454965` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001620` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.340630 | 7.825878 | 7.048155 |
| ber | 0.361126 | 0.002104 | 0.001896 |
| noise_sigma | 0.082479 | 0.002992 | 0.002488 |
| hold_snm | 0.340630 | 7.825878 | 7.048155 |
| read_snm | -0.109474 | 8.209324 | 7.330790 |
| write_margin | -0.173197 | 76.490414 | 65.894791 |
| read_fail | 0.999971 | 0.000000 | 0.000000 |
| write_fail | 0.999941 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 7.048155 | 5.934224 | 8.026266 |
| ber | 0.001896 | 0.001692 | 0.002183 |
| noise_sigma | 0.002488 | 0.002042 | 0.002963 |
| hold_snm | 7.048155 | 6.003603 | 7.842788 |
| read_snm | 7.330790 | 6.248389 | 8.318358 |
| write_margin | 65.894791 | 54.018769 | 77.059532 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 6.725081 |
| ber | -0.001861 |
| noise_sigma | 0.001937 |
| hold_snm | 6.725081 |
| read_snm | -11.350331 |
| write_margin | -61.698040 |
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
| ber | 0.366667 |
| read_fail | 0.433333 |
| write_fail | 0.000000 |
| noise_sigma | 0.400000 |

- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.
