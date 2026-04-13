# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:02:01.944898+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `native_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
- Split mode: `random`
- Target clip quantile: `0.01`
- Target normalize: `True`
- Target prob-logit: `False`
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
| 1 | Gradient Boosting | 0.999965 | 0.087928 | 0.008300 | 1540 | yes |
| 2 | Polynomial (deg=3) | 0.998017 | 0.949948 | 0.004584 | 120 | yes |
| 3 | MLP 2-layer (Perceptron Gate) | 0.991494 | 0.836947 | 0.000581 | 181 | yes |
| 4 | Polynomial (deg=2) | 0.974902 | 2.524924 | 0.004119 | 36 | no |
| 5 | SVR (RBF) | 0.970887 | 3.332848 | 0.007301 | 0 | no |
| 6 | Random Forest | 0.968382 | 1.286467 | 0.387729 | 3558 | no |
| 7 | Linear Regression | 0.900793 | 0.199764 | 0.001227 | 8 | no |
| 8 | MLP 3-layer (sklearn) | -0.996707 | 3.206810 | 0.006447 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.979965` (best Pareto R2 `0.999965` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001162` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.994466 | 1.093629 | 0.743591 |
| ber | 0.992377 | 0.000317 | 0.000232 |
| noise_sigma | 0.952846 | 0.002232 | 0.001660 |
| hold_snm | 0.994466 | 1.093629 | 0.743591 |
| read_snm | 0.993299 | 1.282033 | 0.899983 |
| write_margin | 0.997248 | 6.843182 | 5.670112 |
| read_fail | 0.999981 | 0.000000 | 0.000000 |
| write_fail | 0.999960 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 0.743591 | 0.435493 | 1.039602 |
| ber | 0.000232 | 0.000158 | 0.000327 |
| noise_sigma | 0.001660 | 0.001013 | 0.002196 |
| hold_snm | 0.743591 | 0.448399 | 1.048785 |
| read_snm | 0.899983 | 0.547555 | 1.203020 |
| write_margin | 5.670112 | 4.416510 | 7.013715 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.141080 |
| ber | -0.000091 |
| noise_sigma | 0.002571 |
| hold_snm | -0.141080 |
| read_snm | -0.517515 |
| write_margin | 4.876919 |
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
| ber | 0.000000 |
| read_fail | 0.000000 |
| write_fail | 0.000000 |
| noise_sigma | 0.000000 |

- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.
