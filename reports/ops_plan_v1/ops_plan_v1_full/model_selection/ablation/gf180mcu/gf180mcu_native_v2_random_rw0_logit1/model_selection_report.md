# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:16:05.115489+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `native_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
- Split mode: `random`
- Target clip quantile: `0.01`
- Target normalize: `True`
- Target prob-logit: `True`
- Fail aux split (`read_fail/write_fail` dedicated heads): `False`
- Fail aux profile (requested -> resolved): `gf180mcu -> gf180mcu`
- R2 clip range: `[-10.0, 1.0]`
- Target importance (weighted aggregation): `snm=1.00, ber=1.50, noise_sigma=1.30, hold_snm=1.00, read_snm=1.20, write_margin=1.20, read_fail=2.00, write_fail=2.00`
- Samples: `45`
- Features: `temp_k, vdd, corner_ff, corner_fs, corner_sf, corner_ss, corner_tt`
- Cross-validation folds used: `5`

## Leaderboard

| Rank | Model | Mean R2 | Mean MAE | Infer ms/sample | Params | Pareto |
|---:|---|---:|---:|---:|---:|---:|
| 1 | MLP 3-layer (sklearn) | 0.843581 | 3.111524 | 0.010009 | 505 | yes |
| 2 | Gradient Boosting | 0.821375 | 0.131414 | 0.009300 | 1540 | yes |
| 3 | Polynomial (deg=3) | 0.818667 | 1.158000 | 0.006577 | 120 | yes |
| 4 | MLP 2-layer (Perceptron Gate) | 0.811217 | 0.905961 | 0.000703 | 181 | yes |
| 5 | SVR (RBF) | 0.792774 | 3.381002 | 0.007940 | 0 | no |
| 6 | Polynomial (deg=2) | 0.792277 | 2.761285 | 0.005539 | 36 | no |
| 7 | Random Forest | 0.783855 | 1.528042 | 0.381981 | 3548 | no |
| 8 | Linear Regression | 0.730511 | 0.294880 | 0.001551 | 8 | no |

## Recommendation

- Recommended model: **MLP 3-layer (sklearn)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.823581` (best Pareto R2 `0.843581` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.020018` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.962876 | 2.989498 | 2.317730 |
| ber | 0.958604 | 0.000896 | 0.000707 |
| noise_sigma | 0.918030 | 0.003943 | 0.002880 |
| hold_snm | 0.962876 | 2.989498 | 2.317730 |
| read_snm | 0.955768 | 3.445297 | 2.678534 |
| write_margin | 0.952567 | 29.490649 | 22.495466 |
| read_fail | 0.999927 | 0.000000 | 0.000000 |
| write_fail | 0.300580 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 2.317730 | 1.671066 | 2.888899 |
| ber | 0.000707 | 0.000535 | 0.000897 |
| noise_sigma | 0.002880 | 0.001966 | 0.003824 |
| hold_snm | 2.317730 | 1.615637 | 2.906970 |
| read_snm | 2.678534 | 1.956473 | 3.515186 |
| write_margin | 22.495466 | 16.471251 | 29.232041 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 6.661283 |
| ber | -0.001100 |
| noise_sigma | 0.003895 |
| hold_snm | 6.661283 |
| read_snm | 6.841907 |
| write_margin | 52.284023 |
| read_fail | 0.000000 |
| write_fail | 0.000000 |

## OOD Guardrails

- Training temp envelope: `233.15` to `398.15` K
- Training VDD envelope: `1.6200` to `1.9800` V
- Corners present: `ff, fs, sf, ss, tt`
- PDK IDs present: `gf180mcu`
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
