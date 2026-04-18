# AMD ROCm/HIP 강화 구현 계획서

## 1. 목적
현재 `SRAM_nosie_simulation-GPU-experiment` 레포는 **CPU 재현 가능한 benchmark + optional CUDA lane + portability 문서/CI/아티팩트 체계**를 이미 갖춘 상태다. 다음 단계의 목적은 이 기반을 유지하면서, **AMD GPU가 없는 현재 환경에서도 ROCm/HIP/PyTorch-on-ROCm 관련성을 실질적으로 강화**하는 것이다.

이 계획의 목표는 세 가지다.

1. CUDA 전용처럼 보이는 부분을 줄이고 **backend-neutral 구조**를 강화한다.
2. AMD GPU가 생겼을 때 바로 검증 가능한 **ROCm 실행/검증 프로토콜**을 준비한다.
3. 면접/서류에서 과장 없이 말할 수 있는 **증거물(docs, tests, artifacts, code structure)** 을 늘린다.

## 2. 현재 기준점

### 이미 완료된 기반
- `README.md`는 레포를 “SRAM GPU Portability And Benchmarking”으로 재정의했고, CPU benchmark artifacts, optional CUDA execution, fidelity check, future ROCm/HIP porting cost reduction을 명시한다.
- `backends/`와 `benchmarks/`가 도입되어 analytical benchmark path가 분리되었다.
- `docs/hip_porting_plan.md`, `docs/backend_portability.md`, `docs/limitations_and_claims.md`, `docs/prd_completion_matrix.md` 등 portability 문서 묶음이 존재한다.
- `.github/workflows/cpu-smoke.yml` 와 `.github/workflows/portability-release.yml` 로 CPU smoke/verification/release evidence 체계가 있다.
- `reports/portability/dashboard.md` 에 대표 benchmark snapshot이 쌓이기 시작했다.

### 아직 남아 있는 구조적 한계
- `backends/cuda_lane.py` 이름과 내부 구현이 CUDA vendor-specific 하다.
- `backends/torch_portable.py` 는 `torch.version.hip` 감지는 하지만, device resolution은 여전히 `"cuda"` 중심이며 동기화도 `torch.cuda.synchronize()` 중심이다.
- `execution_policy.py` 는 generic selection 로직을 가지지만 여전히 CUDA/CuPy 흔적이 있다.
- `native_backend.py` 의 simulate/lifetime/optimize GPU fallback path는 완전히 새 abstraction 위로 올라오지 않았다.
- 현재 문서도 명시하듯, **AMD GPU/ROCm runtime validation은 아직 수행되지 않았다.**

## 3. 이번 배치의 범위

### 포함 범위
- benchmark path 의 backend-neutral 강화
- ROCm/HIP 준비 문서 및 validation matrix 구체화
- PyTorch portable layer의 vendor-agnostic 정리
- native backend portability 1차 정리
- Linux/ROCm 검증 프로토콜 설계
- external-facing claim language 정리

### 제외 범위
- 실제 AMD GPU 성능 수치 생성
- 실제 ROCm runtime benchmark 결과 게시
- HIP native kernel 최적화 완료 주장
- distributed/multi-node benchmark 구현

## 4. 최종 산출물
1. `gpu_pytorch` lane를 대체/보강하는 **accelerator-neutral benchmark lane**
2. `torch_portable.py` 의 **backend-neutral device/sync abstraction**
3. `docs/rocm_validation_matrix.md`
4. `docs/instinct_target_profile.md`
5. `docs/hipify_preflight_inventory.md`
6. `docs/native_backend_rocm_migration_plan.md`
7. benchmark artifact schema 확장 (`backend_kind`, `torch_build`, `hip_version`, `validation_status` 등)
8. CPU-only CI 유지 + optional CUDA regression 유지
9. AMD hardware access 이후 바로 실행 가능한 수동 checklist

## 5. 성공 기준

