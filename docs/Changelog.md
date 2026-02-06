# 추가·변경 기능 이력

설계/동작/가이드 문서와 동기화하기 위한 **추가된 기능**과 **변경된 기능** 요약. (반영 시점: 2026-02)

---

## 1. API·안정화

### 1.1 temperature=0 통일 (CAGR 변동 완화)
- **변경:** 모든 AI 호출(Grok, Gemini, OpenAI)에서 `temperature=0` 사용.
- **목적:** 실행마다 CAGR이 12% vs 18%처럼 크게 흔들리던 현상을 완화. 4회 테스트 시 최종 CAGR 변동 폭이 약 6.7%p → 1.2%p로 축소됨.
- **참고:** `scripts/generate_portfolio_report_3ai.py` 상단 `API_TEMPERATURE = 0` 및 주석.

### 1.2 CAGR 전용 테스트 옵션
- **추가 옵션:**
  - `--test-cagr-only`: CAGR 예측만 1회 (Grok→Gemini→OpenAI 최소). 보고서 미생성.
  - `--test-cagr-runs N`: CAGR 예측만 N회 연속 수행 후 요약 표 출력 (temperature 효과 비교용).
- **용도:** 풀 보고서 없이 3-AI CAGR만 반복 실행해 변동 확인.

---

## 2. 보고서 구조·내용

### 2.1 보고서 구성 순서 (재구성)
- **순서:** 실행 요약 → 현재 상황 분석 → CAGR 분석 및 전략 → 지출 시나리오 정의 → 시나리오별 자산 추이 분석 → 추가 분석 → 액션플랜.
- **반영 위치:** `prompts/portfolio_prompt.txt` Step 4, `prompts/step3_openai_system.md`.

### 2.2 구간별 CAGR 감쇠 (고정값 → AI 제안)
- **변경:** 2034 90% / 2035~2039 75% / 2040+ 50% 고정 대신, **Grok·Gemini·OpenAI가 구간별 감쇠율을 근거와 함께 제안**하도록 변경.
- **반영:** `portfolio_prompt.txt`, `step1_grok_system.md`, `step2_gemini_system.md`, `step3_openai_system.md`, step2b 프롬프트.

### 2.3 자산 추이 계산 방식
- **단위:** 시나리오별 자산 추이 표 **억원** 통일.
- **계산:** 연초자산에 CAGR 성장 적용 후, 해당 연도 인출/추가투자를 **연말에 반영**(보수적). 성장은 연말 일괄 반영.
- **목표 달성 판정:** 각 시나리오마다 **2035년 말 자산 기준 연 4% 인출 시 월 가능 인출액(만원)** 요약 표 추가.

### 2.4 가족 부양 예측
- **변경:** "데이터 부재" 등 불필요한 사유 표기 금지. 보고서 내 자산 추이·4% 인출액으로 산출 가능하므로 범위만 명시.

---

## 3. 데이터·주가 기준

### 3.1 미국 주가: 정규장 종가 기준 + 애프터마켓 명시
- **평가·계산:** **정규장 종가(regular)** 기준으로 포트폴리오 평가 및 보고서 본문 사용.
- **보고서 표기:** 정규장 종가와 함께 **애프터마켓 가격도 함께 명시**.
- **반영:** `_best_usd_price()` 우선순위 regular → post → pre, 프롬프트/portfolio_prompt/step3 지침.

---

## 4. 디버그·유틸리티

### 4.1 Debug Step 0 (환율·주가 확인)
- **추가:** `--debug-step` 실행 시 **가장 먼저** Step 0으로 환율·미국 주가 확인 블록 출력 후 Step 1~5 진행.
- **함수:** `_print_exchange_and_stock_prices()`.

### 4.2 환율·주가만 실행 옵션
- **옵션:** `--check-prices` (별도 실행용). `--test-data-fetch`와 동일하게 환율·주가 API 조회만 수행 후 종료.

---

## 5. TBD (추후 논의·미적용)

- **기존 예측 CAGR 참고:** 당장은 적용 안 함. temperature=0으로 변동 충분히 완화. 나중에 필요 시 구현 검토. → `docs/TBD.md`
- **액션플랜 3-AI 논의:** 현행 OpenAI 단독 유지. 필요 시 Step 2/2b에 액션플랜 초안 논의 추가 검토. → `docs/TBD.md`

---

## 6. 문서 간 참조

- **PDR:** `PDR_Multi_AI_Portfolio_Report.md` — 프로젝트 개요·기능 요구사항·기술 스택. 변경 사항은 본 이력 문서 참조.
- **설계:** `docs/3AI_Report_Design.md` — Version 3 아키텍처·데이터 흐름. 보고서 구조·감쇠 제안·temperature 반영.
- **동작 흐름:** `docs/Main_Flow.md` — 실제 5단계 흐름 및 CLI 옵션.
- **성장률:** `docs/Growth_Rate_Agreement_Process.md` — CAGR 합의 메커니즘. temperature·감쇠 제안 반영.
- **스크립트 가이드:** `scripts/README_3AI.md` — 사용법·옵션. 새 옵션 및 동작 반영.
