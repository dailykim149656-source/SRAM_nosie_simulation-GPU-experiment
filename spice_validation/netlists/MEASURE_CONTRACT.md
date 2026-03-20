# MEASURE Contract

Revision: `v2-proxy-compat-2026-02-18`

`run_spice_validation.py` parses ngspice logs using required v1 tags and optional v2 tags.

## Required (v1, backward-compatible)

- `MEAS_SNM_MV=<float>`
- `MEAS_NOISE=<float>`
- `MEAS_BER=<float>`

These three tags must always be emitted.

## Optional (v2 extension)

- `MEAS_HOLD_SNM_MV=<float>`
- `MEAS_READ_SNM_MV=<float>`
- `MEAS_WRITE_MARGIN_MV=<float>`
- `MEAS_NOISE_SIGMA=<float>`
- `MEAS_READ_FAIL=<float>`
- `MEAS_WRITE_FAIL=<float>`

If v2 tags are missing, the runner applies compatibility fallback:

- `hold_snm_mv := snm_mv`
- `read_snm_mv := snm_mv`
- `noise_sigma := noise`
- `write_margin_mv/read_fail/write_fail := NaN`

## Proxy Definition (current templates)

Current bundled templates emit proxy-style metrics in `.control`:

- `hold_snm_mv`: proxy hold margin in mV (currently tied to `snm_mv`)
- `read_snm_mv`: `snm_mv - read_disturb * 1000`
- `write_margin_mv`: `(VDD - write_error) * 1000`
- `noise_sigma`: currently mapped to `noise_proxy`
- `read_fail`, `write_fail`: logistic proxy from read/write margins

These are **pre-silicon proxy-compatible** values, not silicon-validated signoff metrics.

## Example Emission

```spice
echo MEAS_SNM_MV=$&snm_mv
echo MEAS_NOISE=$&noise_proxy
echo MEAS_BER=$&ber_proxy
echo MEAS_HOLD_SNM_MV=$&hold_snm_mv
echo MEAS_READ_SNM_MV=$&read_snm_mv
echo MEAS_WRITE_MARGIN_MV=$&write_margin_mv
echo MEAS_NOISE_SIGMA=$&noise_sigma
echo MEAS_READ_FAIL=$&read_fail
echo MEAS_WRITE_FAIL=$&write_fail
```
