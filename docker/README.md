# Docker Portability Recipe

An optional CPU-only reproducible environment is provided via `Dockerfile.portability`.

## Build

```bash
docker build -f Dockerfile.portability -t sram-portability-smoke .
```

## Run

```bash
docker run --rm sram-portability-smoke
```

This image is intentionally CPU-only and is meant for reproducible smoke validation of the analytical portability benchmark path.
