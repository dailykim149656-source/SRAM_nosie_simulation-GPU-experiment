# PDK Run Configs

These JSON files are optional overrides for `run_spice_validation.py --spice-source pdk`.

Usage:

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source pdk --pdk-id sky130 --pdk-config .\spice_validation\configs\pdk_runs\sky130.json
```

Notes:
- `pdk_id` must match `--pdk-id`.
- Relative paths are resolved relative to the config file location.
- `model_lib`, `*_file`, and `*_corner_pattern` paths are resolved and injected into netlist templates.
- `model_root` is metadata in reports and should still point to the real deck root for traceability.
- For non-ngspice adapter path, optional keys:
  - `simulator`: `spectre|hspice|xyce`
  - `external_sim_cmd`: command template (placeholders: `__SIMULATOR__`, `__NETLIST__`, `__LOG_PATH__`, `__RAW_DIR__`, `__CASE_ID__`)
  - `external_sim_timeout_sec`: timeout per operating point.
