# Model Selection Report (Phase 2)

- Generated: 2026-04-13T13:59:02.179964+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `delta_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
- Split mode: `random`
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
| 1 | MLP 3-layer (sklearn) | 0.064523 | 5.180096 | 0.010728 | 505 | yes |
| 2 | Random Forest | -0.226748 | 6.502415 | 0.431527 | 4388 | no |
| 3 | Linear Regression | -0.515315 | 7.833717 | 0.001477 | 8 | yes |
| 4 | SVR (RBF) | -0.546408 | 5.736772 | 0.006857 | 0 | no |
| 5 | MLP 2-layer (Perceptron Gate) | -0.553022 | 7.840329 | 0.000868 | 181 | yes |
| 6 | Polynomial (deg=2) | -0.771343 | 8.844418 | 0.005455 | 36 | no |
| 7 | Polynomial (deg=3) | -0.852594 | 8.001578 | 0.006318 | 120 | no |
| 8 | Gradient Boosting | -1.182467 | 8.111525 | 0.009272 | 1540 | no |

## Recommendation

- Recommended model: **MLP 3-layer (sklearn)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.044523` (best Pareto R2 `0.064523` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.021456` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | -0.177171 | 6.634438 | 3.969894 |
| ber | -0.255878 | 0.001649 | 0.000970 |
| noise_sigma | -0.098085 | 0.002021 | 0.001233 |
| hold_snm | -0.177171 | 6.634438 | 3.969894 |
| read_snm | -0.177688 | 6.857330 | 4.112824 |
| write_margin | -0.663992 | 62.768801 | 37.615696 |
| read_fail | 0.999969 | 0.000000 | 0.000000 |
| write_fail | 0.299201 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 3.969894 | 2.410803 | 5.619534 |
| ber | 0.000970 | 0.000579 | 0.001382 |
| noise_sigma | 0.001233 | 0.000765 | 0.001836 |
| hold_snm | 3.969894 | 2.454873 | 5.682444 |
| read_snm | 4.112824 | 2.434965 | 5.838240 |
| write_margin | 37.615696 | 22.272026 | 51.544186 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 0.045164 |
| ber | 0.000194 |
| noise_sigma | 0.000518 |
| hold_snm | 0.045164 |
| read_snm | 0.053250 |
| write_margin | -12.334636 |
| read_fail | -0.000000 |
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
