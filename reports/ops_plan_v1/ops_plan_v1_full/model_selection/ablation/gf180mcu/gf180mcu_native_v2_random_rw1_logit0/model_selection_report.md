# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:12:30.664269+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `native_v2`
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
| 1 | Gradient Boosting | 0.999959 | 0.142467 | 0.007874 | 1540 | yes |
| 2 | Polynomial (deg=3) | 0.997308 | 1.153840 | 0.005607 | 120 | yes |
| 3 | MLP 2-layer (Perceptron Gate) | 0.989156 | 0.936580 | 0.000725 | 181 | yes |
| 4 | SVR (RBF) | 0.971350 | 3.381002 | 0.009688 | 0 | no |
| 5 | Polynomial (deg=2) | 0.970270 | 2.902456 | 0.004918 | 36 | no |
| 6 | Random Forest | 0.961164 | 1.555613 | 0.380822 | 3560 | no |
| 7 | Linear Regression | 0.922457 | 0.321579 | 0.001412 | 8 | no |
| 8 | MLP 3-layer (sklearn) | -1.002105 | 3.601992 | 0.008316 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.979959` (best Pareto R2 `0.999959` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001450` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.993769 | 1.265173 | 0.844652 |
| ber | 0.991273 | 0.000414 | 0.000289 |
| noise_sigma | 0.935776 | 0.003253 | 0.002565 |
| hold_snm | 0.993769 | 1.265173 | 0.844652 |
| read_snm | 0.993209 | 1.443951 | 1.003407 |
| write_margin | 0.996544 | 7.926924 | 6.327117 |
| read_fail | 0.999977 | 0.000000 | 0.000000 |
| write_fail | 0.999966 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 0.844652 | 0.522050 | 1.145759 |
| ber | 0.000289 | 0.000192 | 0.000406 |
| noise_sigma | 0.002565 | 0.001796 | 0.003232 |
| hold_snm | 0.844652 | 0.506057 | 1.132657 |
| read_snm | 1.003407 | 0.645515 | 1.334038 |
| write_margin | 6.327117 | 4.577689 | 8.128781 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.304872 |
| ber | -0.000006 |
| noise_sigma | 0.004284 |
| hold_snm | -0.304872 |
| read_snm | -0.865725 |
| write_margin | 0.575530 |
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
