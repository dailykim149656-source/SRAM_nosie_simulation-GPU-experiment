# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:25:42.233898+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `delta_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
- Split mode: `group_pvt`
- Target clip quantile: `0.01`
- Target normalize: `True`
- Target prob-logit: `True`
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
| 1 | Polynomial (deg=2) | 0.327165 | 8.700362 | 0.004950 | 36 | yes |
| 2 | MLP 2-layer (Perceptron Gate) | 0.310591 | 8.910396 | 0.000683 | 181 | yes |
| 3 | Linear Regression | 0.296328 | 8.801747 | 0.001420 | 8 | no |
| 4 | MLP 3-layer (sklearn) | 0.271347 | 9.177440 | 0.006906 | 505 | no |
| 5 | Random Forest | 0.228722 | 9.932278 | 0.392252 | 4448 | no |
| 6 | Polynomial (deg=3) | 0.110672 | 10.882352 | 0.005779 | 120 | no |
| 7 | Gradient Boosting | 0.110499 | 10.549785 | 0.007354 | 1540 | no |
| 8 | SVR (RBF) | 0.017491 | 11.353667 | 0.006526 | 0 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.307165` (best Pareto R2 `0.327165` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001366` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.367443 | 7.627840 | 6.846091 |
| ber | 0.381378 | 0.002064 | 0.001856 |
| noise_sigma | 0.085036 | 0.003222 | 0.002571 |
| hold_snm | 0.367443 | 7.627840 | 6.846091 |
| read_snm | 0.097328 | 7.772873 | 6.911334 |
| write_margin | -0.046340 | 73.791428 | 64.837102 |
| read_fail | 0.999969 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 6.846091 | 5.717019 | 7.830388 |
| ber | 0.001856 | 0.001632 | 0.002149 |
| noise_sigma | 0.002571 | 0.001992 | 0.003161 |
| hold_snm | 6.846091 | 5.781837 | 7.680777 |
| read_snm | 6.911334 | 5.823212 | 7.828076 |
| write_margin | 64.837102 | 53.819100 | 75.228706 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 6.964360 |
| ber | -0.001951 |
| noise_sigma | 0.003580 |
| hold_snm | 6.964360 |
| read_snm | -9.390513 |
| write_margin | -59.747290 |
| read_fail | 0.000000 |
| write_fail | 0.000001 |

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