### 기술 기준
- CPU smoke, existing CUDA smoke, artifact validation, fidelity tests가 모두 유지된다.
- 새 코드가 CUDA-only naming/logic에 덜 묶인다.
- benchmark output이 “cuda only”가 아니라 “backend kind / accelerator kind / runtime kind”를 기록한다.
- native backend와 analytical benchmark path가 같은 capability vocabulary를 사용한다.

### 포트폴리오 기준
- README/문서만 봐도 “현재는 CPU+CUDA validated, AMD는 미검증이지만 HIP/ROCm migration plan이 명확하다”는 점이 드러난다.
- AMD 면접에서 “왜 AMD GPU가 없는데 ROCm 관련성을 주장하나?”라는 질문에, 구조/문서/테스트/claim guardrail로 방어 가능하다.

## 6. 구현 원칙
1. **작동하는 CUDA codebase에서 시작한다.**
2. **incremental porting** 원칙을 따른다.
3. ROCm 결과를 추정해서 쓰지 않는다.
4. backend-neutral abstraction을 먼저 만들고, ROCm lane은 hardware access 이후 붙인다.
5. torch-level portable path를 기준 경로로 두고, vendor-specific lane은 wrapper로 격리한다.

## 7. 작업 트랙

### Track A. Naming / API 정리
목표: 코드가 NVIDIA 전용 프로젝트처럼 읽히지 않게 만든다.

#### 작업
- `gpu_pytorch` lane의 내부 표현을 `accelerated_torch` 또는 `torch_accelerated`로 개편
- CLI의 `--device gpu` 는 유지하되, 내부 metadata에는 `backend_kind: cpu|cuda|hip|unknown` 저장
- `cuda_lane.py`는 backward compatibility를 유지하면서도 내부적으로는 `accelerator_lane.py` 또는 alias layer 도입
- README/문서의 “CUDA benchmark” 표현을 “accelerated torch lane (currently CUDA-validated)” 식으로 조정

#### 대상 파일
- `backends/cuda_lane.py`
- `backends/registry.py`
- `benchmarks/schema.py`
- `benchmarks/reports.py`
- `README.md`
- `docs/backend_portability.md`
- `docs/limitations_and_claims.md`

#### 완료 기준
- artifact와 report에서 vendor name과 lane name이 분리 기록된다.
- 대외 문서에서 “CUDA=유일한 GPU path”처럼 읽히는 표현이 줄어든다.

---

### Track B. Torch portable layer 일반화
목표: `torch_portable.py` 가 ROCm/HIP 시점의 기준 abstraction이 되게 만든다.

#### 작업
- `resolve_torch_accelerator()` 를 `resolve_torch_runtime()` 와 `resolve_torch_device()` 로 분리
- `torch.version.hip` 존재 여부를 metadata로 기록
- 동기화를 `synchronize_torch_device(device, backend_kind)` 형태로 일반화
- `"cuda"` string 직접 사용 지점을 helper 함수 뒤로 감춤
- `torch_cuda_info()` 명칭은 backward compatibility wrapper로만 남기고, 실제 구현은 `torch_accelerator_info()` 를 기준으로 정리

#### 대상 파일
- `backends/torch_portable.py`
- `backends/cuda_lane.py`
- `gpu_analytical_adapter.py`
- `execution_policy.py`

#### 완료 기준
- upper layer는 `torch.cuda.*` 직접 호출 없이 accelerator metadata만 소비한다.
- `torch_portable.py` 내부에서 backend kind / device string / display name / hip version을 함께 제공한다.

---

### Track C. Benchmark schema / artifact 확장
목표: ROCm hardware가 없어도 “future ROCm validation frame”을 먼저 만든다.

#### 작업
`metadata.json` 에 아래 필드 추가:
- `backend_kind`
- `runtime_kind`
- `torch_version`
- `torch_build_tag`
- `cuda_version`
- `hip_version`
- `device_display_name`
- `validation_scope` (`cpu_validated`, `cuda_validated`, `rocm_pending` 등)
- `claim_level` (`measured`, `prepared`, `planned`)

