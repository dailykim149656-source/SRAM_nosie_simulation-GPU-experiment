# Model Selection Report (Phase 2)

- Generated: 2026-04-13T14:11:53.733026+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- PDK id: `gf180mcu`
- Target Source: `native_v2`
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
| 1 | MLP 3-layer (sklearn) | 0.837439 | 3.470284 | 0.007217 | 505 | yes |
| 2 | Gradient Boosting | 0.821378 | 0.142467 | 0.007502 | 1540 | no |
| 3 | Polynomial (deg=3) | 0.818712 | 1.153841 | 0.006152 | 120 | yes |
| 4 | MLP 2-layer (Perceptron Gate) | 0.810575 | 0.936581 | 0.000870 | 181 | yes |
| 5 | SVR (RBF) | 0.792774 | 3.381002 | 0.006798 | 0 | no |
| 6 | Polynomial (deg=2) | 0.791551 | 2.902457 | 0.005166 | 36 | no |
| 7 | Random Forest | 0.782625 | 1.555613 | 0.386243 | 3560 | no |
| 8 | Linear Regression | 0.743990 | 0.321579 | 0.001528 | 8 | no |

## Recommendation

- Recommended model: **MLP 3-layer (sklearn)**
- Deployment candidate: **MLP 2-layer (Perceptron Gate)**
- Accuracy ceiling: **MLP 3-layer (sklearn)**
- Rule step 1 (quality): Pareto models with R2 >= `0.817439` (best Pareto R2 `0.837439` - tolerance `0.020000`)
- Rule step 2 (speed): among quality candidates, keep models within `0.012304` ms/sample (2.00x fastest quality latency), then choose best R2

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.957340 | 3.183150 | 2.527040 |
| ber | 0.942534 | 0.001024 | 0.000804 |
| noise_sigma | 0.911343 | 0.004071 | 0.003036 |
| hold_snm | 0.957340 | 3.183150 | 2.527040 |
| read_snm | 0.944219 | 4.045194 | 3.271492 |
| write_margin | 0.942129 | 33.085779 | 24.901800 |
| read_fail | 0.999927 | 0.000000 | 0.000000 |
| write_fail | 0.301311 | 0.000001 | 0.000001 |

## Notes

- This report benchmarks model families under identical features/splits/metrics.
- `*_v2` target sources are noise-aware contract extensions and can include fail-rate style targets.
- For reproducibility, pair this file with the matching pareto CSV and fixed command lines.

## Bootstrap CI

| Target | MAE | MAE 95% CI Low | MAE 95% CI High |
|---|---:|---:|---:|
| snm | 2.527040 | 1.874434 | 3.117189 |
| ber | 0.000804 | 0.000610 | 0.001007 |
| noise_sigma | 0.003036 | 0.002155 | 0.003944 |
| hold_snm | 2.527040 | 1.874238 | 3.134091 |
| read_snm | 3.271492 | 2.593284 | 3.999925 |
| write_margin | 24.901800 | 18.020433 | 31.601070 |
| read_fail | 0.000000 | 0.000000 | 0.000000 |
| write_fail | 0.000001 | 0.000001 | 0.000001 |

## Worst-Corner Bias

- Definition: `SS` corner with high-temperature and low-VDD rows from the dataset envelope.

| Target | Signed Mean Error |
|---|---:|
| snm | 7.479171 |
| ber | -0.000903 |
| noise_sigma | 0.004604 |
| hold_snm | 7.479171 |
| read_snm | 7.723691 |
| write_margin | 70.414785 |
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
