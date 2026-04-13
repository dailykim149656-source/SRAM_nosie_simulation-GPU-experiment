# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:16:43.592800+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `native_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
- Split mode: `random`
- Target clip quantile: `0.01`
- Target normalize: `True`
- Target prob-logit: `False`
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
| 1 | Gradient Boosting | 0.999958 | 0.131414 | 0.007599 | 1540 | yes |
| 2 | Polynomial (deg=3) | 0.997255 | 1.158000 | 0.006477 | 120 | yes |
| 3 | MLP 2-layer (Perceptron Gate) | 0.989783 | 0.905961 | 0.000625 | 181 | yes |
| 4 | SVR (RBF) | 0.971350 | 3.381002 | 0.007345 | 0 | no |
| 5 | Polynomial (deg=2) | 0.970991 | 2.761284 | 0.005283 | 36 | no |
| 6 | Random Forest | 0.962441 | 1.528042 | 0.418270 | 3548 | no |
| 7 | Linear Regression | 0.909044 | 0.294880 | 0.001635 | 8 | no |
| 8 | MLP 3-layer (sklearn) | -0.995826 | 3.243129 | 0.007622 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.979958` (best Pareto R2 `0.999958` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001250` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.994399 | 1.186623 | 0.803700 |
| ber | 0.992349 | 0.000386 | 0.000277 |
| noise_sigma | 0.939091 | 0.003243 | 0.002448 |
| hold_snm | 0.994399 | 1.186623 | 0.803700 |
| read_snm | 0.992855 | 1.446127 | 1.034056 |
| write_margin | 0.996774 | 7.491027 | 6.079082 |
| read_fail | 0.999976 | 0.000000 | 0.000000 |
| write_fail | 0.999960 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 0.803700 | 0.466255 | 1.134467 |
| ber | 0.000277 | 0.000181 | 0.000400 |
| noise_sigma | 0.002448 | 0.001488 | 0.003194 |
| hold_snm | 0.803700 | 0.476977 | 1.133496 |
| read_snm | 1.034056 | 0.644122 | 1.361555 |
| write_margin | 6.079082 | 4.595327 | 7.736211 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.371400 |
| ber | -0.000033 |
| noise_sigma | 0.004055 |
| hold_snm | -0.371400 |
| read_snm | -0.922634 |
| write_margin | 3.155383 |
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
