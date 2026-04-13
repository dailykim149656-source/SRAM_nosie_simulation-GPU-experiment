# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:09:42.523967+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `delta_v2`
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
| 1 | MLP 3-layer (sklearn) | 0.141927 | 4.725336 | 0.007887 | 505 | yes |
| 2 | Linear Regression | -0.056081 | 6.290072 | 0.001428 | 8 | yes |
| 3 | SVR (RBF) | -0.067669 | 4.883607 | 0.006157 | 0 | no |
| 4 | MLP 2-layer (Perceptron Gate) | -0.070979 | 6.187576 | 0.000722 | 181 | yes |
| 5 | Polynomial (deg=2) | -0.089441 | 6.267189 | 0.005035 | 36 | no |
| 6 | Random Forest | -0.282891 | 6.125893 | 0.405322 | 4382 | no |
| 7 | Polynomial (deg=3) | -0.334744 | 5.749474 | 0.005406 | 120 | no |
| 8 | Gradient Boosting | -0.569413 | 6.248260 | 0.008662 | 1540 | no |

## Recommendation

- Recommended model: **MLP 3-layer (sklearn)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.121927` (best Pareto R2 `0.141927` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.015774` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.008834 | 6.661160 | 3.907524 |
| ber | -0.017553 | 0.001634 | 0.000959 |
| noise_sigma | -0.014067 | 0.001947 | 0.001167 |
| hold_snm | 0.008834 | 6.661160 | 3.907524 |
| read_snm | 0.008831 | 6.891614 | 4.048791 |
| write_margin | -0.761003 | 55.340061 | 33.539341 |
| read_fail | 0.999979 | 0.000000 | 0.000000 |
| write_fail | 0.259588 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 3.907524 | 2.439849 | 5.550191 |
| ber | 0.000959 | 0.000576 | 0.001354 |
| noise_sigma | 0.001167 | 0.000647 | 0.001745 |
| hold_snm | 3.907524 | 2.249475 | 5.606288 |
| read_snm | 4.048791 | 2.256934 | 5.512565 |
| write_margin | 33.539341 | 18.114670 | 52.576536 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.020828 |
| ber | -0.000146 |
| noise_sigma | 0.000002 |
| hold_snm | -0.020828 |
| read_snm | -0.017271 |
| write_margin | 0.271932 |
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
