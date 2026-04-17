# PRD - SRAM_nosie_simulation-GPU-experiment 포터블 GPU 벤치마크/문서화 전환

- 버전: v0.1
- 상태: Draft
- 작성일: 2026-04-17
- 문서 목적: 현재 연구 중심 공개 레포를 **NVIDIA 환경에서 즉시 실행 가능**하고, 동시에 **AMD ROCm/HIP 이식 가능성을 설명할 수 있는 엔지니어링 포트폴리오 레포**로 전환하기 위한 실행형 요구사항 문서

---

## 1. 프로젝트 개요

### 1.1 프로젝트명
**SRAM GPU Portability & Benchmark Modernization**

### 1.2 한 줄 정의
기존 SRAM surrogate/simulation 레포를,  
**(a) CPU / NVIDIA CUDA 환경에서 재현 가능한 benchmark 자산**으로 만들고,  
**(b) AMD ROCm/HIP로 옮기기 쉬운 backend 구조와 문서**를 갖춘 공개 엔지니어링 레포로 개편한다.

### 1.3 왜 하는가
현재 레포는 이미 연구/검증/리포트 생성의 뼈대가 있다. 하지만 외부 기술 리뷰어나 채용 담당자가 보기에 다음 질문에 답하기가 어렵다.

- GPU 경로가 어디까지 검증되었는가?
- 성능 수치는 재현 가능한가?
- CUDA 의존성이 얼마나 강한가?
- ROCm/HIP로 옮기려면 어디를 손봐야 하는가?
- 결과의 정합성(fidelity)은 어떻게 보장하는가?
- CPU-only / GPU / native / validation 경로가 어떤 규칙으로 선택되는가?

본 프로젝트는 이 빈칸을 메워서, 레포를 “연구 스냅샷”에서 “이식성과 성능 엔지니어링을 의식한 공개 기술 자산”으로 끌어올린다.

---

## 2. 배경 및 현재 상태

### 2.1 현재 레포의 강점
현재 레포는 다음 특성을 이미 갖고 있다.

- simulation entry point, UI, validation, report generation, optional native backend 구조가 존재
- `execution_policy.py` 기반의 CPU/GPU 선택 정책이 존재
- `gpu_analytical_adapter.py`를 통해 optional PyTorch/CUDA 기반 analytical dataset + surrogate inference path가 존재
- `scripts/run_gpu_analytical_benchmark.py`를 통해 CPU existing / CPU NumPy / GPU PyTorch benchmark 뼈대가 존재
- `scripts/check_ops_plan_v1_env.py`, `scripts/verify_ops_plan_v1_outputs.py`, evidence-pack/export 스크립트가 있어 재현성 체계의 출발점이 있음
- PDK matrix / node scaling / benchmark summary 형태의 public report snapshot이 이미 있음

### 2.2 현재 레포의 약점
다음 문제 때문에 AMD/AI/HPC 포지셔닝이 약해 보일 수 있다.

1. **backend 구조가 명시적으로 portable 하지 않음**
   - GPU path가 CUDA/PyTorch 보조 경로 형태로 보임
   - CUDA touch point가 명시적으로 분리되어 있지 않음

2. **benchmark 체계가 “결과는 있으나 규격화는 덜 된 상태”**
   - 환경 정보, seed, warmup, repeat, percentile, artifact schema가 더 정형화될 필요가 있음
   - 결과가 reviewer에게 “다시 돌릴 수 있는가?”를 즉시 전달하지 못함

3. **requirements / 설치 경로가 최소 요건 중심**
   - base, UI, benchmark, dev, native 의존성이 나뉘어 있지 않음

4. **문서가 연구 스냅샷 중심**
   - portability rationale, HIP migration inventory, benchmark methodology, limitations statement가 부족

5. **report 위생 문제**
   - 일부 산출물은 로컬 절대 경로(예: Windows drive path)를 포함
   - 공개 포트폴리오 관점에서는 비식별화/상대경로화가 필요

---

## 3. 제품 비전

### 3.1 비전
이 레포를 아래처럼 인식되게 만든다.

