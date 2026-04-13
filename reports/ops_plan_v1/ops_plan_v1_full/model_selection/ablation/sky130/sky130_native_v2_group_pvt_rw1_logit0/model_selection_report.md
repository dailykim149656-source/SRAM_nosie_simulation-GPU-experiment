# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:05:20.885578+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `native_v2`
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
| 1 | Gradient Boosting | 0.999986 | 0.059644 | 0.008836 | 1540 | yes |
| 2 | Polynomial (deg=3) | 0.999343 | 0.642083 | 0.005855 | 120 | yes |
| 3 | Random Forest | 0.998003 | 0.467252 | 0.427139 | 3744 | no |
| 4 | MLP 2-layer (Perceptron Gate) | 0.996417 | 0.642934 | 0.000745 | 181 | yes |
| 5 | Polynomial (deg=2) | 0.989993 | 2.134194 | 0.004871 | 36 | no |
| 6 | SVR (RBF) | 0.972094 | 3.321194 | 0.009766 | 0 | no |
| 7 | Linear Regression | 0.961383 | 0.156386 | 0.001743 | 8 | no |
| 8 | MLP 3-layer (sklearn) | -1.077983 | 3.532215 | 0.006975 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.979986` (best Pareto R2 `0.999986` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001490` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.996854 | 0.965149 | 0.557866 |
| ber | 0.994389 | 0.000312 | 0.000220 |
| noise_sigma | 0.984811 | 0.001648 | 0.001152 |
| hold_snm | 0.996854 | 0.965149 | 0.557866 |
| read_snm | 0.996859 | 1.033151 | 0.623781 |
| write_margin | 0.998543 | 5.622250 | 4.445640 |
| read_fail | 0.999980 | 0.000000 | 0.000000 |
| write_fail | 0.999941 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 0.557866 | 0.352852 | 0.798255 |
| ber | 0.000220 | 0.000173 | 0.000293 |
| noise_sigma | 0.001152 | 0.000822 | 0.001562 |
| hold_snm | 0.557866 | 0.333441 | 0.801213 |
| read_snm | 0.623781 | 0.414693 | 0.893313 |
| write_margin | 4.445640 | 3.424414 | 5.347179 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.022933 |
| ber | -0.000078 |
| noise_sigma | 0.002009 |
| hold_snm | -0.022933 |
| read_snm | -0.323554 |
| write_margin | 2.090052 |
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
