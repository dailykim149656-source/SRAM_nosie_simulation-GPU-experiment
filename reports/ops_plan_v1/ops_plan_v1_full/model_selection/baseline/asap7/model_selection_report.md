# Model Selection Report (Phase 2)

- Generated: 2026-04-13T13:55:23.714699+00:00
- Data source: `predictive-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_asap7_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `asap7`
- Target Source: `spice_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
- Split mode: `group_pvt`
- Target clip quantile: `0.01`
- Target normalize: `True`
- Target prob-logit: `True`
- Fail aux split (`read_fail/write_fail` dedicated heads): `False`
- Fail aux profile (requested -> resolved): `auto -> default`
- R2 clip range: `[-10.0, 1.0]`
- Target importance (weighted aggregation): `snm=1.00, ber=1.50, noise_sigma=1.30, hold_snm=1.00, read_snm=1.20, write_margin=1.20, read_fail=2.00, write_fail=2.00`
- Samples: `27`
- Features: `temp_k, vdd, corner_ff, corner_ss, corner_tt`
- Cross-validation folds used: `5`

## Leaderboard

| Rank | Model | Mean R2 | Mean MAE | Infer ms/sample | Params | Pareto |
|---:|---|---:|---:|---:|---:|---:|
| 1 | Gradient Boosting | 0.940468 | 1.000987 | 0.012620 | 1540 | yes |
| 2 | Polynomial (deg=3) | 0.893409 | 1.468237 | 0.010871 | 56 | yes |
| 3 | Polynomial (deg=2) | 0.855446 | 2.243295 | 0.010422 | 21 | yes |
| 4 | Random Forest | 0.801129 | 2.958975 | 0.703617 | 2520 | no |
| 5 | MLP 2-layer (Perceptron Gate) | 0.755227 | 2.004333 | 0.001236 | 141 | yes |
| 6 | SVR (RBF) | 0.741961 | 2.408699 | 0.010455 | 0 | no |
| 7 | Linear Regression | 0.698611 | 1.818940 | 0.004200 | 6 | no |
| 8 | MLP 3-layer (sklearn) | 0.516945 | 2.746813 | 0.013226 | 457 | no |

## Recommendation

- Recommended model: **Gradient Boosting**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.920468` (best Pareto R2 `0.940468` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.025239` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.948582 | 1.611169 | 1.367157 |
| ber | 0.945718 | 0.001995 | 0.001684 |
| noise_sigma | 0.975491 | 0.001290 | 0.001092 |
| hold_snm | 0.948582 | 1.611169 | 1.367157 |
| read_snm | 0.985497 | 0.932639 | 0.807278 |
| write_margin | 0.985354 | 7.766982 | 6.253386 |
| read_fail | 0.792170 | 0.000001 | 0.000001 |
| write_fail | 1.000000 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 1.372231 | 1.058377 | 1.646762 |
| ber | 0.001664 | 0.001211 | 0.002105 |
| noise_sigma | 0.001042 | 0.000748 | 0.001351 |
| hold_snm | 1.372231 | 1.021774 | 1.689870 |
| read_snm | 0.779922 | 0.574970 | 0.998848 |
| write_margin | 6.274695 | 4.417037 | 8.078762 |
| read_fail | 0.000001 | 0.000001 | 0.000002 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.181841 |
| ber | 0.000684 |
| noise_sigma | -0.002093 |
| hold_snm | -0.181841 |
| read_snm | 0.752078 |
| write_margin | 6.016543 |
| read_fail | -0.000000 |
| write_fail | 0.000000 |

## OOD Guardrails

- Training temp envelope: `233.15` to `358.15` K
- Training VDD envelope: `0.6300` to `0.7700` V
- Corners present: `ff, ss, tt`
- PDK IDs present: `asap7`
- Worst-corner rows covered: `1`
- Rule-based OOD flags should trigger when a deployment sample falls outside this temp/VDD/corner envelope.

## Monotonic Sanity (Dataset)

| Target | Violation Rate |
|---|---:|
| ber | 0.166667 |
| read_fail | 0.222222 |
| write_fail | 0.000000 |
| noise_sigma | 0.166667 |

- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.