`results.csv` / `report.md` 에도 아래 반영:
- lane 명칭과 runtime 명칭 분리
- skipped reason 표준화 (`forced_cpu_env`, `no_accelerator_runtime`, `rocm_not_available`, `cuda_unavailable` 등)

#### 대상 파일
- `benchmarks/schema.py`
- `benchmarks/env.py`
- `benchmarks/runner.py`
- `benchmarks/reports.py`
- `benchmarks/validate.py`
- `tests/test_report_generation.py`

#### 완료 기준
- 새 artifact는 CPU/CUDA 뿐 아니라 future ROCm run도 같은 schema로 담을 수 있다.
- path hygiene를 깨지 않고 metadata가 확장된다.

---

### Track D. ROCm validation document package
목표: AMD GPU가 생기면 바로 실행 가능한 문서 세트를 만든다.

#### 신규 문서
1. `docs/rocm_validation_matrix.md`
   - target OS (Linux only)
   - ROCm version selection policy
   - PyTorch wheel/source install decision
   - benchmark suites to run (`smoke`, `full`)
   - acceptance thresholds
   - fail/blocked states

2. `docs/instinct_target_profile.md`
   - 이 레포 workload가 Instinct-class accelerator에서 어떤 의미를 갖는지
   - 예상 bottleneck (dataset generation / inference / memory / sync)
   - first-day validation priority

3. `docs/hipify_preflight_inventory.md`
   - Python/native CUDA touch points
   - automatic conversion 후보
   - manual review 필요 영역
   - native build hotspot

4. `docs/rocm_manual_checklist.md`
   - environment setup
   - install verification
   - smoke/full benchmark sequence
   - fidelity gates
   - publication rules

#### 완료 기준
- “AMD 장비가 생기면 무엇부터 어떻게 검증할지”가 문서만으로 명확하다.
- ROCm 미검증 상태와 향후 검증 상태를 혼동하지 않게 된다.

---

### Track E. Native backend 1차 migration
목표: benchmark path와 native runtime path의 용어/구조를 맞춘다.

#### 작업
- `native_backend.py` 의 torch fallback capability reporting을 `backends.registry` 기준으로 통일
- simulate/lifetime/optimize torch fallback helper를 별도 module로 분리
- native extension dispatch와 torch accelerator fallback을 함수 레벨에서 분리
- device labeling (`cuda`, `cpu`) 대신 runtime capability object를 통해 normalization

#### 대상 파일
- `native_backend.py`
- `backends/registry.py`
- 신규 `backends/runtime_torch_fallbacks.py`
- `docs/native_backend_portability_inventory.md`
- 신규 `docs/native_backend_rocm_migration_plan.md`

#### 완료 기준
- `native_backend.py` 가 GPU fallback math + dispatch policy + metadata formatting을 한 파일에서 동시에 떠안지 않는다.
- 향후 HIP/native work를 독립 milestone으로 떼기 쉬워진다.

---

### Track F. Linux-first / packaging / CI 정리
목표: ROCm이 Linux 중심이라는 점을 반영해 repo의 실행 표면을 더 명확히 한다.

#### 작업
- `README.md` 에 Linux-first CPU/CUDA/ROCm-planned 실행 매트릭스 표 추가
- `requirements-benchmark.txt` 또는 별도 docs에 “PyTorch is manually selected by runtime target” 명시 강화
- `Dockerfile.portability` 와 `docker/README.md` 에 “CPU-only reproducibility container” 성격을 더 분명히 표시
- optional workflow 문서에 “future self-hosted ROCm runner” 섹션 추가

#### 대상 파일
- `README.md`
- `docker/README.md`
- `docs/portability_release_checklist.md`
- 신규 `docs/ci_future_rocm_runner_note.md`

#### 완료 기준
- 사용자에게 현재 가능한 것(CPU/CUDA)과 아직 불가능한 것(ROCm measured run)이 명확히 구분된다.

## 8. 단계별 실행 순서

### Phase 1. Safe refactor (1주차)
- Track A 일부
- Track B 일부
- Track C schema 설계
- 테스트 깨지지 않는 수준의 internal rename/metadata 추가

