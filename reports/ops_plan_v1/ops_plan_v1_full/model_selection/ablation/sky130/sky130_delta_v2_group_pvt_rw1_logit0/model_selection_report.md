# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:06:33.414264+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `delta_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
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
| 1 | Linear Regression | 0.115187 | 6.429593 | 0.001646 | 8 | yes |
| 2 | Polynomial (deg=2) | 0.064748 | 6.474385 | 0.005603 | 36 | no |
| 3 | MLP 2-layer (Perceptron Gate) | 0.063572 | 6.466171 | 0.000871 | 181 | yes |
| 4 | SVR (RBF) | 0.047624 | 5.004794 | 0.009232 | 0 | no |
| 5 | Random Forest | -0.062527 | 6.036586 | 0.449567 | 4382 | no |
| 6 | Gradient Boosting | -0.381484 | 6.210486 | 0.008903 | 1540 | no |
| 7 | Polynomial (deg=3) | -0.421791 | 6.815725 | 0.007819 | 120 | no |
| 8 | MLP 3-layer (sklearn) | -1.684829 | 4.862100 | 0.007841 | 505 | no |

## Recommendation

- Recommended model: **Linear Regression**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.095187` (best Pareto R2 `0.115187` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.003292` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.067618 | 6.177807 | 5.020582 |
| ber | 0.088855 | 0.001538 | 0.001053 |
| noise_sigma | -0.489544 | 0.001961 | 0.001477 |
| hold_snm | 0.067618 | 6.177807 | 5.020582 |
| read_snm | 0.066767 | 6.394668 | 5.195131 |
| write_margin | -2.018435 | 58.936095 | 46.443846 |
| read_fail | 0.999993 | 0.000000 | 0.000000 |
| write_fail | 1.000000 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 5.020582 | 4.051879 | 6.146546 |
| ber | 0.001053 | 0.000702 | 0.001379 |
| noise_sigma | 0.001477 | 0.001097 | 0.001938 |
| hold_snm | 5.020582 | 3.837640 | 6.182610 |
| read_snm | 5.195131 | 4.034016 | 6.200907 |
| write_margin | 46.443846 | 35.771598 | 59.658000 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -3.771063 |
| ber | 0.000400 |
| noise_sigma | 0.001081 |
| hold_snm | -3.771063 |
| read_snm | -3.896958 |
| write_margin | -33.144868 |
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