> “SRAM surrogate/simulation workload를 대상으로, CPU와 NVIDIA GPU에서 재현 가능한 benchmark와 fidelity validation을 제공하고, AMD ROCm/HIP로의 이식 비용을 낮추도록 설계된 공개 엔지니어링 코드베이스”

### 3.2 목표 사용자
- **1차 사용자:** 레포 소유자(포트폴리오/지원 용도)
- **2차 사용자:** 기술 면접관, hiring manager, reviewer
- **3차 사용자:** 추후 재현 실행을 시도하는 외부 엔지니어
- **4차 사용자:** 나중에 AMD GPU 또는 ROCm 환경을 확보한 뒤 실제 port/validation을 수행할 미래의 자신

### 3.3 핵심 가치
- 재현 가능성
- 정직한 포터빌리티 서사
- 결과 정합성 검증
- 엔지니어링 성숙도
- 문서화/설명 가능성

---

## 4. 목표 / 비목표

## 4.1 목표 (Goals)

### G1. Backend 추상화
CPU / Torch / CUDA-specific touch point를 명시적으로 분리하여 향후 ROCm/HIP 이식 경로를 설계한다.

### G2. 재현 가능한 benchmark 체계
표준 CLI, 표준 artifact schema(JSON/CSV/Markdown), 환경 정보 기록, warmup/repeat/statistics를 도입한다.

### G3. Fidelity 검증
CPU 기준 결과와 NumPy / GPU 경로 결과 간의 수치 오차를 자동 검증한다.

### G4. 설치/환경 체계 정비
requirements를 역할별로 분리하고, Linux-first 실행 경로와 optional CUDA 경로를 분명히 한다.

### G5. 문서 자산화
README, benchmark methodology, portability plan, limitations 문서를 만들어 레포의 기술 메시지를 명확히 한다.

### G6. CI 가능성 확보
CPU-only 환경에서 최소 smoke test, schema validation, fidelity smoke, report generation이 돌아가도록 한다.

## 4.2 비목표 (Non-goals)

### NG1. AMD GPU 실측 성능 결과 생성
현재 프로젝트는 AMD GPU가 없는 조건을 전제로 한다.  
따라서 실제 AMD 성능 수치, ROCm 실측 결과, MI 시리즈 비교표는 본 스코프에 포함하지 않는다.

### NG2. 대규모 multi-node 분산학습 완성
HPC 감각은 문서/아키텍처 수준으로 반영하되, 실제 multi-node distributed training/inference 구현은 이번 범위에 포함하지 않는다.

### NG3. UI 전면 개편
Streamlit/PySide UI를 새로 디자인하는 것은 목표가 아니다. 이번 프로젝트의 중심은 backend, benchmark, docs, CI이다.

### NG4. Native backend의 실사용 HIP 포팅 완료
native extension의 HIP 포팅 후보를 식별하고 문서화할 수는 있으나, 실제 HIP 포팅과 AMD 상 검증은 미래 단계로 둔다.

---

## 5. 성공 지표 (Success Metrics)

### SM1. CPU-only 재현성
다음 명령이 CPU-only 환경에서 성공해야 한다.
- benchmark smoke suite 실행
- fidelity smoke 실행
- report generation
- environment preflight

### SM2. CUDA 환경 동작
NVIDIA GPU + PyTorch CUDA 환경에서 GPU benchmark lane이 성공해야 하며, 실패 시 명시적으로 `skipped` 또는 `unsupported` 상태로 기록되어야 한다.

### SM3. 결과 artifact 표준화
모든 benchmark run은 아래를 남겨야 한다.
- `metadata.json`
- `results.csv`
- `report.md`
- 선택 사항: `plots/*.png`

### SM4. 오차 관리
CPU 기준 lane 대비 대체 lane의 오차 threshold가 config로 정의되고 자동 검사되어야 한다.

### SM5. 문서 완성도
다음 문서가 존재해야 한다.
- README (개편)
- `docs/benchmark_methodology.md`
- `docs/backend_portability.md`
- `docs/hip_porting_plan.md`
- `docs/limitations_and_claims.md`

