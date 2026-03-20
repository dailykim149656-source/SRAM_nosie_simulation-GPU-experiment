# Unified App Usage

This repository includes multiple UI entry points. The unified Streamlit app is the quickest way to inspect the public snapshot.

## Launch

```powershell
streamlit run streamlit_app_unified.py
```

## What To Explore

- perceptron-based SRAM simulation behavior
- SNM and BER trends
- reliability and workload-linked views
- representative public report snapshots under `reports/`

## Recommended Workflow

1. Run the unified app for a quick visual walkthrough.
2. Use the desktop app if you want local research-data management and report export.
3. Use `scripts/build_research_evidence_pack.py` to regenerate the public-facing evidence summary.

## Public Snapshot Limits

- Only representative report snapshots are bundled.
- Large result trees under `spice_validation/results/`, `spice_validation/reports/`, `logs/`, and `artifacts/` are intentionally excluded.
