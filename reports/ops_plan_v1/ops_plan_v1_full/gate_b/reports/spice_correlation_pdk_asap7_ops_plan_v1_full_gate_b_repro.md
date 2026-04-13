# SPICE Correlation Report

- Generated: 2026-04-13T13:52:31.349702+00:00
- Data source: `predictive-pdk-pre-silicon`
- SPICE source: `pdk:asap7`
- Simulator: `xyce`
- External sim command token: `"C:\Program`
- External sim timeout (sec): `300`
- PDK ID: `asap7`
- PDK class: `predictive`
- Model revision: `asap7-openroad-local-xyce-l107`
- Macro mode: `6t-cell`
- PDK license: `BSD-3-Clause`
- Model root: `vendor/pdks/asap7_pdk_r1p7`
- PDK registry: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\pdk_registry.json`
- PDK config: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\configs\pdk_runs_external\asap7.json`
- Native backend: `hybrid`
- Measure contract revision: `v3-ber-contract-aligned-2026-02-18`
- PVT grid: corners=`tt,ff,ss` temps_k=`233.15,298.15,358.15` vdds=`0.63,0.70,0.77`
- Operating points: `27`
- Raw CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_asap7_ops_plan_v1_full_gate_b_repro.csv`
- Native flags: noise=`True` variability=`True` thermal=`True` seed=`None`
- SPICE MC: mode=`off` runs=`1` seed=`20260218`
- SPICE MC effective mode: `off`
- Mean SPICE runtime per operating point (ms): `159.209019`
- Mean SPICE runtime per MC sample (ms): `159.209019`
- Mean Native runtime per operating point (ms): `120.778926`
- SNM/Noise contract mode: `affine_corner_temp`
- Allow contract fallback: `False`
- BER contract mode: `native_fit`
- BER contract params (center/slope mV): `141.531249 / 201.943257` (fit samples `27`)
- Proxy config: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\calibration\default_spice_proxy.json`

## Error Summary

| Metric | Value |
|---|---:|
| MAE(SNM mV) | 3.070962 |
| MAE(SNM mV raw-native) | 159.136291 |
| MAE(noise) | 0.001102 |
| MAE(BER) | 0.003780 |
| MAE(log10 BER) | 0.003538 |
| Max |delta BER| | 0.008781 |
| MAE(BER raw-native) | 0.509299 |
| MAE(log10 BER raw-native) | 2.957257 |
| Max |delta BER| raw-native | 0.560873 |
| MAE(BER contract) | 0.003780 |
| MAE(log10 BER contract) | 0.003538 |
| Max |delta BER| contract | 0.008781 |
| MAE(Hold SNM mV) | 3.070962 |
| MAE(Read SNM mV) | 3.098525 |
| MAE(Write Margin mV) | 8.195429 |
| MAE(Noise Sigma) | 0.001102 |
| MAE(Noise Sigma raw-native) | 0.396254 |
| MAE(Read Fail) | 0.000002 |
| MAE(Read Fail raw-native) | 0.777713 |
| MAE(Write Fail) | 0.000000 |
| MAE(Write Fail raw-native) | 0.023581 |

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
| snm_mv | spice_snm_mv_raw | spice_snm_mv_raw | 325.025503 | 27 | no | no | usable | fitted | 0 | 9 | 0.022561 | 168.198280 | 27 |
| hold_snm_mv | spice_snm_mv_raw | spice_snm_mv_raw | 325.025503 | 27 | no | no | usable | fitted | 0 | 9 | 0.022561 | 168.198280 | 27 |
| read_snm_mv | n/a | spice_read_snm_mv_raw | 592.263000 | 27 | no | no | usable | fitted | 0 | 9 | 0.000967 | 156.668859 | 27 |
| write_margin_mv | n/a | spice_write_margin_mv_raw | 700.905990 | 27 | no | no | usable | fitted | 0 | 9 | 0.139163 | 561.441296 | 27 |
| noise | n/a | spice_noise_raw | 0.340548 | 27 | no | no | usable | fitted | 0 | 9 | -0.017130 | 0.124635 | 27 |
| noise_sigma | n/a | spice_noise_sigma_raw | 0.340548 | 27 | no | no | usable | fitted | 0 | 9 | -0.017130 | 0.124635 | 27 |

## Notes

- The bundled template uses simplified compact models; replace with PDK-calibrated models for signoff.
- v2 metrics are proxy-compatible unless the template emits physically extracted metrics.
- Keep this report in version control with the exact command line used.
