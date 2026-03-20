# Model Selection Report (Phase 2)

- Generated: 2026-03-09T04:36:03.749594+00:00
- Data source: `foundry-pdk-pre-silicon`
- Input CSV: `not bundled in public snapshot`
- PDK id: `sky130`
- Target Source: `spice_v2`
- Targets: `snm, ber, noise_sigma, hold_snm, read_snm, write_margin, read_fail, write_fail`
- Risk weighting: `True`
- Split mode: `group_pvt`
- Samples: `45`
- Features: `temp_k, vdd, corner_ff, corner_fs, corner_sf, corner_ss, corner_tt`
- Cross-validation folds used: `5`

## Leaderboard

| Rank | Model | Mean R2 | Mean MAE | Infer ms/sample | Params | Pareto |
|---:|---|---:|---:|---:|---:|---:|
| 1 | MLP 3-layer (sklearn) | 0.728322 | 6.834313 | 0.083091 | 505 | yes |
| 2 | Polynomial (deg=3) | 0.719340 | 5.710323 | 0.067006 | 120 | yes |
| 3 | MLP 2-layer (Perceptron Gate) | 0.717861 | 6.182323 | 0.016356 | 181 | yes |
| 4 | Random Forest | 0.708615 | 6.220209 | 6.251983 | 3868 | no |
| 5 | Polynomial (deg=2) | 0.708154 | 6.858017 | 0.039762 | 36 | no |
| 6 | Linear Regression | 0.699859 | 6.429427 | 0.035997 | 8 | no |
| 7 | Gradient Boosting | 0.698484 | 6.271021 | 0.015905 | 1540 | yes |
| 8 | SVR (RBF) | 0.569070 | 8.354196 | 0.059621 | 0 | no |

## Recommendation

- Recommended model: **MLP 2-layer (Perceptron Gate)**

| Target | R2 | RMSE | MAE |
|---|---:|---:|---:|
| snm | 0.816239 | 6.545204 | 5.278709 |
| ber | 0.823192 | 0.001566 | 0.001284 |
| noise_sigma | 0.972808 | 0.002173 | 0.001563 |
| hold_snm | 0.816239 | 6.545204 | 5.278709 |
| read_snm | 0.832241 | 6.769393 | 5.458922 |
| write_margin | 0.757945 | 56.072516 | 43.441608 |
| read_fail | 0.999950 | 0.000000 | 0.000000 |
| write_fail | 0.000000 | 0.000001 | 0.000001 |

## Notes

- This report is kept as a representative public snapshot.
- The matching full result family and auxiliary pareto CSVs are intentionally not bundled here.
