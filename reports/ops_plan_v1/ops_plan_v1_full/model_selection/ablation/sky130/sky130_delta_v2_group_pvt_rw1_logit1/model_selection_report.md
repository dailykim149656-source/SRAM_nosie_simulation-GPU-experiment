# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:05:57.225589+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `delta_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
- Split mode: `group_pvt`
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
| 1 | MLP 3-layer (sklearn) | 0.147342 | 4.726544 | 0.008639 | 505 | yes |
| 2 | Linear Regression | -0.063385 | 6.429593 | 0.001396 | 8 | yes |
| 3 | Polynomial (deg=2) | -0.113823 | 6.474386 | 0.004986 | 36 | no |
| 4 | MLP 2-layer (Perceptron Gate) | -0.114989 | 6.466171 | 0.000824 | 181 | yes |
| 5 | SVR (RBF) | -0.130947 | 5.004794 | 0.008646 | 0 | no |
| 6 | Random Forest | -0.241099 | 6.036587 | 0.364822 | 4382 | no |
| 7 | Gradient Boosting | -0.560056 | 6.210486 | 0.008449 | 1540 | no |
| 8 | Polynomial (deg=3) | -0.600363 | 6.815725 | 0.005873 | 120 | no |

## Recommendation

- Recommended model: **MLP 3-layer (sklearn)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.127342` (best Pareto R2 `0.147342` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.017278` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.004846 | 6.677457 | 3.911194 |
| ber | 0.008741 | 0.001617 | 0.000947 |
| noise_sigma | 0.012663 | 0.001930 | 0.001163 |
| hold_snm | 0.004846 | 6.677457 | 3.911194 |
| read_snm | 0.004960 | 6.908150 | 4.052463 |
| write_margin | -0.762712 | 55.340240 | 33.540848 |
| read_fail | 0.999977 | 0.000000 | 0.000000 |
| write_fail | 0.260155 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 3.911194 | 2.441411 | 5.566710 |
| ber | 0.000947 | 0.000555 | 0.001337 |
| noise_sigma | 0.001163 | 0.000637 | 0.001740 |
| hold_snm | 3.911194 | 2.240254 | 5.603122 |
| read_snm | 4.052463 | 2.248003 | 5.526753 |
| write_margin | 33.540848 | 18.115425 | 52.576227 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.019888 |
| ber | 0.000083 |
| noise_sigma | 0.000066 |
| hold_snm | -0.019888 |
| read_snm | -0.016601 |
| write_margin | 0.269242 |
| read_fail | 0.000000 |
| write_fail | 0.000000 |

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
| ber | 0.400000 |
| read_fail | 0.466667 |
| write_fail | 0.000000 |
| noise_sigma | 0.433333 |

- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.
