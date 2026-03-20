# PDK Validation Criteria and Decision Rules

작성일: 2026-02-17  
대상: `SRAM-Simulator-with-perceptron`

---

## 1) 평가 축 분리 (핵심 원칙)

정확도 판단은 반드시 3개 축으로 분리한다.

1. **SPICE vs Silicon (SPICE 물리 정확도)**
- 목적: SPICE 자체가 실측을 얼마나 맞추는지 검증

2. **Perceptron vs SPICE (Surrogate 근사 정확도)**
- 목적: Perceptron이 pre-silicon golden(SPICE)을 얼마나 빠르게/정확히 근사하는지 검증

3. **Perceptron vs Silicon (최종 실사용 정확도)**
- 목적: end-to-end에서 Perceptron 예측이 실측에 유효한지 검증

판정 원칙:
- pre-silicon 단계에서는 `Perceptron vs SPICE`가 주 평가축
- post-silicon 단계에서는 최종 판정축을 `Perceptron vs Silicon`으로 승격

---

## 2) 데이터셋 최소 요구사항

## 공통 샘플링
- Corner: `TT/FF/SS` 필수 (가능하면 `FS/SF` 추가)
- Temperature: 최소 3점 (`-40C`, `25C`, `125C`)
- VDD: nominal ±10% 이상
- Macro/array 조건: 최소 2개 이상 (예: 1kb, 64kb)

## 샘플 수
- SPICE PVT grid: 최소 45 포인트
- Monte Carlo: 포인트당 최소 200 (권장 500+)
- Silicon correlation: 조건당 wafer/lot/temperature 반복 확보

---

## 3) 메트릭 정의

필수 메트릭:
- `SNM` (mV): hold/read/write 분리 권장
- `Read Fail Rate`
- `Write Fail Rate`
- `BER`
- `Noise Sigma` (정의 고정 필요)
- `Leakage`

평가 통계:
- `MAE`, `RMSE`, `R2`
- `Max |Error|` (worst-case safety)
- `P95 |Error|`
- Corner별 편향(`signed mean error`)

---

## 4) 합격 기준 (Gate)

## Gate A: SPICE vs Silicon (SPICE signoff 신뢰도)
- MAE(SNM mV) <= 8
- P95 |SNM error| <= 15 mV
- MAE(log10 BER) <= 0.30 decade
- Read/Write fail rate 오차 <= 20% (relative)
- Corner별 systematic bias가 동일 방향으로 2개 corner 이상 누적되면 fail

## Gate B: Perceptron vs SPICE (Surrogate 승인)
- MAE(SNM mV) <= 10
- MAE(noise sigma) <= 0.02
- MAE(log10 BER) <= 0.35 decade
- Max |delta BER| <= 0.05 (absolute)
- Inference latency 개선 >= 50x (vs SPICE wall-clock)

## Gate C: Perceptron vs Silicon (최종 승격)
- MAE(SNM mV) <= 12
- MAE(log10 BER) <= 0.40 decade
- Read/Write fail rate 오차 <= 25% (relative)
- Safety-critical corner(SS, high-T, low-V)에서 fail-rate 과소예측 금지

주의:
- Gate C 통과 전에는 대외 문구를 `silicon-correlated`로 표기하지 않는다.

---

## 5) 판정 규칙 (SPICE가 더 정확한가? Perceptron이 더 정확한가?)

## Rule 1. 실리콘 데이터 없음 (pre-silicon)
- 판정 대상: `Perceptron vs SPICE`
- 결론 표현:
  - "Perceptron이 SPICE를 X 오차로 근사"
  - "SPICE가 절대적으로 더 정확"이라는 표현은 금지(실측 부재)

## Rule 2. 실리콘 데이터 있음 (post-silicon)
- 비교:
  - `Err_spice = metric(SPICE, Silicon)`
  - `Err_perc = metric(Perceptron, Silicon)`
- 판정:
  - `Err_perc < Err_spice`가 핵심 메트릭 60% 이상에서 일관되면 Perceptron 우세
  - 반대면 SPICE 우세
  - 차이가 미미하면 "동등" + 속도/운영비 기준으로 선택

## Rule 3. 안전성 우선
- worst-case corner에서 과소예측(낙관적 오판) 모델은 우세 판정 금지
- 필요 시 보수 보정(guard-band) 후 재평가

---

## 6) 리포트 템플릿 필수 항목

모든 공식 리포트 상단에 아래 항목 고정:
- Data source: `proxy-calibrated | foundry PDK deck correlated | silicon-correlated`
- PDK version / simulator / corner map / temperature grid
- Monte Carlo sample count
- metric definitions revision
- pass/fail summary by gate

---

## 7) 문구 가이드 (대외 발표)

- Gate A/B만 통과: `Foundry PDK deck correlated (pre-silicon)`
- Gate C 통과: `Silicon-correlated`
- proxy만 있는 경우: `Proxy-calibrated node-profile benchmark`

금지 문구:
- "PDK signoff validated" (Gate A 통과 전)
- "silicon accurate" (Gate C 통과 전)

---

## 8) 현재 프로젝트에 즉시 적용할 액션

1. `ci_regression_check.py`에 `log10 BER` 오차 지표 추가
2. `spice_validation/reports/*` 템플릿에 data source header 강제
3. `scripts/run_node_scaling.py` 보고서에 `proxy-calibrated` 표기 유지
4. PDK 연동 완료 후 Gate A/B/C 판정표 자동 생성 스크립트 추가
