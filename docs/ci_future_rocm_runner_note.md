# Future ROCm Runner Note

Current CI is CPU-focused, with optional CUDA validation performed only where local installs allow it.

## Future ROCm CI Direction

- use a self-hosted Linux runner with ROCm installed
- keep ROCm validation separate from the default CPU smoke workflow
- require measured artifacts before any public ROCm claim changes

## Minimum Future ROCm Job

- install the matching PyTorch ROCm build
- run `python -m unittest discover -s tests -p "test_*.py"`
- run `python -m benchmarks.cli --suite smoke --device auto`
- run `python -m benchmarks.validate --artifact-dir <run_id>`

## Why This Is Deferred

- this repository currently has no AMD hardware in the working environment
- simulating ROCm CI without hardware would overstate validation
