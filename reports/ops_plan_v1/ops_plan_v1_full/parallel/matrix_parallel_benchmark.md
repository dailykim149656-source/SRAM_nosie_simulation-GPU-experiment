# Matrix Parallel Benchmark

- Generated: 2026-04-13T14:39:35.224039+00:00
- PDK IDs: `gf180mcu,freepdk45_openram`
- Repeats: `2`
- Baseline workers: `1`

## Summary

| workers | runs | mean sec | stdev sec | speedup vs baseline | failure rate |
|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 137.838036 | 0.564503 | 1.0000x | 0.0% |
| 2 | 2 | 103.320504 | 2.552181 | 1.3341x | 0.0% |
| 4 | 2 | 76.394074 | 1.486483 | 1.8043x | 0.0% |
| 8 | 2 | 67.369368 | 0.215392 | 2.0460x | 0.0% |

## Notes

- Timing includes matrix runner startup, per-PDK execution, summary generation, and log capture.
- Failure rate counts non-zero exits from the wrapped matrix run.
- Blocked PDKs are excluded from this benchmark by design.

## Blocked PDKs

- Excluded from scaling benchmark: `ihp_sg13g2`
- These remain blocker-tracking entries and are not counted in speedup figures.
