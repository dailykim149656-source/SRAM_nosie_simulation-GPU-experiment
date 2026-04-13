# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:07:04.133450+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `spice_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
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
| 1 | MLP 3-layer (sklearn) | 0.728322 | 6.834313 | 0.011990 | 505 | yes |
| 2 | MLP 2-layer (Perceptron Gate) | 0.720170 | 6.235450 | 0.000780 | 181 | yes |
| 3 | Polynomial (deg=3) | 0.719340 | 5.710323 | 0.004979 | 120 | no |
| 4 | Polynomial (deg=2) | 0.708154 | 6.858017 | 0.004496 | 36 | no |
| 5 | Random Forest | 0.707220 | 6.297098 | 0.362625 | 3868 | no |
| 6 | Gradient Boosting | 0.697702 | 6.231763 | 0.007735 | 1540 | no |
| 7 | Linear Regression | 0.693171 | 6.298607 | 0.001378 | 8 | no |
| 8 | SVR (RBF) | 0.569070 | 8.354196 | 0.006241 | 0 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.708322` (best Pareto R2 `0.728322` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001560` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.822537 | 6.475067 | 5.190481 |
| ber | 0.832242 | 0.001532 | 0.001253 |
| noise_sigma | 0.971747 | 0.002212 | 0.001506 |
| hold_snm | 0.822537 | 6.475067 | 5.190481 |
| read_snm | 0.840892 | 6.635155 | 5.307763 |
| write_margin | 0.750187 | 57.122194 | 44.235766 |
| read_fail | 0.999950 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 5.190481 | 4.101957 | 6.273404 |
| ber | 0.001253 | 0.001014 | 0.001510 |
| noise_sigma | 0.001506 | 0.001055 | 0.002096 |
| hold_snm | 5.190481 | 3.975420 | 6.411487 |
| read_snm | 5.307763 | 4.156765 | 6.307182 |
| write_margin | 44.235766 | 33.041114 | 58.517619 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 4.569069 |
| ber | -0.001302 |
| noise_sigma | 0.000388 |
| hold_snm | 4.569069 |
| read_snm | 4.548793 |
| write_margin | 25.728255 |
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
