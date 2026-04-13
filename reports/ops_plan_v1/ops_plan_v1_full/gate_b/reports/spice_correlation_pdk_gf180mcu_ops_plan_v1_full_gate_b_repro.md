# SPICE Correlation Report

- Generated: 2026-04-13T13:51:40.022398+00:00
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
- Raw CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/gate_b/results/spice_vs_native_pdk_gf180mcu_ops_plan_v1_full_gate_b_repro.csv`
- Native flags: noise=`True` variability=`True` thermal=`True` seed=`None`
- SPICE MC: mode=`off` runs=`1` seed=`20260218`
- SPICE MC effective mode: `off`
- Mean SPICE runtime per operating point (ms): `2601.394336`
- Mean SPICE runtime per MC sample (ms): `2601.394336`
- Mean Native runtime per operating point (ms): `129.747133`
- SNM/Noise contract mode: `affine_corner_temp`
- Allow contract fallback: `False`
- BER contract mode: `native_fit`
- BER contract params (center/slope mV): `-58.175753 / 883.383169` (fit samples `45`)
- Proxy config: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\calibration\default_spice_proxy.json`

## Error Summary

| Metric | Value |
|---|---:|
| MAE(SNM mV) | 7.580673 |
| MAE(SNM mV raw-native) | 268.290892 |
| MAE(noise) | 0.002377 |
| MAE(BER) | 0.002070 |
| MAE(log10 BER) | 0.002212 |
| Max |delta BER| | 0.005315 |
| MAE(BER raw-native) | 0.594054 |
| MAE(log10 BER raw-native) | 0.391602 |
| Max |delta BER| raw-native | 0.602216 |
| MAE(BER contract) | 0.002070 |
| MAE(log10 BER contract) | 0.002212 |
| Max |delta BER| contract | 0.005315 |
| MAE(Hold SNM mV) | 7.580673 |
| MAE(Read SNM mV) | 7.540723 |
| MAE(Write Margin mV) | 61.292643 |
| MAE(Noise Sigma) | 0.002377 |
| MAE(Noise Sigma raw-native) | 0.681499 |
| MAE(Read Fail) | 0.000000 |
| MAE(Read Fail raw-native) | 0.998921 |
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
| snm_mv | spice_snm_mv_raw | spice_snm_mv_raw | 43.778380 | 45 | no | no | usable | fitted | 0 | 15 | 0.357454 | 274.754674 | 45 |
| hold_snm_mv | spice_snm_mv_raw | spice_snm_mv_raw | 43.778380 | 45 | no | no | usable | fitted | 0 | 15 | 0.357454 | 274.754674 | 45 |
| read_snm_mv | n/a | spice_read_snm_mv_raw | 1867.964000 | 45 | no | no | usable | fitted | 0 | 15 | -0.003797 | 268.073286 | 45 |
| write_margin_mv | n/a | spice_write_margin_mv_raw | 1809.229000 | 45 | no | no | usable | fitted | 0 | 15 | 0.021775 | 1720.164414 | 45 |
| noise | n/a | spice_noise_raw | 0.507503 | 45 | no | no | usable | fitted | 0 | 15 | -0.011241 | 0.061652 | 45 |
| noise_sigma | n/a | spice_noise_sigma_raw | 0.507503 | 45 | no | no | usable | fitted | 0 | 15 | -0.011241 | 0.061652 | 45 |

## Notes

- The bundled template uses simplified compact models; replace with PDK-calibrated models for signoff.
- v2 metrics are proxy-compatible unless the template emits physically extracted metrics.
- Keep this report in version control with the exact command line used.
