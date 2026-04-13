# SPICE Correlation Report

- Generated: 2026-04-13T14:36:01.903596+00:00
- Data source: `predictive-pdk-pre-silicon`
- SPICE source: `pdk:freepdk45_openram`
- Simulator: `ngspice`
- External sim command token: `n/a`
- External sim timeout (sec): `900`
- PDK ID: `freepdk45_openram`
- PDK class: `predictive`
- Model revision: `freepdk45-openram-local`
- Macro mode: `compiled-sram`
- PDK license: `Apache-2.0`
- Model root: `vendor/pdks/OpenRAM/technology/freepdk45`
- PDK registry: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\pdk_registry.json`
- PDK config: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\configs\pdk_runs\freepdk45_openram.json`
- Native backend: `hybrid`
- Measure contract revision: `v3-ber-contract-aligned-2026-02-18`
- PVT grid: corners=`tt,ff,ss` temps_k=`233.15,298.15,398.15` vdds=`0.90,1.00,1.10`
- Operating points: `27`
- Raw CSV: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/reports/ops_plan_v1/ops_plan_v1_full/parallel/workers_4/repeat_1/results/spice_vs_native_pdk_freepdk45_openram_matrix_parallel_w4_r1.csv`
- Native flags: noise=`True` variability=`True` thermal=`True` seed=`None`
- SPICE MC: mode=`off` runs=`1` seed=`20260218`
- SPICE MC effective mode: `off`
- Mean SPICE runtime per operating point (ms): `2564.954296`
- Mean SPICE runtime per MC sample (ms): `2564.954296`
- Mean Native runtime per operating point (ms): `483.475407`
- SNM/Noise contract mode: `affine_corner_temp`
- Allow contract fallback: `False`
- BER contract mode: `native_fit`
- BER contract params (center/slope mV): `154.726026 / 184.963026` (fit samples `27`)
- Proxy config: `F:\gpu experiment\SRAM_nosie_simulation-GPU-experiment\spice_validation\calibration\default_spice_proxy.json`

## Error Summary

| Metric | Value |
|---|---:|
| MAE(SNM mV) | 3.843994 |
| MAE(SNM mV raw-native) | 198.361112 |
| MAE(noise) | 0.003469 |
| MAE(BER) | 0.005135 |
| MAE(log10 BER) | 0.004975 |
| Max |delta BER| | 0.013533 |
| MAE(BER raw-native) | 0.558605 |
| MAE(log10 BER raw-native) | 0.355621 |
| Max |delta BER| raw-native | 0.586967 |
| MAE(BER contract) | 0.005135 |
| MAE(log10 BER contract) | 0.004975 |
| Max |delta BER| contract | 0.013533 |
| MAE(Hold SNM mV) | 3.843994 |
| MAE(Read SNM mV) | 4.272553 |
| MAE(Write Margin mV) | 42.886441 |
| MAE(Noise Sigma) | 0.003469 |
| MAE(Noise Sigma raw-native) | 0.622815 |
| MAE(Read Fail) | 0.000000 |
| MAE(Read Fail raw-native) | 0.999993 |
| MAE(Write Fail) | 0.000000 |
| MAE(Write Fail raw-native) | 0.000012 |

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
| snm_mv | spice_read_snm_mv_raw | spice_read_snm_mv_raw | 967.713400 | 27 | no | no | usable | fitted | 0 | 9 | -0.005706 | 195.262766 | 27 |
| hold_snm_mv | spice_read_snm_mv_raw | spice_read_snm_mv_raw | 967.713400 | 27 | no | no | usable | fitted | 0 | 9 | -0.005706 | 195.262766 | 27 |
| read_snm_mv | n/a | spice_read_snm_mv_raw | 967.713400 | 27 | no | no | usable | fitted | 0 | 9 | -0.009128 | 181.425682 | 27 |
| write_margin_mv | n/a | spice_write_margin_mv_raw | 979.572000 | 27 | no | no | usable | fitted | 0 | 9 | 0.011213 | 892.913310 | 27 |
| noise | n/a | spice_noise_raw | 0.463145 | 27 | no | no | usable | fitted | 0 | 9 | -0.058614 | 0.142184 | 27 |
| noise_sigma | n/a | spice_noise_sigma_raw | 0.463145 | 27 | no | no | usable | fitted | 0 | 9 | -0.058614 | 0.142184 | 27 |

## Notes

- The bundled template uses simplified compact models; replace with PDK-calibrated models for signoff.
- v2 metrics are proxy-compatible unless the template emits physically extracted metrics.
- Keep this report in version control with the exact command line used.
