# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:08:32.286827+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `native_v2`
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
| 1 | MLP 3-layer (sklearn) | 0.839789 | 3.007378 | 0.006947 | 505 | yes |
| 2 | Gradient Boosting | 0.821413 | 0.050198 | 0.008014 | 1540 | no |
| 3 | Polynomial (deg=3) | 0.820730 | 0.641086 | 0.009281 | 120 | no |
| 4 | Random Forest | 0.819468 | 0.465669 | 0.454097 | 3738 | no |
| 5 | MLP 2-layer (Perceptron Gate) | 0.817395 | 0.629071 | 0.000819 | 181 | yes |
| 6 | Polynomial (deg=2) | 0.812279 | 1.907107 | 0.007878 | 36 | no |
| 7 | SVR (RBF) | 0.793518 | 3.321194 | 0.007071 | 0 | no |
| 8 | Linear Regression | 0.770193 | 0.150730 | 0.002262 | 8 | no |

## Recommendation

- Recommended model: **MLP 3-layer (sklearn)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.819789` (best Pareto R2 `0.839789` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.013894` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.973839 | 2.584527 | 1.965605 |
| ber | 0.952527 | 0.000876 | 0.000687 |
| noise_sigma | 0.925810 | 0.003611 | 0.002748 |
| hold_snm | 0.973839 | 2.584527 | 1.965605 |
| read_snm | 0.969325 | 2.987313 | 2.268038 |
| write_margin | 0.952792 | 29.058678 | 22.520983 |
| read_fail | 0.999951 | 0.000000 | 0.000000 |
| write_fail | 0.259588 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 1.965605 | 1.478746 | 2.605992 |
| ber | 0.000687 | 0.000536 | 0.000871 |
| noise_sigma | 0.002748 | 0.002145 | 0.003718 |
| hold_snm | 1.965605 | 1.527272 | 2.509907 |
| read_snm | 2.268038 | 1.682369 | 2.983851 |
| write_margin | 22.520983 | 16.898990 | 29.473540 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -1.275491 |
| ber | 0.000587 |
| noise_sigma | 0.001997 |
| hold_snm | -1.275491 |
| read_snm | -1.414530 |
| write_margin | 3.646781 |
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
