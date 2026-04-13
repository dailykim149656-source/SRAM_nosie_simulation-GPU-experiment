# SPICE Correlation Report

- Generated: 2026-04-13T13:49:36.229183+00:00
- Data source: `foundry-pdk-pre-silicon`
- SPICE source: `pdk:sky130`
- Simulator: `ngspice`
- External sim command token: `n/a`
- External sim timeout (sec): `900`
- PDK ID: `sky130`
- PDK class: `foundry-open`
- Model revision: `sky130-open-local`
- Macro mode: `6t-cell`
- PDK license: `Apache-2.0`
- Model root: `vendor/pdks/sky130_fd_pr`
- PDK registry: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\pdk_registry.json`
- PDK config: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\configs\pdk_runs\sky130.json`
- Native backend: `hybrid`
- Measure contract revision: `v3-ber-contract-aligned-2026-02-18`
- PVT grid: corners=`tt,ff,ss,sf,fs` temps_k=`233.15,298.15,373.15` vdds=`1.60,1.80,1.95`
- Operating points: `45`
- Raw CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_sky130_ops_plan_v1_full_gate_b_repro.csv`
- Native flags: noise=`True` variability=`True` thermal=`True` seed=`None`
- SPICE MC: mode=`off` runs=`1` seed=`20260218`
- SPICE MC effective mode: `off`
- Mean SPICE runtime per operating point (ms): `3437.279180`
- Mean SPICE runtime per MC sample (ms): `3437.279180`
- Mean Native runtime per operating point (ms): `76.247442`
- SNM/Noise contract mode: `affine_corner_temp`
- Allow contract fallback: `False`
- BER contract mode: `native_fit`
- BER contract params (center/slope mV): `-106.303696 / 996.344111` (fit samples `45`)
- Proxy config: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\calibration\default_spice_proxy.json`

## Error Summary

| Metric | Value |
|---|---:|
| MAE(SNM mV) | 3.821171 |
| MAE(SNM mV raw-native) | 278.079559 |
| MAE(noise) | 0.001131 |
| MAE(BER) | 0.000925 |
| MAE(log10 BER) | 0.000990 |
| Max |delta BER| | 0.004616 |
| MAE(BER raw-native) | 0.595254 |
| MAE(log10 BER raw-native) | 0.392853 |
| Max |delta BER| raw-native | 0.600580 |
| MAE(BER contract) | 0.000925 |
| MAE(log10 BER contract) | 0.000990 |
| Max |delta BER| contract | 0.004616 |
| MAE(Hold SNM mV) | 3.821171 |
| MAE(Read SNM mV) | 3.950969 |
| MAE(Write Margin mV) | 33.302983 |
| MAE(Noise Sigma) | 0.001131 |
| MAE(Noise Sigma raw-native) | 0.736329 |
| MAE(Read Fail) | 0.000000 |
| MAE(Read Fail raw-native) | 0.999982 |
| MAE(Write Fail) | 0.000000 |
| MAE(Write Fail raw-native) | 0.000001 |

## SPICE Proxy Parameters

| Key | Value |
|---|---:|
| snm_scale_mv | 500.000000 |
| noise_scale | 1.000000 |
| noise_write_weight | 0.500000 |
| ber_center_mv | 120.000000 |
| ber_slope_mv | 10.000000 |

## Contract Fit Summary

| Metric | Requested Raw Source | Chosen Raw Source | Span | Finite | Fallback | Invalid Raw | Reason | Fit Status | Group Fallbacks | Groups | Global a | Global b | Samples |
|---|---|---|---:|---:|---|---|---|---|---:|---:|---:|---:|---:|
| snm_mv | spice_read_snm_mv_raw | spice_read_snm_mv_raw | 1688.279100 | 45 | no | no | usable | fitted | 0 | 15 | -0.004997 | 274.134613 | 45 |
| hold_snm_mv | spice_read_snm_mv_raw | spice_read_snm_mv_raw | 1688.279100 | 45 | no | no | usable | fitted | 0 | 15 | -0.004997 | 274.134613 | 45 |
| read_snm_mv | n/a | spice_read_snm_mv_raw | 1688.279100 | 45 | no | no | usable | fitted | 0 | 15 | -0.004919 | 268.035469 | 45 |
| write_margin_mv | n/a | spice_write_margin_mv_raw | 1808.902000 | 45 | no | no | usable | fitted | 0 | 15 | 0.037510 | 1711.129409 | 45 |
| noise | n/a | spice_noise_raw | 0.479545 | 45 | no | no | usable | fitted | 0 | 15 | -0.021115 | 0.067974 | 45 |
| noise_sigma | n/a | spice_noise_sigma_raw | 0.479545 | 45 | no | no | usable | fitted | 0 | 15 | -0.021115 | 0.067974 | 45 |

## Notes

- The bundled template uses simplified compact models; replace with PDK-calibrated models for signoff.
- v2 metrics are proxy-compatible unless the template emits physically extracted metrics.
- Keep this report in version control with the exact command line used.
