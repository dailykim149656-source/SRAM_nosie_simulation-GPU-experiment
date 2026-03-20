# SPICE Validation Bootstrap

This folder is the Phase 1 starting point for SPICE correlation.

Current scope:
- PVT sweep runner (`run_spice_validation.py`)
- Netlist template (`netlists/sram6t_template.sp`)
- Real PDK templates (`netlists/pdk/*.sp`)
- CSV + markdown report generation (`results/`, `reports/`)

Important:
- The bundled template is a **transistor-level 6T topology** with simplified compact models.
- It is enough for flow bring-up and correlation plumbing.
- Real deck includes are now wired for `sky130`, `gf180mcu`, `ihp_sg13g2`, `asap7`, `freepdk45_openram`.
- Metric equations are still proxy-style (`SNM/noise/BER`), so this is pre-silicon correlation plumbing, not signoff.

## Quick Start

Run pipeline wiring check without ngspice:

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source placeholder
```

Run with ngspice (strict mode):

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source ngspice
```

Run in PDK mode (registry/config driven):

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source pdk --pdk-id sky130 --pdk-config .\spice_validation\configs\pdk_runs\sky130.json
```

Run PDK mode with MC preview (`param_perturb` fallback path):

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source pdk --pdk-id sky130 --pdk-config .\spice_validation\configs\pdk_runs\sky130.json --spice-mc-runs 3 --mc-mode param_perturb --spice-seed 20260218
```

Set explicit report provenance (recommended):

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source ngspice --data-source proxy-calibrated
```

If `ngspice` is not on PATH:

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source ngspice --ngspice-bin "C:\msys64\ucrt64\bin\ngspice.exe"
```

## Fetch Real PDK Sources (GitHub)

Clone once into `vendor/pdks`:

```powershell
.\scripts\fetch_open_pdks.ps1
```

Equivalent manual commands:

```powershell
git clone --filter=blob:none --sparse --depth 1 https://github.com/google/skywater-pdk-libs-sky130_fd_pr.git vendor/pdks/sky130_fd_pr
git -C vendor/pdks/sky130_fd_pr sparse-checkout set models cells

git clone --filter=blob:none --sparse --depth 1 https://github.com/google/globalfoundries-pdk-libs-gf180mcu_fd_pr.git vendor/pdks/gf180mcu_fd_pr
git -C vendor/pdks/gf180mcu_fd_pr sparse-checkout set models cells

git clone --filter=blob:none --sparse --depth 1 https://github.com/IHP-GmbH/IHP-Open-PDK.git vendor/pdks/IHP-Open-PDK
git -C vendor/pdks/IHP-Open-PDK sparse-checkout set ihp-sg13g2/libs.tech/ngspice ihp-sg13g2/libs.ref/sg13g2_stdcell/spice ihp-sg13g2/libs.ref/sg13g2_io/spice

git clone --filter=blob:none --sparse --depth 1 https://github.com/The-OpenROAD-Project/asap7_pdk_r1p7.git vendor/pdks/asap7_pdk_r1p7
git -C vendor/pdks/asap7_pdk_r1p7 sparse-checkout set models

git clone --filter=blob:none --sparse --depth 1 https://github.com/VLSIDA/OpenRAM.git vendor/pdks/OpenRAM
git -C vendor/pdks/OpenRAM sparse-checkout set technology/freepdk45 compiler/tests/golden
```

If git ownership checks fail in your environment, add each clone path with:

```powershell
git config --global --add safe.directory <absolute-repo-path>
```

## PDK Smoke Commands

SKY130 (foundry-open):

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source pdk --pdk-id sky130 --pdk-config .\spice_validation\configs\pdk_runs\sky130.json --corners tt --temps-k 298.15 --vdds 1.80
```

GF180MCU (foundry-open):

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source pdk --pdk-id gf180mcu --pdk-config .\spice_validation\configs\pdk_runs\gf180mcu.json --corners tt --temps-k 298.15 --vdds 1.80
```

