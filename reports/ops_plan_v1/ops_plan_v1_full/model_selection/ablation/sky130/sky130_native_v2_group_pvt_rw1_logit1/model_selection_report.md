# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:04:39.313698+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `native_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
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
| 1 | Gradient Boosting | 0.821408 | 0.059645 | 0.007018 | 1540 | yes |
| 2 | Polynomial (deg=3) | 0.820762 | 0.642083 | 0.004814 | 120 | yes |
| 3 | Random Forest | 0.819432 | 0.467252 | 0.307292 | 3744 | no |
| 4 | MLP 2-layer (Perceptron Gate) | 0.817843 | 0.642935 | 0.000779 | 181 | yes |
| 5 | Polynomial (deg=2) | 0.811380 | 2.134195 | 0.004792 | 36 | no |
| 6 | SVR (RBF) | 0.793518 | 3.321194 | 0.008980 | 0 | no |
| 7 | Linear Regression | 0.782829 | 0.156386 | 0.001494 | 8 | no |
| 8 | MLP 3-layer (sklearn) | 0.754192 | 3.396659 | 0.010099 | 505 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.801408` (best Pareto R2 `0.821408` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.001558` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.996854 | 0.965149 | 0.557866 |
| ber | 0.994330 | 0.000314 | 0.000221 |
| noise_sigma | 0.984811 | 0.001648 | 0.001152 |
| hold_snm | 0.996854 | 0.965149 | 0.557866 |
| read_snm | 0.996859 | 1.033151 | 0.623781 |
| write_margin | 0.998543 | 5.622250 | 4.445640 |
| read_fail | 0.999951 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 0.557866 | 0.352852 | 0.798255 |
| ber | 0.000221 | 0.000172 | 0.000295 |
| noise_sigma | 0.001152 | 0.000822 | 0.001562 |
| hold_snm | 0.557866 | 0.333441 | 0.801213 |
| read_snm | 0.623781 | 0.414693 | 0.893313 |
| write_margin | 4.445640 | 3.424414 | 5.347179 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.022933 |
| ber | -0.000081 |
| noise_sigma | 0.002009 |
| hold_snm | -0.022933 |
| read_snm | -0.323554 |
| write_margin | 2.090052 |
| read_fail | 0.000000 |
| write_fail | 0.000001 |

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
