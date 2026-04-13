# Gate B Summary

- Generated: 2026-04-13T13:55:24.077412+00:00
- Report glob: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\reports\ops_plan_v1\ops_plan_v1_full\gate_b\reports\spice_correlation_pdk_*.md`
- Pareto dir: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/model_selection/baseline`
- Thresholds: snm<=10.0, noise_sigma<=0.02, log10_ber<=0.35, max_delta_ber<=0.05, latency_gain>=50.0

| PDK | MAE SNM | MAE Noise Sigma | MAE log10 BER | Max Delta BER | Best Infer ms | Latency Gain x | Gate B |
|---|---:|---:|---:|---:|---:|---:|---|
| asap7 | 3.070962 | 0.001102 | 0.003538 | 0.008781 | 0.001236 | 128778.325002 | pass |
| freepdk45_openram | 3.843994 | 0.003469 | 0.004975 | 0.013533 | 0.001356 | 1032340.231577 | pass |
| gf180mcu | 7.580673 | 0.002377 | 0.002212 | 0.005315 | 0.000822 | 3165890.137507 | pass |
| sky130 | 3.821171 | 0.001131 | 0.000990 | 0.004616 | 0.000762 | 4509056.890940 | pass |
