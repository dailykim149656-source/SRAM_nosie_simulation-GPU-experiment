# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:02:33.407880+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `delta_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
- Split mode: `random`
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
| 1 | MLP 3-layer (sklearn) | 0.082521 | 4.905494 | 0.006255 | 505 | yes |
| 2 | Random Forest | -0.236028 | 6.488506 | 0.322121 | 4368 | no |
| 3 | SVR (RBF) | -0.251981 | 5.337756 | 0.005581 | 0 | yes |
| 4 | Linear Regression | -0.445964 | 7.673736 | 0.001346 | 8 | yes |
| 5 | MLP 2-layer (Perceptron Gate) | -0.464372 | 7.553871 | 0.000598 | 181 | yes |
| 6 | Polynomial (deg=2) | -0.706796 | 8.645020 | 0.004924 | 36 | no |
| 7 | Polynomial (deg=3) | -0.879985 | 7.769263 | 0.004517 | 120 | no |
| 8 | Gradient Boosting | -1.217728 | 8.077530 | 0.006434 | 1540 | no |

## Recommendation

- Recommended model: **MLP 3-layer (sklearn)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.062521` (best Pareto R2 `0.082521` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.012510` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | -0.175362 | 6.631948 | 3.944989 |
| ber | -0.277619 | 0.001666 | 0.001020 |
| noise_sigma | -0.184530 | 0.002043 | 0.001242 |
| hold_snm | -0.175362 | 6.631948 | 3.944989 |
| read_snm | -0.175883 | 6.854991 | 4.086438 |
| write_margin | -0.378837 | 60.525851 | 35.120571 |
| read_fail | 0.999974 | 0.000000 | 0.000000 |
| write_fail | 0.298496 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 3.944989 | 2.395231 | 5.591284 |
| ber | 0.001020 | 0.000633 | 0.001418 |
| noise_sigma | 0.001242 | 0.000773 | 0.001856 |
| hold_snm | 3.944989 | 2.457053 | 5.665538 |
| read_snm | 4.086438 | 2.412686 | 5.830103 |
| write_margin | 35.120571 | 19.867415 | 49.159680 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 0.041997 |
| ber | -0.000147 |
| noise_sigma | 0.000370 |
| hold_snm | 0.041997 |
| read_snm | 0.049794 |
| write_margin | -10.900511 |
| read_fail | -0.000000 |
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
