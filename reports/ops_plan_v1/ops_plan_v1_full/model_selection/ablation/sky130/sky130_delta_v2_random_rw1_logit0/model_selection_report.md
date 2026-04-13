# Model Selection Report (Phase 2)

- Generated: 2026-04-13T13:59:55.224683+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `delta_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
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
| 1 | Random Forest | -0.048177 | 6.502414 | 0.625445 | 4388 | yes |
| 2 | Linear Regression | -0.336744 | 7.833716 | 0.001378 | 8 | yes |
| 3 | SVR (RBF) | -0.367836 | 5.736772 | 0.012105 | 0 | no |
| 4 | MLP 2-layer (Perceptron Gate) | -0.374456 | 7.840329 | 0.001052 | 181 | yes |
| 5 | Polynomial (deg=2) | -0.592771 | 8.844417 | 0.005232 | 36 | no |
| 6 | Polynomial (deg=3) | -0.674023 | 8.001578 | 0.005873 | 120 | no |
| 7 | Gradient Boosting | -1.003895 | 8.111524 | 0.012844 | 1540 | no |
| 8 | MLP 3-layer (sklearn) | -1.774620 | 5.312515 | 0.008797 | 505 | no |

## Recommendation

- Recommended model: **Random Forest**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `-0.068177` (best Pareto R2 `-0.048177` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `1.250889` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | -0.513773 | 7.241317 | 5.121982 |
| ber | -0.516856 | 0.001755 | 0.001239 |
| noise_sigma | -0.552405 | 0.002111 | 0.001422 |
| hold_snm | -0.513773 | 7.241317 | 5.121982 |
| read_snm | -0.526148 | 7.496179 | 5.315321 |
| write_margin | -1.156027 | 68.541818 | 46.834154 |
| read_fail | 0.999994 | 0.000000 | 0.000000 |
| write_fail | 1.000000 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 5.121982 | 3.692788 | 6.623959 |
| ber | 0.001239 | 0.000871 | 0.001605 |
| noise_sigma | 0.001422 | 0.000951 | 0.002009 |
| hold_snm | 5.121982 | 3.733373 | 6.786809 |
| read_snm | 5.315321 | 3.715260 | 6.825665 |
| write_margin | 46.834154 | 32.817629 | 61.187322 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -4.154149 |
| ber | 0.001015 |
| noise_sigma | 0.000547 |
| hold_snm | -4.154149 |
| read_snm | -4.364616 |
| write_margin | -15.600668 |
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