IHP SG13G2 (foundry-open):

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source pdk --pdk-id ihp_sg13g2 --pdk-config .\spice_validation\configs\pdk_runs\ihp_sg13g2.json --corners tt --temps-k 298.15 --vdds 1.20
```

ASAP7 (predictive):

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source pdk --pdk-id asap7 --pdk-config .\spice_validation\configs\pdk_runs\asap7.json --corners tt --temps-k 298.15 --vdds 0.70
```

FreePDK45 + OpenRAM (predictive):

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source pdk --pdk-id freepdk45_openram --pdk-config .\spice_validation\configs\pdk_runs\freepdk45_openram.json --corners tt --temps-k 298.15 --vdds 1.00
```

## PDK Matrix Run

Run all configured PDKs in one shot (full PVT per config):

```powershell
.\.venv\Scripts\python.exe .\scripts\run_pdk_matrix.py
```

Allow runtime-compatibility blocked PDK rows (for mixed-simulator operation planning):

```powershell
.\.venv\Scripts\python.exe .\scripts\run_pdk_matrix.py --allow-blocked
```

Outputs:
- `spice_validation/reports/pdk_matrix_summary.csv`
- `spice_validation/reports/pdk_matrix_summary.md`

## Measure Contract

- Contract file: `spice_validation/netlists/MEASURE_CONTRACT.md`
- Current revision: `v2-proxy-compat-2026-02-18`
- Backward compatible with legacy tags (`MEAS_SNM_MV`, `MEAS_NOISE`, `MEAS_BER`)

## Windows Install (MSYS2)

If ngspice is not available on your machine:

```powershell
winget install --id MSYS2.MSYS2 -e --accept-source-agreements --accept-package-agreements
C:\msys64\usr\bin\bash.exe -lc "pacman -Sy --noconfirm --needed mingw-w64-ucrt-x86_64-ngspice"
```

The runner auto-detects `C:\msys64\ucrt64\bin\ngspice.exe`.

Main outputs:
- `spice_validation/results/spice_vs_native.csv`
- `spice_validation/reports/spice_correlation_report.md`

PDK metadata files:
- `spice_validation/pdk_registry.json`
- `spice_validation/configs/pdk_runs/*.json`

## Runtime Status (ngspice Binary in This Repo)

- `sky130`: pass
- `gf180mcu`: pass
- `freepdk45_openram`: pass
- `ihp_sg13g2`: fail on PSP model type (`psp103va`) not supported by this ngspice build
- `asap7`: fail on BSIM-CMG level 72 not supported by this ngspice build

When this happens, `run_spice_validation.py` emits structured error tags:
- `[SPICE_RUNTIME:NGSPICE_UNSUPPORTED_PSP]`
- `[SPICE_RUNTIME:NGSPICE_UNSUPPORTED_LEVEL72]`

## Proxy Calibration (Optional)

Fit proxy coefficients from an existing correlation CSV:

```powershell
.\.venv\Scripts\python.exe .\spice_validation\fit_spice_proxy.py --input-csv .\spice_validation\results\spice_vs_native_hybrid.csv --out-config .\spice_validation\calibration\fitted_spice_proxy.json
```

Re-run correlation with fitted coefficients:

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source ngspice --spice-proxy-config .\spice_validation\calibration\fitted_spice_proxy.json
```

You can also control native-side stochastic knobs for deterministic checks:

```powershell
.\.venv\Scripts\python.exe .\spice_validation\run_spice_validation.py --spice-source ngspice --native-noise-enable false --native-variability-enable false --native-thermal-enable false --native-seed 42
```

## CI Regression Gate

Run the end-to-end gate locally:

```powershell
.\.venv\Scripts\python.exe .\ci_regression_check.py
```

Thresholds and default knobs are controlled by:

- `spice_validation/calibration/ci_thresholds_hybrid.json`

Regression metrics include:
- `MAE(SNM mV)`
- `MAE(noise)`
- `MAE(BER)`
- `MAE(log10 BER)`
- `Max |delta BER|`

## Next Upgrade Steps

1. Replace template with real 6T SRAM deck per corner/voltage/temp.
2. Extract SNM/read/write fail metrics using `.MEASURE` or waveform post-processing.
3. Add calibration script to fit model coefficients against SPICE outputs.
4. Wire this command into CI for regression protection.
