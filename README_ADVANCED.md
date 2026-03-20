# Advanced UI Guide

This document summarizes the advanced analysis surfaces exposed by the public snapshot.

## Desktop UI

Launch:

```powershell
python pyside_sram_app_advanced.py
```

Major areas:
- core SRAM simulation
- SNM analysis
- variability and Monte Carlo views
- thermal and retention analysis
- reliability analysis
- research data management
- AI research analysis

## Research Data

The desktop app includes a `Research Data` tab for storing measured or curated SNM samples.

Local files:
- `research_data.json`
- `research_data_<timestamp>.csv`
- `logs/research_analysis_<timestamp>.json`

These files are local working outputs and are not intended for version control in this public repository.

## AI Research Analysis

The app can analyze local research data using configured AI service credentials from `.env`.

Expected environment variables:

```env
AZURE_OPENAI_KEY=...
AZURE_OPENAI_ENDPOINT=...
```

The public UI wording is intentionally neutral and research-oriented even though the environment variable names remain Azure-compatible.

## PDF and Report Export

The advanced UI can generate a full simulation report when the required plotting and PDF dependencies are installed.

Representative bundled public report snapshots live under `reports/`, but the full local export history is intentionally excluded from this repository.
