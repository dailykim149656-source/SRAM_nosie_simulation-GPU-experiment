# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:13:16.664513+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `delta_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
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
| 1 | Random Forest | 0.088598 | 10.454917 | 0.346501 | 4258 | yes |
| 2 | MLP 2-layer (Perceptron Gate) | -0.038458 | 10.472912 | 0.000985 | 181 | yes |
| 3 | Polynomial (deg=2) | -0.083538 | 11.410014 | 0.004305 | 36 | no |
| 4 | MLP 3-layer (sklearn) | -0.123078 | 11.067117 | 0.014427 | 505 | no |
| 5 | Linear Regression | -0.149025 | 10.562786 | 0.001408 | 8 | no |
| 6 | Gradient Boosting | -0.268722 | 13.567083 | 0.007330 | 1540 | no |
| 7 | Polynomial (deg=3) | -0.423972 | 14.130657 | 0.005048 | 120 | no |
| 8 | SVR (RBF) | -0.638949 | 13.764885 | 0.007916 | 0 | no |

## Recommendation

- Recommended model: **Random Forest**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.068598` (best Pareto R2 `0.088598` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.693002` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.212065 | 8.182726 | 7.256699 |
| ber | 0.213654 | 0.002234 | 0.001979 |
| noise_sigma | 0.198385 | 0.002896 | 0.002181 |
| hold_snm | 0.212065 | 8.182726 | 7.256699 |
| read_snm | 0.102903 | 8.276127 | 7.326385 |
| write_margin | -1.778054 | 87.951796 | 78.153504 |
| read_fail | 0.999983 | 0.000000 | 0.000000 |
| write_fail | -0.000000 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 7.256699 | 6.187160 | 8.416273 |
| ber | 0.001979 | 0.001627 | 0.002377 |
| noise_sigma | 0.002181 | 0.001451 | 0.002868 |
| hold_snm | 7.256699 | 6.106710 | 8.378191 |
| read_snm | 7.326385 | 6.180397 | 8.744332 |
| write_margin | 78.153504 | 68.327443 | 91.477891 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 5.196944 |
| ber | -0.001419 |
| noise_sigma | 0.000586 |
| hold_snm | 5.196944 |
| read_snm | -4.199077 |
| write_margin | -28.328060 |
| read_fail | 0.000000 |
| write_fail | 0.000001 |

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
| ber | 0.366667 |
| read_fail | 0.433333 |
| write_fail | 0.000000 |
| noise_sigma | 0.400000 |

- Violation means a fail-like metric improved when VDD decreased within same corner/temp group.
