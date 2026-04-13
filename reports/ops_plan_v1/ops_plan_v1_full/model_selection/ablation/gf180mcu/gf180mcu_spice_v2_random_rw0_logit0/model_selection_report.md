# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:15:30.898621+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `spice_v2`
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
| 1 | MLP 2-layer (Perceptron Gate) | 0.776440 | 10.188822 | 0.000849 | 181 | yes |
| 2 | Random Forest | 0.748938 | 10.145474 | 0.494099 | 3968 | no |
| 3 | Linear Regression | 0.738993 | 10.232550 | 0.001613 | 8 | no |
| 4 | Polynomial (deg=2) | 0.721588 | 11.166763 | 0.006352 | 36 | no |
| 5 | Gradient Boosting | 0.619146 | 13.007622 | 0.013821 | 1540 | no |
| 6 | Polynomial (deg=3) | 0.598409 | 12.906920 | 0.008317 | 120 | no |
| 7 | SVR (RBF) | 0.358960 | 13.949708 | 0.009547 | 0 | no |
| 8 | MLP 3-layer (sklearn) | -1.241526 | 10.712436 | 0.008813 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.756440` (best Pareto R2 `0.776440` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001697` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.612583 | 8.383673 | 7.534775 |
| ber | 0.626324 | 0.002248 | 0.002057 |
| noise_sigma | 0.965723 | 0.002512 | 0.001784 |
| hold_snm | 0.612583 | 8.383673 | 7.534775 |
| read_snm | 0.664641 | 8.659074 | 7.814903 |
| write_margin | 0.398824 | 84.473694 | 74.718304 |
| read_fail | 0.999981 | 0.000000 | 0.000000 |
| write_fail | 0.999960 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 7.534775 | 6.481875 | 8.581607 |
| ber | 0.002057 | 0.001756 | 0.002360 |
| noise_sigma | 0.001784 | 0.001325 | 0.002283 |
| hold_snm | 7.534775 | 6.412070 | 8.685449 |
| read_snm | 7.814903 | 6.644225 | 8.897762 |
| write_margin | 74.718304 | 64.478385 | 87.304922 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -5.779687 |
| ber | 0.001341 |
| noise_sigma | 0.000744 |
| hold_snm | -5.779687 |
| read_snm | 3.402505 |
| write_margin | 21.692685 |
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
| ber | 0.300000 |
| read_fail | 0.266667 |
| write_fail | 0.000000 |
| noise_sigma | 0.266667 |

- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.