### SM6. 공개 레포 위생
커밋되는 산출물에는 로컬 절대 경로, 민감 식별 정보, 불필요한 대형 artifact가 포함되지 않아야 한다.

---

## 6. 제약사항 및 가정

### 6.1 제약사항
- AMD GPU 없음
- 실제 ROCm runtime 검증 불가
- 공개 레포이므로 대형 raw dump를 계속 커밋할 수 없음
- 기존 구조를 최대한 보존하면서 점진적 리팩터링이 필요함

### 6.2 가정
- 현재 사용자 환경에는 CPU-only와 NVIDIA CUDA 두 경로 모두 접근 가능할 수 있다
- Python 중심 구조는 유지한다
- native backend는 optional path로 남긴다
- 기존 report snapshot은 “대표 예시”로 유지하되, 새 표준 산출물 체계로 점진 전환한다

### 6.3 원칙
- **과장 금지:** “ROCm-ready” 표현 금지. 대신 “designed for future ROCm/HIP portability” 수준으로 서술
- **실측 우선:** 없는 수치는 만들지 않음
- **portable-first:** CUDA-specific 최적화는 분리하되, 기본 구현은 가능한 portable한 경로를 우선
- **relative-path only:** 공개 산출물에 로컬 절대경로 금지

---

## 7. 범위 정의

## 7.1 반드시 포함 (In Scope)

### S1. Backend 레이어 도입
- backend capability registry
- CPU baseline lane
- Torch portable lane
- CUDA lane (optional)
- native lane metadata hook

### S2. Benchmark 프레임워크
- benchmark case schema
- benchmark runner
- warmup + repeats
- median / mean / stdev / optional p95
- throughput / latency / fidelity metrics
- environment metadata capture

### S3. 테스트 및 검증
- smoke fidelity test
- benchmark schema validation
- CPU-only regression path
- optional CUDA smoke

### S4. 문서/README 정비
- 목적/한계/실행법/결과해석/portability/roadmap

### S5. 설치/패키징 정리
- requirements 분리
- optional extras 정의
- Linux quickstart
- optional Dockerfile 또는 reproducible environment recipe

### S6. 산출물 및 report 위생
- 결과 디렉토리 규격
- report template 통일
- 절대경로 제거
- representative snapshot policy 정의

## 7.2 선택 포함 (Stretch / Optional)
- native backend portability inventory
- minimal pyproject 도입
- plots 자동 생성
- GitHub Actions artifact upload
- benchmark comparison dashboard markdown

## 7.3 제외 (Out of Scope)
- 실제 HIP 코드 변환 완료
- ROCm CI
- AMD GPU 결과
- distributed cluster orchestration
- UI redesign

---

## 8. 요구사항 상세

## 8.1 기능 요구사항 (Functional Requirements)

### FR-1. Backend registry
시스템은 backend별 capability를 식별할 수 있어야 한다.
- backend 이름
- 사용 가능 여부
- 선택 이유
- device 정보
- precision 지원
- fallback 가능 여부

**예상 산출물**
- `backends/base.py`
- `backends/registry.py`

### FR-2. CPU baseline lane
시스템은 기존 analytical dataset + surrogate inference의 CPU 기준 경로를 제공해야 한다.
- “기존 구현” lane
- “chunked NumPy” lane

### FR-3. GPU lane
시스템은 PyTorch 기반 GPU lane을 지원해야 한다.
- CUDA available 여부를 탐지
- CUDA 미가용 시 실패가 아닌 `skipped`로 기록
- device name, torch version, precision 정보 기록

### FR-4. Portable Torch lane
시스템은 device 문자열이 고정적으로 `"cuda"`에 묶이지 않도록 설계되어야 한다.
- 내부 device abstraction 지원
- 향후 `"cuda"`, `"cpu"`, `"hip"` 또는 ROCm-compatible torch device를 수용 가능하도록 구조화

### FR-5. Benchmark suite CLI
사용자는 단일 CLI로 benchmark를 실행할 수 있어야 한다.
예:
```bash
python -m benchmarks.run_suite --suite smoke
python -m benchmarks.run_suite --suite full --device auto
python scripts/run_gpu_analytical_benchmark.py --cases 10000x512,5000x1024
```