**목표:** 현재 CPU smoke + CUDA smoke + release verification 그대로 유지

### Phase 2. Evidence expansion (2주차)
- Track C 완료
- Track D 문서 패키지 작성
- representative reports/dashboard 갱신

**목표:** 레포를 보는 사람이 “다음 AMD 검증 단계가 문서로 설계돼 있다”는 것을 이해할 수 있게 만들기

### Phase 3. Native alignment (3주차)
- Track E 시작
- `native_backend.py` torch fallback 분리
- capability vocabulary 통일

**목표:** benchmark path와 runtime path가 다른 언어를 쓰지 않게 만들기

### Phase 4. Release polish (4주차)
- Track F
- README 최종 정리
- portability release artifacts 갱신
- issue backlog 업데이트

**목표:** 레포가 포트폴리오/지원서 링크로 사용 가능한 수준이 되게 만들기

## 9. 우선순위

### P1 반드시 할 것
- `torch_portable.py` 일반화
- artifact schema 확장
- `rocm_validation_matrix.md`
- `hipify_preflight_inventory.md`
- README claim language 개편

### P2 하면 강해지는 것
- native backend torch fallback 분리
- accelerator-neutral lane naming
- future ROCm runner note

### P3 장비 확보 후 할 것
- ROCm lane 실제 구현
- HIPIFY trial output
- PyTorch-on-ROCm measured benchmark
- native/HIP build 실험

## 10. 리스크와 대응

### 리스크 1. “ROCm 준비”가 과장으로 읽힘
대응:
- `limitations_and_claims.md` 와 README에 `validated / conditional / not validated` 구분 유지
- artifact에 `claim_level` 필드 추가

### 리스크 2. naming만 바뀌고 실질적 개선이 없음
대응:
- schema/env/report/runner/tests까지 같이 바꿔서 evidence를 남긴다.

### 리스크 3. native backend 정리 범위가 과도해짐
대응:
- 이번 배치에서 native는 full port가 아니라 “torch fallback 분리 + migration note”까지만 한다.

### 리스크 4. 향후 ROCm 버전/호환성 변경
대응:
- 문서에 구체 버전 하드코딩보다 “selection policy + official matrix 확인” 방식 채택

## 11. 검증 계획

### 자동 검증
- `python -m unittest discover -s tests -p "test_*.py"`
- `python -m benchmarks.cli --suite smoke --device cpu`
- CUDA 환경에서 `python -m benchmarks.cli --suite smoke --device auto`
- `python -m benchmarks.validate --artifact-dir <latest>`
- `python scripts/verify_portability_prd.py`

### 수동 검증
- README quickstart 문서 복제 실행
- `reports/portability/dashboard.md` 재생성
- 새 metadata/report에 ROCm pending state가 올바르게 반영되는지 확인
- 외부 claim 문구 점검

## 12. 대외 설명 문구

### 사용 가능
- CPU benchmark artifacts are reproducible today.
- NVIDIA CUDA execution is optional when a compatible PyTorch build is installed.
- CUDA-specific logic is increasingly isolated to reduce future ROCm/HIP porting cost.
- ROCm validation workflows and HIP migration inventory are documented, but AMD hardware execution has not yet been validated in this repository.

### 사용 금지
- ROCm-ready
- HIP-complete
- validated on AMD GPUs
- portable to AMD today

## 13. 최종 기대 효과
이 구현 배치가 끝나면 이 레포는 단순히 “CUDA도 조금 돌아가는 SRAM repo”가 아니라,

- **CPU/CUDA validated benchmark asset**
- **ROCm/HIP migration-aware codebase**
- **AMD hardware access 이후 즉시 검증 가능한 문서/테스트/아티팩트 체계 보유 레포**

로 설명할 수 있게 된다.

즉, AMD GPU가 없는 지금 상태에서도 **ROCm/Instinct/HIP/PyTorch-on-ROCm 준비도**를 상당히 끌어올릴 수 있다.
