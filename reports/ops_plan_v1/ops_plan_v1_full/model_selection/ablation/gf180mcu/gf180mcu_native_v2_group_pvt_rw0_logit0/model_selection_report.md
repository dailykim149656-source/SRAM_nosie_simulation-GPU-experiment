# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:25:09.454839+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `native_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
- Split mode: `group_pvt`
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
| 1 | Gradient Boosting | 0.999990 | 0.075973 | 0.007920 | 1540 | yes |
| 2 | Polynomial (deg=3) | 0.999094 | 0.770192 | 0.005454 | 120 | yes |
| 3 | Random Forest | 0.997711 | 0.526935 | 0.369978 | 3766 | no |
| 4 | MLP 2-layer (Perceptron Gate) | 0.994910 | 0.678312 | 0.000989 | 181 | yes |
| 5 | Polynomial (deg=2) | 0.989530 | 2.249010 | 0.004697 | 36 | no |
| 6 | SVR (RBF) | 0.970048 | 3.365991 | 0.008637 | 0 | no |
| 7 | Linear Regression | 0.953780 | 0.221877 | 0.001308 | 8 | no |
| 8 | MLP 3-layer (sklearn) | -0.994718 | 3.213898 | 0.008499 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.979990` (best Pareto R2 `0.999990` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001978` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.996989 | 1.017304 | 0.584925 |
| ber | 0.994475 | 0.000376 | 0.000267 |
| noise_sigma | 0.972209 | 0.002753 | 0.001808 |
| hold_snm | 0.996989 | 1.017304 | 0.584925 |
| read_snm | 0.996292 | 1.224836 | 0.713017 |
| write_margin | 0.998386 | 6.097760 | 4.640723 |
| read_fail | 0.999973 | 0.000000 | 0.000000 |
| write_fail | 0.999935 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 0.584925 | 0.356010 | 0.846564 |
| ber | 0.000267 | 0.000215 | 0.000351 |
| noise_sigma | 0.001808 | 0.001279 | 0.002572 |
| hold_snm | 0.584925 | 0.361043 | 0.834433 |
| read_snm | 0.713017 | 0.473156 | 0.989695 |
| write_margin | 4.640723 | 3.546896 | 5.798017 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.079106 |
| ber | -0.000093 |
| noise_sigma | 0.003000 |
| hold_snm | -0.079106 |
| read_snm | -0.500843 |
| write_margin | 2.662920 |
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
