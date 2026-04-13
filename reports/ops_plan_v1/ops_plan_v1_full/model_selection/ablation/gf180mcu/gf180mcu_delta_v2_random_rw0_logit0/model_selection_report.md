# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:18:23.662316+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `delta_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
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
| 1 | Random Forest | 0.272999 | 10.571313 | 0.565803 | 4268 | yes |
| 2 | MLP 2-layer (Perceptron Gate) | 0.167788 | 10.152975 | 0.000837 | 181 | yes |
| 3 | Polynomial (deg=2) | 0.140658 | 11.179979 | 0.006872 | 36 | no |
| 4 | Linear Regression | 0.113134 | 10.308462 | 0.001918 | 8 | no |
| 5 | Gradient Boosting | -0.075277 | 13.538913 | 0.014037 | 1540 | no |
| 6 | Polynomial (deg=3) | -0.184964 | 13.681666 | 0.008795 | 120 | no |
| 7 | SVR (RBF) | -0.394191 | 13.642449 | 0.011755 | 0 | no |
| 8 | MLP 3-layer (sklearn) | -1.950388 | 10.885837 | 0.009397 | 505 | no |

## Recommendation

- Recommended model: **Random Forest**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.252999` (best Pareto R2 `0.272999` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `1.131606` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.220233 | 8.151374 | 7.260996 |
| ber | 0.219285 | 0.002228 | 0.001981 |
| noise_sigma | 0.188493 | 0.002917 | 0.002210 |
| hold_snm | 0.220233 | 8.151374 | 7.260996 |
| read_snm | 0.077202 | 8.361368 | 7.383160 |
| write_margin | -1.707884 | 88.881219 | 79.175895 |
| read_fail | 0.999987 | 0.000000 | 0.000000 |
| write_fail | 1.000000 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 7.260996 | 6.181769 | 8.385138 |
| ber | 0.001981 | 0.001626 | 0.002354 |
| noise_sigma | 0.002210 | 0.001478 | 0.002884 |
| hold_snm | 7.260996 | 6.047512 | 8.337064 |
| read_snm | 7.383160 | 6.106159 | 8.857146 |
| write_margin | 79.175895 | 69.094521 | 92.327698 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 6.166276 |
| ber | -0.001646 |
| noise_sigma | 0.000533 |
| hold_snm | 6.166276 |
| read_snm | -4.114965 |
| write_margin | -27.974828 |
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
