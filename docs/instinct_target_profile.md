# Instinct Target Profile

This repository is preparing for future validation on AMD Instinct-class accelerators, not claiming it today.

## Intended First-Day Questions

- Does the canonical `torch_accelerated` lane run unchanged on a ROCm PyTorch build?
- Are the benchmark artifacts structurally identical to the current CPU/CUDA artifacts?
- Is fidelity against the CPU baseline still within the existing thresholds?

## Expected Workload Shape

- Analytical dataset generation with large vectorized tensor operations.
- Simple forward inference over exported perceptron weights.
- Moderate synchronization needs at benchmark boundaries.
- Throughput is more important than kernel micro-optimization in the first ROCm pass.

## Likely Bottlenecks

- Dataset generation and random sampling throughput.
- Host-to-device or synchronization overhead at small smoke sizes.
- Differences in PyTorch ROCm runtime behavior rather than algorithmic limitations.

## First-Day Validation Priority

1. Run smoke and confirm artifact integrity.
2. Run fidelity and confirm numerical parity.
3. Run the full suite only after smoke is stable.
4. Leave native HIP porting out of scope until the torch lane is proven stable.
