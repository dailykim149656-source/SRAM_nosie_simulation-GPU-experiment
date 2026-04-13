# Model Selection Report (Phase 2)

- Generated: 2026-04-13T13:58:18.094192+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `native_v2`
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
| 1 | Gradient Boosting | 0.999958 | 0.098680 | 0.013396 | 1540 | yes |
| 2 | Polynomial (deg=3) | 0.998005 | 0.954975 | 0.009459 | 120 | yes |
| 3 | MLP 2-layer (Perceptron Gate) | 0.990888 | 0.869368 | 0.001014 | 181 | yes |
| 4 | Polynomial (deg=2) | 0.973078 | 2.731916 | 0.007086 | 36 | no |
| 5 | SVR (RBF) | 0.970887 | 3.332848 | 0.008763 | 0 | no |
| 6 | Random Forest | 0.967049 | 1.303926 | 0.535471 | 3572 | no |
| 7 | Linear Regression | 0.915731 | 0.217069 | 0.001871 | 8 | no |
| 8 | MLP 3-layer (sklearn) | -1.001526 | 3.612488 | 0.007687 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.979958` (best Pareto R2 `0.999958` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.002028` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.993847 | 1.145454 | 0.755720 |
| ber | 0.991241 | 0.000338 | 0.000245 |
| noise_sigma | 0.950119 | 0.002227 | 0.001727 |
| hold_snm | 0.993847 | 1.145454 | 0.755720 |
| read_snm | 0.993409 | 1.288301 | 0.876964 |
| write_margin | 0.996871 | 7.343352 | 5.975427 |
| read_fail | 0.999983 | 0.000000 | 0.000000 |
| write_fail | 0.999966 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 0.755720 | 0.453417 | 1.026912 |
| ber | 0.000245 | 0.000171 | 0.000336 |
| noise_sigma | 0.001727 | 0.001162 | 0.002221 |
| hold_snm | 0.755720 | 0.451276 | 1.010869 |
| read_snm | 0.876964 | 0.540330 | 1.178592 |
| write_margin | 5.975427 | 4.558644 | 7.426136 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.133112 |
| ber | -0.000060 |
| noise_sigma | 0.002746 |
| hold_snm | -0.133112 |
| read_snm | -0.516348 |
| write_margin | 2.528828 |
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
