# SPICE Correlation Report

- Generated: 2026-04-13T14:36:56.729197+00:00
- Data source: `foundry-pdk-pre-silicon`
- SPICE source: `pdk:gf180mcu`
- Simulator: `ngspice`
- External sim command token: `n/a`
- External sim timeout (sec): `900`
- PDK ID: `gf180mcu`
- PDK class: `foundry-open`
- Model revision: `gf180mcu-open-local`
- Macro mode: `6t-cell`
- PDK license: `Apache-2.0`
- Model root: `vendor/pdks/gf180mcu_fd_pr`
- PDK registry: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\pdk_registry.json`
- PDK config: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\configs\pdk_runs\gf180mcu.json`
- Native backend: `hybrid`
- Measure contract revision: `v3-ber-contract-aligned-2026-02-18`
- PVT grid: corners=`tt,ff,ss,sf,fs` temps_k=`233.15,298.15,398.15` vdds=`1.62,1.80,1.98`
- Operating points: `45`
- Raw CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/parallel/workers_4/repeat_2/results/spice_vs_native_pdk_gf180mcu_matrix_parallel_w4_r2.csv`
- Native flags: noise=`True` variability=`True` thermal=`True` seed=`None`
- SPICE MC: mode=`off` runs=`1` seed=`20260218`
- SPICE MC effective mode: `off`
- Mean SPICE runtime per operating point (ms): `4319.636696`
- Mean SPICE runtime per MC sample (ms): `4319.636696`
- Mean Native runtime per operating point (ms): `324.555942`
- SNM/Noise contract mode: `affine_corner_temp`
- Allow contract fallback: `False`
- BER contract mode: `native_fit`
- BER contract params (center/slope mV): `-58.175753 / 883.383169` (fit samples `45`)
- Proxy config: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\calibration\default_spice_proxy.json`

## Error Summary

| Metric | Value |
|---|---:|
| MAE(SNM mV) | 8.967679 |
| MAE(SNM mV raw-native) | 267.591418 |
| MAE(noise) | 0.001744 |
| MAE(BER) | 0.002449 |
| MAE(log10 BER) | 0.002617 |
| Max |delta BER| | 0.007168 |
| MAE(BER raw-native) | 0.594034 |
| MAE(log10 BER raw-native) | 0.391593 |
| Max |delta BER| raw-native | 0.602220 |
| MAE(BER contract) | 0.002449 |
| MAE(log10 BER contract) | 0.002617 |
| Max |delta BER| contract | 0.007168 |
| MAE(Hold SNM mV) | 8.967679 |
| MAE(Read SNM mV) | 6.419987 |
| MAE(Write Margin mV) | 46.100683 |
| MAE(Noise Sigma) | 0.001744 |
| MAE(Noise Sigma raw-native) | 0.646393 |
| MAE(Read Fail) | 0.000000 |
| MAE(Read Fail raw-native) | 0.999662 |
| MAE(Write Fail) | 0.000000 |
| MAE(Write Fail raw-native) | 0.000000 |

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
| snm_mv | spice_snm_mv_raw | spice_snm_mv_raw | 51.539018 | 45 | no | no | usable | fitted | 1 | 15 | 0.610908 | 271.777705 | 45 |
| hold_snm_mv | spice_snm_mv_raw | spice_snm_mv_raw | 51.539018 | 45 | no | no | usable | fitted | 1 | 15 | 0.610908 | 271.777705 | 45 |
| read_snm_mv | n/a | spice_read_snm_mv_raw | 1850.577300 | 45 | no | no | usable | fitted | 0 | 15 | -0.008706 | 264.445325 | 45 |
| write_margin_mv | n/a | spice_write_margin_mv_raw | 1832.805000 | 45 | no | no | usable | fitted | 0 | 15 | 0.069638 | 1676.249960 | 45 |
| noise | n/a | spice_noise_raw | 0.511155 | 45 | no | no | usable | fitted | 0 | 15 | -0.011214 | 0.061239 | 45 |
| noise_sigma | n/a | spice_noise_sigma_raw | 0.511155 | 45 | no | no | usable | fitted | 0 | 15 | -0.011214 | 0.061239 | 45 |

## Notes

- The bundled template uses simplified compact models; replace with PDK-calibrated models for signoff.
- v2 metrics are proxy-compatible unless the template emits physically extracted metrics.
- Keep this report in version control with the exact command line used.
