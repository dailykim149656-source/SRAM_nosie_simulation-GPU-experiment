# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:01:26.892571+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `native_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
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
| 1 | MLP 3-layer (sklearn) | 0.842413 | 3.074432 | 0.007426 | 505 | yes |
| 2 | Gradient Boosting | 0.821385 | 0.087928 | 0.008173 | 1540 | no |
| 3 | Polynomial (deg=3) | 0.819430 | 0.949948 | 0.004896 | 120 | yes |
| 4 | MLP 2-layer (Perceptron Gate) | 0.812930 | 0.836947 | 0.000643 | 181 | yes |
| 5 | Polynomial (deg=2) | 0.796227 | 2.524925 | 0.004493 | 36 | no |
| 6 | SVR (RBF) | 0.792306 | 3.332849 | 0.006777 | 0 | no |
| 7 | Random Forest | 0.789842 | 1.286467 | 0.336673 | 3558 | no |
| 8 | Linear Regression | 0.722248 | 0.199764 | 0.001165 | 8 | no |

## Recommendation

- Recommended model: **MLP 3-layer (sklearn)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.822413` (best Pareto R2 `0.842413` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.014853` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.960326 | 2.894387 | 2.240632 |
| ber | 0.952756 | 0.000780 | 0.000612 |
| noise_sigma | 0.924222 | 0.002949 | 0.002164 |
| hold_snm | 0.960326 | 2.894387 | 2.240632 |
| read_snm | 0.955754 | 3.256318 | 2.525800 |
| write_margin | 0.949958 | 29.518935 | 22.431402 |
| read_fail | 0.999951 | 0.000000 | 0.000000 |
| write_fail | 0.298496 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 2.240632 | 1.590403 | 2.825221 |
| ber | 0.000612 | 0.000453 | 0.000786 |
| noise_sigma | 0.002164 | 0.001515 | 0.002902 |
| hold_snm | 2.240632 | 1.592308 | 2.879317 |
| read_snm | 2.525800 | 1.858740 | 3.338993 |
| write_margin | 22.431402 | 16.612706 | 28.584590 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 7.289684 |
| ber | -0.000967 |
| noise_sigma | 0.001239 |
| hold_snm | 7.289684 |
| read_snm | 7.399375 |
| write_margin | 67.809621 |
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
