# Raw Metric Span Audit

- Generated: 2026-03-09T04:18:42.919416+00:00
- Input tag: `matrix_fullpvt_xyce_mixed_contractfix_20260309`
- PDKs: `sky130, gf180mcu, freepdk45_openram, asap7`
- Metrics: `spice_snm_mv_raw, spice_hold_snm_mv_raw, spice_read_snm_mv_raw, spice_write_margin_mv_raw`
- Status rule: `degenerate` means raw span is below the configured minimum threshold for that metric.

## Summary

| PDK | Primary SNM Raw Span | Read SNM Raw Span | Primary Status | Read Status | Suggested Primary Source |
|---|---:|---:|---|---|---|
| sky130 | 0.000000 | 1688.279100 | degenerate | usable | spice_read_snm_mv_raw |
| gf180mcu | 31.871725 | 1854.753700 | usable | usable | spice_snm_mv_raw |
| freepdk45_openram | 0.000004 | 967.713400 | degenerate | usable | spice_read_snm_mv_raw |
| asap7 | 325.025503 | 592.263000 | usable | usable | spice_snm_mv_raw |

## sky130

| Metric | Finite Rows | Min | Max | Span | Mean | Median | Native Span | Span Ratio vs Native | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| spice_snm_mv_raw | 45 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 58.364762 | 0.000000 | degenerate |
| spice_hold_snm_mv_raw | 45 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 58.364762 | 0.000000 | degenerate |
| spice_read_snm_mv_raw | 45 | -1695.310000 | -7.030900 | 1688.279100 | -789.440618 | -747.484000 | 63.280293 | 26.679382 | usable |
| spice_write_margin_mv_raw | 45 | 141.098000 | 1950.000000 | 1808.902000 | 556.163000 | 203.019000 | 390.962763 | 4.626788 | usable |

## gf180mcu

| Metric | Finite Rows | Min | Max | Span | Mean | Median | Native Span | Span Ratio vs Native | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| spice_snm_mv_raw | 45 | 0.000675 | 31.872400 | 31.871725 | 9.371135 | 8.597070 | 63.496040 | 0.501948 | usable |
| spice_hold_snm_mv_raw | 45 | 0.000675 | 31.872400 | 31.871725 | 9.371135 | 8.597070 | 63.496040 | 0.501948 | usable |
| spice_read_snm_mv_raw | 45 | -1848.840000 | 5.913700 | 1854.753700 | -983.386560 | -1443.420000 | 69.518473 | 26.680012 | usable |
| spice_write_margin_mv_raw | 45 | 148.864000 | 1980.000000 | 1831.136000 | 1118.666400 | 1620.000000 | 410.186935 | 4.464150 | usable |

## freepdk45_openram

| Metric | Finite Rows | Min | Max | Span | Mean | Median | Native Span | Span Ratio vs Native | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| spice_snm_mv_raw | 27 | 0.000000 | 0.000004 | 0.000004 | 0.000001 | 0.000000 | 47.522388 | 0.000000 | degenerate |
| spice_hold_snm_mv_raw | 27 | 0.000000 | 0.000004 | 0.000004 | 0.000001 | 0.000000 | 47.522388 | 0.000000 | degenerate |
| spice_read_snm_mv_raw | 27 | -1001.070000 | -33.356600 | 967.713400 | -542.952952 | -821.244000 | 62.117274 | 15.578813 | usable |
| spice_write_margin_mv_raw | 27 | 120.428000 | 1100.000000 | 979.572000 | 647.441630 | 899.996000 | 321.624056 | 3.045705 | usable |

## asap7

| Metric | Finite Rows | Min | Max | Span | Mean | Median | Native Span | Span Ratio vs Native | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| spice_snm_mv_raw | 27 | 0.028397 | 325.053900 | 325.025503 | 105.801297 | 0.186752 | 34.825565 | 9.332957 | usable |
| spice_hold_snm_mv_raw | 27 | 0.028397 | 325.053900 | 325.025503 | 105.801297 | 0.186752 | 34.825565 | 9.332957 | usable |
| spice_read_snm_mv_raw | 27 | -298.915700 | 293.347300 | 592.263000 | 13.346517 | -23.225300 | 46.494858 | 12.738247 | usable |
| spice_write_margin_mv_raw | 27 | 69.093810 | 769.999800 | 700.905990 | 163.092707 | 90.017420 | 237.244107 | 2.954366 | usable |
