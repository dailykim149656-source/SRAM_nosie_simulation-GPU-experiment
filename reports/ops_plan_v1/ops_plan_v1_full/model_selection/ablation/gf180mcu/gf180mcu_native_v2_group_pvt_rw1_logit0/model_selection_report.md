# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:20:49.515146+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `native_v2`
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
| 1 | Gradient Boosting | 0.999987 | 0.083947 | 0.008002 | 1540 | yes |
| 2 | Polynomial (deg=3) | 0.999127 | 0.751949 | 0.004938 | 120 | yes |
| 3 | Random Forest | 0.997714 | 0.531404 | 0.336925 | 3754 | no |
| 4 | MLP 2-layer (Perceptron Gate) | 0.995569 | 0.684941 | 0.000872 | 181 | yes |
| 5 | Polynomial (deg=2) | 0.989072 | 2.396379 | 0.004373 | 36 | no |
| 6 | SVR (RBF) | 0.970048 | 3.365991 | 0.007110 | 0 | no |
| 7 | Linear Regression | 0.965020 | 0.235763 | 0.001479 | 8 | no |
| 8 | MLP 3-layer (sklearn) | -1.075573 | 3.624784 | 0.008165 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.979987` (best Pareto R2 `0.999987` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001743` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.996653 | 1.072014 | 0.664504 |
| ber | 0.993984 | 0.000393 | 0.000284 |
| noise_sigma | 0.978537 | 0.002419 | 0.001756 |
| hold_snm | 0.996653 | 1.072014 | 0.664504 |
| read_snm | 0.996697 | 1.155851 | 0.732564 |
| write_margin | 0.998442 | 5.990310 | 4.550453 |
| read_fail | 0.999974 | 0.000000 | 0.000000 |
| write_fail | 0.999941 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 0.664504 | 0.446695 | 0.919359 |
| ber | 0.000284 | 0.000225 | 0.000372 |
| noise_sigma | 0.001756 | 0.001266 | 0.002320 |
| hold_snm | 0.664504 | 0.436897 | 0.922995 |
| read_snm | 0.732564 | 0.500482 | 1.006125 |
| write_margin | 4.550453 | 3.300171 | 5.648009 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.191144 |
| ber | -0.000031 |
| noise_sigma | 0.003378 |
| hold_snm | -0.191144 |
| read_snm | -0.650652 |
| write_margin | 0.328885 |
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
| ber | 0.000000 |
| read_fail | 0.000000 |
| write_fail | 0.000000 |
| noise_sigma | 0.000000 |

- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.
