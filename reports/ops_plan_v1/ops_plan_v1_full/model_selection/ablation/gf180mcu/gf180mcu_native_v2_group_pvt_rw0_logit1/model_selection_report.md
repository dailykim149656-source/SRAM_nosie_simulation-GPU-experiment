# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:24:32.421214+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `native_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `False`
- Split mode: `group_pvt`
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
| 1 | MLP 3-layer (sklearn) | 0.837773 | 3.078893 | 0.007662 | 505 | yes |
| 2 | Gradient Boosting | 0.821409 | 0.075974 | 0.008165 | 1540 | no |
| 3 | Polynomial (deg=3) | 0.820506 | 0.770193 | 0.009226 | 120 | no |
| 4 | Random Forest | 0.819135 | 0.526935 | 0.593998 | 3766 | no |
| 5 | MLP 2-layer (Perceptron Gate) | 0.816343 | 0.678312 | 0.001159 | 181 | yes |
| 6 | Polynomial (deg=2) | 0.810907 | 2.249010 | 0.007706 | 36 | no |
| 7 | SVR (RBF) | 0.791458 | 3.365992 | 0.007449 | 0 | no |
| 8 | Linear Regression | 0.775199 | 0.221877 | 0.002275 | 8 | no |

## Recommendation

- Recommended model: **MLP 3-layer (sklearn)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.817773` (best Pareto R2 `0.837773` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.015324` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.972608 | 2.844078 | 2.151443 |
| ber | 0.944565 | 0.001151 | 0.000888 |
| noise_sigma | 0.916188 | 0.004685 | 0.003387 |
| hold_snm | 0.972608 | 2.844078 | 2.151443 |
| read_snm | 0.969091 | 3.275337 | 2.487184 |
| write_margin | 0.952836 | 30.485275 | 22.658633 |
| read_fail | 0.999927 | 0.000000 | 0.000000 |
| write_fail | 0.261889 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 2.151443 | 1.607003 | 2.785953 |
| ber | 0.000888 | 0.000673 | 0.001103 |
| noise_sigma | 0.003387 | 0.002567 | 0.004722 |
| hold_snm | 2.151443 | 1.675757 | 2.729145 |
| read_snm | 2.487184 | 1.811983 | 3.314039 |
| write_margin | 22.658633 | 16.587023 | 29.617521 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | -0.827174 |
| ber | 0.000819 |
| noise_sigma | 0.002937 |
| hold_snm | -0.827174 |
| read_snm | -1.436724 |
| write_margin | 0.188997 |
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
