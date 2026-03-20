# Gate B Summary

- Generated: 2026-03-09T04:55:33.740923+00:00
- Report glob: `spice_validation/reports/spice_correlation_pdk_*_matrix_fullpvt_xyce_mixed_contractfix_20260309.md`
- Pareto dir: `reports/pdk_phase2_n27_xyce_contractfix_20260309`
- Thresholds: snm<=10.0, noise_sigma<=0.02, log10_ber<=0.35, max_delta_ber<=0.05, latency_gain>=50.0

| PDK | MAE SNM | MAE Noise Sigma | MAE log10 BER | Max Delta BER | Best Infer ms | Latency Gain x | Gate B |
|---|---:|---:|---:|---:|---:|---:|---|
| asap7 | 3.070962 | 0.001102 | 0.003538 | 0.008781 | 0.097076 | 2261.777598 | pass |
| freepdk45_openram | 3.843994 | 0.003469 | 0.004975 | 0.013533 | 0.085497 | 22990.634213 | pass |
| gf180mcu | 7.728580 | 0.001916 | 0.002258 | 0.007202 | 0.128262 | 15132.296424 | pass |
| sky130 | 3.821171 | 0.001131 | 0.000990 | 0.004616 | 0.083091 | 36968.884805 | pass |
