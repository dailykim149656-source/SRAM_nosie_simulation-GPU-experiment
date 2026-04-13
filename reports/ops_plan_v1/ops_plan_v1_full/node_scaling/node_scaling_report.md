# Node Scaling Report (Phase 3)

- Generated: 2026-04-13T14:39:37.335316+00:00
- Data source: `proxy-calibrated`
- Workload profile: `llama_7b_online`
- Native backend: `hybrid`
- Node config dir: `F:/gpu experiment/SRAM_nosie_simulation-GPU-experiment/configs/nodes`
- Total sweep points: `81`
- Reference track: `native-derived reference`

## Node Summary

| Node | Points | Mean SNM (mV) | Mean BER | Mean Latency (ms) | Mean Energy/token (uJ) | Mean Tok/s | Accept Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| 22nm | 27 | 199.505 | 3.967503e-01 | 1.000 | 1.420 | 1000.000 | 66.7% |
| 14nm | 27 | 180.010 | 4.696670e-01 | 1.000 | 2.155 | 1000.000 | 55.6% |
| 7nm | 27 | 151.982 | 6.645295e-01 | 1.053 | 3.240 | 954.082 | 7.4% |

## Reference Summary

| Node | Points | Mean SNM (mV) | Mean BER | Mean Latency (ms) | Mean Energy/token (uJ) | Mean Tok/s | Accept Rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| 22nm | 27 | 190.005 | 4.522714e-01 | 1.000 | 1.410 | 1000.000 | 66.7% |
| 14nm | 27 | 180.010 | 4.590567e-01 | 1.000 | 2.119 | 1000.000 | 55.6% |
| 7nm | 27 | 170.000 | 4.715712e-01 | 1.053 | 3.156 | 954.082 | 33.3% |

## Agreement

- Ranking agreement: `100.0%`
- Verdict agreement: `88.9%`

## Scaling Trend

- Compared to `22nm`, `7nm` changes:
  - SNM: -23.82%
  - BER: 67.49%
  - Tail latency: 5.33%
  - Energy/token: 128.19%
- Ranking agreement vs `native-derived reference`: `100.0%`
- Verdict agreement vs `native-derived reference`: `88.9%`

## Notes

- Data source must match the report header (`proxy-calibrated|foundry-pdk-pre-silicon|predictive-pdk-pre-silicon|model-card-calibrated|silicon-correlated`).
- Node profiles are proxy calibrations (not foundry signoff models).
- Use this report for trend analysis and reproducibility checks, then replace with PDK-calibrated values.
