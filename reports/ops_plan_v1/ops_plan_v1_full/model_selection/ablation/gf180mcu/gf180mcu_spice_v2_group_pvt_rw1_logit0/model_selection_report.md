# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:19:40.189842+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `spice_v2`
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
| 1 | MLP 2-layer (Perceptron Gate) | 0.852165 | 9.164334 | 0.000701 | 181 | yes |
| 2 | Linear Regression | 0.847119 | 8.940113 | 0.001605 | 8 | no |
| 3 | Polynomial (deg=2) | 0.841180 | 9.351054 | 0.005940 | 36 | no |
| 4 | Random Forest | 0.834753 | 9.763188 | 0.411690 | 4134 | no |
| 5 | Gradient Boosting | 0.807940 | 10.483532 | 0.008129 | 1540 | no |
| 6 | Polynomial (deg=3) | 0.745612 | 11.778042 | 0.006478 | 120 | no |
| 7 | SVR (RBF) | 0.720623 | 10.878245 | 0.008155 | 0 | no |
| 8 | MLP 3-layer (sklearn) | -1.269708 | 11.503992 | 0.008444 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.832165` (best Pareto R2 `0.852165` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001402` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.755328 | 7.768325 | 7.034723 |
| ber | 0.763676 | 0.002090 | 0.001902 |
| noise_sigma | 0.976009 | 0.002422 | 0.001718 |
| hold_snm | 0.755328 | 7.768325 | 7.034723 |
| read_snm | 0.814660 | 7.579855 | 6.884781 |
| write_margin | 0.534861 | 75.804215 | 66.920230 |
| read_fail | 0.999980 | 0.000000 | 0.000000 |
| write_fail | 0.999941 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 7.034723 | 6.092628 | 8.050360 |
| ber | 0.001902 | 0.001676 | 0.002172 |
| noise_sigma | 0.001718 | 0.001128 | 0.002241 |
| hold_snm | 7.034723 | 6.067875 | 8.028862 |
| read_snm | 6.884781 | 5.974500 | 7.740006 |
| write_margin | 66.920230 | 56.563001 | 76.881277 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -8.318693 |
| ber | 0.002060 |
| noise_sigma | -0.000270 |
| hold_snm | -8.318693 |
| read_snm | 7.888410 |
| write_margin | 65.109452 |
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
