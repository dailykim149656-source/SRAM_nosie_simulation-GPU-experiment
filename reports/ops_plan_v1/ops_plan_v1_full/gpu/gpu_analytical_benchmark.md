# GPU Analytical Benchmark

- Generated: 2026-04-13T14:26:44.551643+00:00
- CUDA status: `NVIDIA GeForce RTX 4060 Ti`
- Smoke max abs prediction delta: `3.209769e-08`
- Smoke mean abs prediction delta: `7.094534e-09`

## Benchmark Results

| Case | Lane | Status | Selected Engine | Device | Wall Clock (s) | Throughput (samples/s) | Mean Prediction |
|---|---|---|---|---|---:|---:|---:|
| 10000x512 | cpu_existing | pass | cpu | cpu | 1.119130 | 8935.516 | 0.060538 |
| 10000x512 | cpu_numpy | pass | cpu | cpu | 1.133020 | 8825.970 | 0.060538 |
| 10000x512 | gpu_pytorch | pass | gpu | NVIDIA GeForce RTX 4060 Ti | 0.276867 | 36118.425 | 0.060261 |
| 5000x1024 | cpu_existing | pass | cpu | cpu | 1.330346 | 3758.421 | 0.060197 |
| 5000x1024 | cpu_numpy | pass | cpu | cpu | 1.208296 | 4138.060 | 0.060197 |
| 5000x1024 | gpu_pytorch | pass | gpu | NVIDIA GeForce RTX 4060 Ti | 0.013457 | 371553.838 | 0.058113 |
| 20000x512 | cpu_existing | pass | cpu | cpu | 2.412789 | 8289.162 | 0.060087 |
| 20000x512 | cpu_numpy | pass | cpu | cpu | 2.387149 | 8378.194 | 0.060087 |
| 20000x512 | gpu_pytorch | pass | gpu | NVIDIA GeForce RTX 4060 Ti | 0.245203 | 81565.037 | 0.060525 |

## Notes

- `CPU existing` uses `AnalyticalSRAMModel.generate_dataset()` and the fitted perceptron `.predict()` path.
- `CPU NumPy` uses chunked analytical generation plus manual NumPy forward on exported perceptron weights.
- `GPU PyTorch` is limited to analytical dataset generation plus batched perceptron inference.
- GPU rows are marked `skipped` when PyTorch or CUDA is unavailable.