### FR-6. Artifact schema
각 실행은 동일한 artifact 구조를 생성해야 한다.
예:
```text
artifacts/
  benchmarks/
    2026-04-17T120000Z/
      metadata.json
      results.csv
      report.md
      plots/
        throughput_vs_case.png
        error_vs_case.png
```

### FR-7. Environment metadata capture
`metadata.json`에는 최소한 다음이 포함되어야 한다.
- timestamp
- git commit hash
- python version
- OS / platform
- CPU info
- torch version (optional)
- CUDA availability / device name (optional)
- selected backend
- case definitions
- seeds
- repeat count
- warmup count

### FR-8. Fidelity validation
시스템은 lane 간 정합성을 자동 검증해야 한다.
- CPU existing vs CPU NumPy
- CPU existing vs GPU PyTorch
- max abs delta
- mean abs delta
- pass/fail 기준

### FR-9. Report generation
시스템은 machine-readable 결과뿐 아니라 human-readable markdown report를 생성해야 한다.
- case별 성능
- lane 상태
- selected engine
- device
- throughput
- fidelity summary
- notes / limitations

### FR-10. Path sanitization
공개 report 및 CSV/MD 출력에는 절대경로가 포함되지 않아야 한다.
- 입력 path는 내부적으로 받을 수 있으나 외부 report에는 relative path 또는 redacted token으로 출력

### FR-11. Requirements split
의존성은 최소 4개 그룹으로 분리한다.
- base
- benchmark
- ui
- dev
- optional native (선택)

### FR-12. Docs bundle
다음 문서를 새로 만들거나 개편해야 한다.
- README
- benchmark methodology
- backend portability
- HIP porting plan
- limitations and claims

### FR-13. CPU-only CI
GitHub Actions 또는 equivalent CI는 CPU-only 환경에서 다음을 수행해야 한다.
- import smoke
- benchmark smoke
- fidelity smoke
- schema validation
- markdown report generation

---

## 8.2 비기능 요구사항 (Non-functional Requirements)

### NFR-1. 재현 가능성
동일 seed와 동일 case 정의에서 benchmark 결과는 통계적으로 일관된 범위에 있어야 한다.

### NFR-2. 유지보수성
새 backend 추가 시 상위 application 로직을 크게 바꾸지 않아야 한다.

### NFR-3. 솔직한 포터빌리티
문서는 “가능한 구조”와 “검증된 결과”를 명확히 구분해야 한다.

### NFR-4. Linux 우선
실행 문서는 Linux-first로 정리하되, Windows 경로도 별도 보조 문서로 유지할 수 있다.

### NFR-5. CPU fallback 안전성
GPU / native 경로가 실패해도 CPU baseline 경로가 깨지지 않아야 한다.

### NFR-6. 공개 레포 적합성
대형 raw dump, local log, binary artifact는 계속 ignore 정책을 유지해야 한다.

---

## 9. 제안 아키텍처

## 9.1 목표 디렉토리 구조
```text
backends/
  __init__.py
  base.py
  registry.py
  cpu_existing.py
  cpu_numpy.py
  torch_portable.py
  cuda_lane.py

benchmarks/
  __init__.py
  schema.py
  cases.py
  env.py
  metrics.py
  runner.py
  reports.py
  cli.py

tests/
  test_backend_registry.py
  test_fidelity_smoke.py
  test_benchmark_schema.py
  test_report_generation.py

docs/
  benchmark_methodology.md
  backend_portability.md
  hip_porting_plan.md
  limitations_and_claims.md

artifacts/
  benchmarks/
```

## 9.2 기존 파일과의 관계
- `gpu_analytical_adapter.py`
  - 유지하되, 내부 구현을 `backends/torch_portable.py` 및 `backends/cuda_lane.py`로 나누는 방향
- `execution_policy.py`
  - `backends/registry.py`와 capability 기반 선택 정책으로 발전
- `scripts/run_gpu_analytical_benchmark.py`
  - benchmark suite CLI의 thin wrapper 또는 compatibility entrypoint로 유지
