# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:09:11.017482+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `native_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
- Split mode: `group_pvt`
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
| 1 | Gradient Boosting | 0.999991 | 0.050198 | 0.008993 | 1540 | yes |
| 2 | Polynomial (deg=3) | 0.999312 | 0.641085 | 0.005818 | 120 | yes |
| 3 | Random Forest | 0.998045 | 0.465669 | 0.355637 | 3738 | no |
| 4 | MLP 2-layer (Perceptron Gate) | 0.995958 | 0.629071 | 0.000909 | 181 | yes |
| 5 | Polynomial (deg=2) | 0.990889 | 1.907106 | 0.005335 | 36 | no |
| 6 | SVR (RBF) | 0.972094 | 3.321194 | 0.008344 | 0 | no |
| 7 | Linear Regression | 0.948777 | 0.150730 | 0.001416 | 8 | no |
| 8 | MLP 3-layer (sklearn) | -0.992283 | 3.142970 | 0.009037 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.979991` (best Pareto R2 `0.999991` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001819` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.997143 | 0.920197 | 0.527904 |
| ber | 0.994810 | 0.000300 | 0.000209 |
| noise_sigma | 0.980105 | 0.001886 | 0.001204 |
| hold_snm | 0.997143 | 0.920197 | 0.527904 |
| read_snm | 0.996626 | 1.071067 | 0.587127 |
| write_margin | 0.998597 | 5.517619 | 4.402797 |
| read_fail | 0.999978 | 0.000000 | 0.000000 |
| write_fail | 0.999934 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 0.527904 | 0.323968 | 0.763203 |
| ber | 0.000209 | 0.000164 | 0.000279 |
| noise_sigma | 0.001204 | 0.000831 | 0.001739 |
| hold_snm | 0.527904 | 0.327228 | 0.759239 |
| read_snm | 0.587127 | 0.360889 | 0.840557 |
| write_margin | 4.402797 | 3.473088 | 5.369639 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 0.145654 |
| ber | -0.000142 |
| noise_sigma | 0.001705 |
| hold_snm | 0.145654 |
| read_snm | -0.119559 |
| write_margin | 4.254890 |
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
