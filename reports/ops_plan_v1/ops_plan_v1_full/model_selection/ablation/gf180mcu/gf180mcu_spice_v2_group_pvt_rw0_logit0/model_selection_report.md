# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:23:43.590714+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `spice_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
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
| 1 | MLP 2-layer (Perceptron Gate) | 0.855076 | 9.123700 | 0.001235 | 181 | yes |
| 2 | Polynomial (deg=2) | 0.845191 | 9.125940 | 0.005868 | 36 | no |
| 3 | Linear Regression | 0.843987 | 8.765959 | 0.001482 | 8 | no |
| 4 | Random Forest | 0.835433 | 9.831872 | 0.537614 | 4116 | no |
| 5 | Gradient Boosting | 0.814086 | 10.459437 | 0.009272 | 1540 | no |
| 6 | Polynomial (deg=3) | 0.780603 | 10.777463 | 0.007446 | 120 | no |
| 7 | SVR (RBF) | 0.737616 | 10.635789 | 0.010212 | 0 | no |
| 8 | MLP 3-layer (sklearn) | -1.188016 | 11.127293 | 0.009086 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.835076` (best Pareto R2 `0.855076` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.002470` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.765635 | 7.587311 | 6.892847 |
| ber | 0.770648 | 0.002054 | 0.001886 |
| noise_sigma | 0.975340 | 0.002464 | 0.001741 |
| hold_snm | 0.765635 | 7.587311 | 6.892847 |
| read_snm | 0.819516 | 7.465607 | 6.660868 |
| write_margin | 0.532015 | 75.374024 | 67.001340 |
| read_fail | 0.999978 | 0.000000 | 0.000000 |
| write_fail | 0.999935 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 6.892847 | 5.863479 | 7.945034 |
| ber | 0.001886 | 0.001671 | 0.002136 |
| noise_sigma | 0.001741 | 0.001175 | 0.002268 |
| hold_snm | 6.892847 | 5.917963 | 7.781942 |
| read_snm | 6.660868 | 5.645137 | 7.502677 |
| write_margin | 67.001340 | 56.779803 | 77.324924 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -7.960105 |
| ber | 0.001929 |
| noise_sigma | 0.000071 |
| hold_snm | -7.960105 |
| read_snm | 6.767637 |
| write_margin | 62.092456 |
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