- `ci_regression_check.py`
  - `tests/` 및 smoke CLI로 역할 분리
- `requirements.txt`
  - `requirements-base.txt`, `requirements-benchmark.txt`, `requirements-ui.txt`, `requirements-dev.txt`로 재구성

## 9.3 설계 원칙
- 상위 business logic는 backend interface만 호출
- vendor-specific 최적화 코드는 isolate
- report writer는 backend 독립적
- env detection은 benchmark metadata와 연결
- 기존 public report snapshot은 유지하되, 새 표준 schema로 신규 산출물 생성

---

## 10. 상세 구현 계획 (Epic 기준)

## Epic A. Baseline audit & freeze
**목적:** 현재 기능을 깨뜨리지 않기 위한 기준선 확보

### 작업
- 현재 benchmark / report / fidelity / env check 동작 목록 정리
- public snapshot 기준선 목록화
- 현재 GPU benchmark script 출력 형식 캡처
- existing smoke cases 정의

### 완료 조건
- baseline inventory 문서 존재
- “리팩터링 전 기준 동작”이 정리됨

---

## Epic B. Backend abstraction
**목적:** CUDA-specific path를 격리하고 portable 구조를 만든다

### 작업
- backend interface 정의
- CPU existing, CPU NumPy, Torch portable, CUDA lane 분리
- backend registry 구현
- selected engine / reason / fallback metadata 표준화
- `execution_policy.py`와 통합

### 완료 조건
- 상위 benchmark runner가 backend registry를 통해 lane 선택
- CUDA unavailable 시 crash가 아닌 skip/fallback
- backend 정보가 artifact에 기록

---

## Epic C. Benchmark framework
**목적:** 결과를 재현 가능한 benchmark asset으로 만든다

### 작업
- case schema 정의
- warmup / repeat / statistics 구현
- metadata capture 구현
- CSV/JSON/Markdown report generator 구현
- plot generator (선택)
- CLI 구현

### 완료 조건
- 단일 command로 smoke/full suite 실행 가능
- 결과물이 표준 artifact 구조로 저장
- benchmark report가 사람 읽기 가능

---

## Epic D. Fidelity & regression
**목적:** 속도 비교뿐 아니라 수치 정합성을 보장한다

### 작업
- smoke fidelity dataset 정의
- lane pair 비교 함수 작성
- tolerance config 작성
- pass/fail report 작성
- regression smoke test 추가

### 권장 threshold 전략
- 초기 threshold는 보수적으로 시작
- 예:
  - max abs delta: `<= 1e-3`
  - mean abs delta: `<= 1e-4`
- baseline capture 이후 필요 시 tightening

### 완료 조건
- CPU existing vs CPU NumPy 비교 자동화
- CUDA 환경 시 CPU existing vs GPU PyTorch 비교 자동화
- CI에서 smoke fidelity pass 가능

---

## Epic E. Packaging & environment
**목적:** 설치와 실행을 reviewer가 이해하기 쉬운 형태로 만든다

### 작업
- requirements 분리
- optional dependency matrix 작성
- Linux quickstart 작성
- env preflight 확장
- optional Dockerfile / container recipe 작성
- path sanitization 로직 추가

### 완료 조건
- base install과 benchmark install이 분리됨
- CPU-only와 CUDA 환경 실행법이 README에 명확함
- 공개 artifact에 절대경로가 남지 않음

---

## Epic F. Documentation refresh
**목적:** 레포 메시지를 “연구 코드”에서 “엔지니어링 자산”으로 전환한다

### 작업
- README 전면 개편
- benchmark methodology 문서 작성
- backend portability 문서 작성
- HIP porting plan 문서 작성
- limitations & claims 문서 작성
- results interpretation guide 작성

### 완료 조건
- 외부 reviewer가 README만 보고도 구조/제약/실행법/한계를 이해 가능
- AMD GPU가 없다는 제약을 숨기지 않음
- CUDA->HIP 이식은 “계획과 inventory” 수준임을 명확히 함

---

## Epic G. CI / automation
**목적:** CPU-only 경로의 지속 가능성을 보장한다

