# Model Selection Report (Phase 2)

- Generated: 2026-04-13T13:57:20.692288+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `native_v2`
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
| 1 | MLP 3-layer (sklearn) | 0.837618 | 3.480068 | 0.010380 | 505 | yes |
| 2 | Gradient Boosting | 0.821382 | 0.098680 | 0.007716 | 1540 | yes |
| 3 | Polynomial (deg=3) | 0.819419 | 0.954976 | 0.005708 | 120 | yes |
| 4 | MLP 2-layer (Perceptron Gate) | 0.812311 | 0.869368 | 0.000842 | 181 | yes |
| 5 | Polynomial (deg=2) | 0.794396 | 2.731916 | 0.005371 | 36 | no |
| 6 | SVR (RBF) | 0.792306 | 3.332849 | 0.009905 | 0 | no |
| 7 | Random Forest | 0.788539 | 1.303925 | 0.423225 | 3572 | no |
| 8 | Linear Regression | 0.737250 | 0.217069 | 0.001375 | 8 | no |

## Recommendation

- Recommended model: **MLP 3-layer (sklearn)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.817618` (best Pareto R2 `0.837618` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.011415` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.955368 | 3.036744 | 2.427448 |
| ber | 0.945738 | 0.000827 | 0.000644 |
| noise_sigma | 0.921693 | 0.002982 | 0.002255 |
| hold_snm | 0.955368 | 3.036744 | 2.427448 |
| read_snm | 0.943695 | 3.751741 | 3.055648 |
| write_margin | 0.935863 | 33.746819 | 25.375993 |
| read_fail | 0.999951 | 0.000000 | 0.000000 |
| write_fail | 0.299201 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 2.427448 | 1.747812 | 2.996054 |
| ber | 0.000644 | 0.000479 | 0.000817 |
| noise_sigma | 0.002255 | 0.001629 | 0.002901 |
| hold_snm | 2.427448 | 1.810791 | 3.028880 |
| read_snm | 3.055648 | 2.441062 | 3.730322 |
| write_margin | 25.375993 | 18.136013 | 32.839377 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 7.613285 |
| ber | -0.000766 |
| noise_sigma | 0.001970 |
| hold_snm | 7.613285 |
| read_snm | 7.983890 |
| write_margin | 77.932759 |
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
