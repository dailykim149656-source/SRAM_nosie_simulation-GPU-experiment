# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:03:05.399472+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `sky130`
- Target Source: `delta_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
- Split mode: `random`
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
| 1 | Random Forest | -0.057457 | 6.488506 | 0.298610 | 4368 | yes |
| 2 | SVR (RBF) | -0.073410 | 5.337756 | 0.006539 | 0 | yes |
| 3 | Linear Regression | -0.267393 | 7.673736 | 0.001237 | 8 | yes |
| 4 | MLP 2-layer (Perceptron Gate) | -0.285807 | 7.553871 | 0.000644 | 181 | yes |
| 5 | Polynomial (deg=2) | -0.528224 | 8.645020 | 0.004221 | 36 | no |
| 6 | Polynomial (deg=3) | -0.701413 | 7.769263 | 0.004607 | 120 | no |
| 7 | Gradient Boosting | -1.039156 | 8.077530 | 0.006804 | 1540 | no |
| 8 | MLP 3-layer (sklearn) | -1.756496 | 5.037871 | 0.007437 | 505 | no |

## Recommendation

- Recommended model: **SVR (RBF)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `-0.077457` (best Pareto R2 `-0.057457` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.013079` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | -0.537119 | 7.445744 | 4.711064 |
| ber | -0.699729 | 0.001887 | 0.001217 |
| noise_sigma | -1.032417 | 0.002274 | 0.001501 |
| hold_snm | -0.537119 | 7.445744 | 4.711064 |
| read_snm | -0.568132 | 7.747194 | 4.924955 |
| write_margin | -0.562014 | 64.112262 | 37.039182 |
| read_fail | 0.999979 | 0.000000 | 0.000000 |
| write_fail | 1.000000 | 0.000000 | 0.000000 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 4.711064 | 3.051828 | 6.661738 |
| ber | 0.001217 | 0.000786 | 0.001688 |
| noise_sigma | 0.001501 | 0.000996 | 0.002149 |
| hold_snm | 4.711064 | 3.100694 | 6.514035 |
| read_snm | 4.924955 | 2.984904 | 6.837612 |
| write_margin | 37.039182 | 22.369917 | 51.715851 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000000 | 0.000000 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.246330 |
| ber | 0.000065 |
| noise_sigma | 0.000088 |
| hold_snm | -0.246330 |
| read_snm | -0.298993 |
| write_margin | -1.656945 |
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
