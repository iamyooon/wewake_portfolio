# 3단계 성장률 합의 프로세스

**Grok(1차 예측) → Gemini(2차 예측) → GPT(최종 결정)** 로 이어지는 성장률 합의 시스템입니다.

## 흐름 요약

| 단계 | AI | 역할 | 출력 |
|------|-----|------|------|
| 1 | **Grok** | 데이터 분석관, Alpha CAGR 예측 | 초안 + `alpha_cagr`, `current_total_krw`, `market_data` (JSON) |
| 2 | **Gemini** | 리스크 감사관, Beta CAGR 예측 | 감사 보고서 + `beta_cagr`, `risk_level`, `audit_notes` (JSON) |
| 3 | **GPT** | 수석 매니저, 최종 CAGR 확정 | 최종 보고서 (로드맵, 복리 저해 효과 경고 포함) |

## Step 1: Grok (Alpha)

- **시스템 프롬프트:** 위웨이크 **데이터 분석관** (실시간 시장 모멘텀·기술적 분석)
- **유저 프롬프트:** `[Step 1 - 데이터 분석관용]` + 포트폴리오 + 실시간 데이터 + 전 종목 테이블화·Alpha CAGR·JSON 지시
- **임무:** 전 종목 테이블화, web_search로 환율·종가 반영, MSTR NAV·테슬라 모멘텀 분석, **Alpha CAGR** 산출
- **JSON:** `{"alpha_cagr": 0.0, "current_total_krw": 0, "market_data": {...}}`

## Step 2: Gemini (Beta)

- **시스템 프롬프트:** 위웨이크 **리스크 감사관** (거시 경제·구글 검색 기반 보수적)
- **유저 프롬프트:** `[Step 2 - 리스크 감사관용]` + Grok 초안 + Alpha CAGR + Beta·risk_level·audit_notes JSON 지시
- **임무:** Grok 초안·Alpha 검토, 구글 서칭으로 거시 경제·블랙스완 확인, **Beta CAGR** 산출 (Grok보다 보수적)
- **JSON:** `{"beta_cagr": 0.0, "risk_level": "low/mid/high", "audit_notes": "..."}`

## Step 3: GPT (최종 결정)

- **시스템 프롬프트:** 위웨이크 **수석 포트폴리오 매니저** (자체 추측 후 Grok·Gemini 의견 반영, Thinking 모드·복리 저해 효과 경고)
- **유저 프롬프트:** `[Step 3 - 수석 매니저용]` + Alpha/Beta 수치 + Grok 초안 전문 + Gemini 감사 전문 + (1) 자체 CAGR 추측 (2) Alpha·Beta 반영 (3) 최종 CAGR 확정·로드맵·복리 저해 효과 지시
- **임무:** **(1) 자체 추측** → **(2) Grok(Alpha)·Gemini(Beta) 의견 검토** → **(3) 세 관점 종합하여 최종 전략적 CAGR** 확정, 전 종목 포함, 로드맵 작성, **월 1,100만 원 인출 복리 저해 효과(Compounding Penalty)** 정밀 계산·경고
- **포맷:** HTML 금지, 등락 기호(▲▼+-), 볼드체(**), 논리적 근거(Why) 포함

## 합의 메커니즘

1. **Grok(Alpha):** 시장 모멘텀 기반 성장률 제안
2. **Gemini(Beta):** 거시·리스크 기반 보수적 성장률 제안
3. **GPT(최종):** **자체 추측**을 한 뒤 Grok·Gemini 의견을 **고려하여** 세 관점을 종합한 최종 CAGR 확정 및 로드맵·경고 반영

## CAGR 안정화 및 구간별 감쇠 (최근 반영)

- **temperature=0:** 모든 AI 호출(Grok, Gemini, OpenAI)에서 `temperature=0` 사용. 실행마다 CAGR이 크게 흔들리던 현상을 완화함(예: 4회 테스트 시 최종 CAGR 변동 폭 약 6.7%p → 1.2%p).
- **구간별 감쇠 제안:** 고정 비율(90/75/50) 대신, **Grok**이 구간별 감쇠율을 근거와 함께 제안하고, **Gemini**가 검토·제안하며, **OpenAI**가 최종 확정. Step1/Step2/Step2b/Step3 프롬프트에 반영됨.

## 스크립트 연동

- `generate_portfolio_report_3ai.py` 에서 위 3단계가 순차 호출됩니다.
- **시스템 프롬프트**는 스크립트 밖 **`prompts/`** 폴더의 MD 파일에서 읽습니다.
  - `prompts/step1_grok_system.md` — Grok
  - `prompts/step2_gemini_system.md` — Gemini
  - `prompts/step3_openai_system.md` — OpenAI
- Grok/Gemini 출력에서 JSON을 파싱해 Alpha/Beta CAGR을 추출하고, GPT 최종 프롬프트에 주입합니다.
- 생성된 보고서 파일 상단에 `성장률 합의: Alpha(Grok) X% → Beta(Gemini) Y% → GPT 최종 확정` 이 기록됩니다.
