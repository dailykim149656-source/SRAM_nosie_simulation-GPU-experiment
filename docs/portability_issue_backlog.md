# Portability Issue Backlog

This backlog breaks the portability PRD into trackable follow-up work after the initial benchmark refactor.

## Open Follow-ups

1. Add ROCm-capability detection to the backend registry once AMD hardware is available.
2. Refactor `native_backend.py` GPU torch fallbacks onto the new backend abstraction surface.
3. Add a backend-neutral synchronization helper in the portable torch layer.
4. Evaluate whether CuPy detection should remain in `execution_policy.py`.
5. Add a committed representative CPU benchmark snapshot.
6. Add a committed representative CUDA benchmark snapshot when the environment is stable enough for publication.
7. Add a Linux quickstart matrix for CPU-only and CUDA-capable installs.
8. Add a manual ROCm validation checklist for future hardware access.