### 작업
- lint / format / import smoke
- CPU benchmark smoke
- CPU fidelity smoke
- report generation smoke
- schema validation
- optional manual CUDA workflow 문서화

### 완료 조건
- main branch에서 CPU-only smoke가 자동 검증
- 로컬/CI 실행 결과가 크게 다르지 않음

---

## 11. 산출물 정의

### D1. 코드 산출물
- backend package
- benchmark package
- tests
- sanitized report pipeline
- updated wrappers

### D2. 문서 산출물
- README
- 4종 이상 docs
- migration inventory
- benchmark methodology

### D3. 결과 산출물
- representative CPU benchmark snapshot
- representative CUDA benchmark snapshot (가능한 경우)
- fidelity snapshot
- sanitized markdown reports

### D4. 운영 산출물
- CI workflow
- issue backlog
- optional release checklist

---

## 12. 수용 기준 (Acceptance Criteria)

### AC-1
`python -m benchmarks.cli --suite smoke`가 CPU-only 환경에서 성공한다.

### AC-2
`python scripts/run_gpu_analytical_benchmark.py`가 compatibility wrapper로 동작하며, 표준 artifact를 남긴다.

### AC-3
GPU 미가용 환경에서 GPU lane은 `skipped` 또는 `unsupported`로 기록되고 프로세스는 실패하지 않는다.

### AC-4
CPU existing / CPU NumPy / GPU PyTorch lane 비교 결과가 artifact에 함께 기록된다.

### AC-5
fidelity smoke 결과가 threshold와 함께 markdown report에 나타난다.

### AC-6
새로 생성되는 공개 report에는 로컬 절대경로가 포함되지 않는다.

### AC-7
README는 다음을 반드시 설명한다.
- 프로젝트 목적
- 무엇이 검증되었는지
- 무엇이 아직 검증되지 않았는지
- CPU-only 실행법
- CUDA 실행법
- 향후 ROCm/HIP 계획

### AC-8
`docs/hip_porting_plan.md`에는 최소한 다음이 포함된다.
- CUDA touch point inventory
- HIPIFY 대상 후보
- 자동 변환 한계
- manual review 필요 영역
- AMD hardware unavailable limitation

### AC-9
CI는 CPU-only smoke, schema validation, report generation을 통과한다.

---

## 13. 우선순위

### P0 (반드시)
- backend abstraction 기본형
- benchmark artifact 표준화
- fidelity smoke
- requirements 분리
- README / methodology / limitations
- path sanitization
- CPU-only CI

### P1 (강력 추천)
- HIP porting inventory
- Linux quickstart
- plot 자동 생성
- wrapper 정리

### P2 (확장)
- native portability inventory
- optional Dockerfile
- benchmark dashboard summary
- release tag / changelog automation

---

## 14. 리스크 및 대응

### R1. AMD GPU가 없어 ROCm 검증 불가
**대응**
- 구조/문서/porting inventory 중심으로 설계
- “verified”와 “planned”를 문서에서 분리
- 실제 ROCm 결과는 future milestone로 분리

### R2. 기존 레포가 넓어서 리팩터링 영향 범위가 큼
**대응**
- wrapper 유지
- compatibility layer 우선
- baseline inventory 작성 후 점진적 이동

### R3. GPU benchmark 변동성
**대응**
- warmup + repeat
- median / stdev 기록
- noise 큰 metric은 note 추가

### R4. Optional dependency가 많아 설치가 복잡함
**대응**
- requirements 분리
- preflight checker 강화
- base / benchmark / ui / dev 경로 분리

### R5. 공개 report에 로컬 정보 노출
**대응**
- path sanitization 유닛 테스트
- representative snapshot 생성 시 scrub step 포함

---

## 15. GitHub 이슈 분해안

### Issue 1 - Baseline inventory 작성
- 현재 실행 가능한 entrypoint와 existing artifacts 목록화

### Issue 2 - Backend interface 설계
- base class / capability schema / registry

### Issue 3 - CPU lanes 분리
- existing CPU lane, NumPy lane 정리

### Issue 4 - Torch portable lane 추가
- device-neutral torch path 정리

