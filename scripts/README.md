# Public Scripts

Only the public-facing helper scripts are included in this repository snapshot.

## Included

- `scripts/run_pdk_matrix.py`
- `scripts/run_model_selection.py`
- `scripts/run_node_scaling.py`
- `scripts/build_research_evidence_pack.py`
- `scripts/export_research_bundle.py`

## Usage

```powershell
python scripts/run_pdk_matrix.py
python scripts/run_model_selection.py
python scripts/run_node_scaling.py
python scripts/build_research_evidence_pack.py
python scripts/export_research_bundle.py --tag public_snapshot --skip-zip
```

## Notes

- Internal experimental helpers and bulk archival scripts are intentionally not included in this public snapshot.
- The evidence pack and exported research bundle operate only on the representative artifacts that are bundled here.