### Issue 5 - CUDA lane wrapper 정리
- CUDA available / skipped 처리

### Issue 6 - Benchmark schema 정의
- case schema / metadata / results schema

### Issue 7 - Benchmark CLI 구현
- smoke/full suite / artifact output

### Issue 8 - Fidelity smoke 구현
- lane pair comparison / tolerance config

### Issue 9 - Report generator 표준화
- markdown / csv / json / optional plot

### Issue 10 - Requirements split
- base / benchmark / ui / dev / optional native

### Issue 11 - Env preflight 확장
- CPU/CUDA install path / warnings / compatibility notes

### Issue 12 - Path sanitization
- absolute path scrub / relative path policy

### Issue 13 - README 개편
- purpose / quickstart / architecture / limitations

### Issue 14 - Benchmark methodology 문서
- warmup / repeat / statistics / fidelity 정의

### Issue 15 - HIP porting plan 문서
- CUDA touch point inventory / HIPIFY notes

### Issue 16 - CI workflow
- CPU-only smoke / schema validation / reports

### Issue 17 - Representative snapshot 갱신
- sanitized benchmark report 추가

---

## 16. 권장 실행 순서

### Sprint 1
- Baseline inventory
- Backend interface skeleton
- Benchmark schema skeleton

### Sprint 2
- CPU lanes 정리
- Torch/CUDA lane 분리
- Artifact writer 구현

### Sprint 3
- Fidelity smoke
- Report generator
- Path sanitization

### Sprint 4
- Requirements split
- README / methodology / limitations
- HIP porting plan

### Sprint 5
- CI
- Representative snapshot 갱신
- 최종 polish

---

## 17. Definition of Done

다음이 모두 만족되면 본 프로젝트는 완료로 본다.

1. CPU-only 환경에서 benchmark/fidelity/report smoke가 성공한다.
2. CUDA 환경에서 GPU lane이 동작하거나, 불가 시 graceful skip이 된다.
3. backend abstraction이 도입되어 상위 로직이 vendor-specific code에 직접 의존하지 않는다.
4. artifact schema가 고정되고 결과가 재현 가능하게 저장된다.
5. 공개 문서가 “무엇이 검증되었고 무엇이 아직 아닌지”를 정직하게 설명한다.
6. 절대경로 및 불필요한 로컬 정보가 공개 산출물에 남지 않는다.
7. ROCm/HIP 이식 계획이 문서화된다.
8. 레포가 포트폴리오/기술면접 관점에서 “성능 엔지니어링과 portability를 이해하는 엔지니어”라는 메시지를 전달한다.

---

## 18. 최종 포지셔닝 문구

이 프로젝트 완료 후 레포는 아래처럼 설명할 수 있어야 한다.

> “I converted a research-oriented SRAM surrogate simulation repository into a reproducible GPU benchmarking and portability-focused engineering codebase. The updated repo validates CPU and NVIDIA CUDA execution paths today, captures fidelity and environment metadata, and isolates CUDA-specific logic to reduce future ROCm/HIP porting cost without overstating unverified AMD support.”

---

## 19. 부록 - 최소 README 메시지 초안

README 첫 문단은 다음 메시지를 담아야 한다.

- 이 레포는 SRAM surrogate/simulation workload를 다룬다
- CPU와 NVIDIA GPU에서 benchmark/fidelity를 재현할 수 있다
- AMD GPU 실측 결과는 아직 없지만, ROCm/HIP 이식을 고려해 backend를 분리했다
- 문서에는 benchmark methodology와 porting plan이 포함된다
- 결과 해석 시 representative snapshot과 limitation 문서를 함께 봐야 한다

---

## 20. 부록 - 구현 시 주의 문구

레포/문서 어디에도 다음 표현을 쓰지 않는다.
- “ROCm-ready”
- “AMD-validated”
- “production-grade AMD support”
- “fully portable to AMD GPUs”

대신 아래 표현을 사용한다.
- “designed for future ROCm/HIP portability”
- “CUDA-specific paths are isolated to reduce porting cost”
- “ROCm validation is pending access to AMD hardware”
- “portable-first benchmark architecture”