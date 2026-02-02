# 포트폴리오 보고서 3-AI 협업 디자인 문서

## 버전 이력

| 버전 | 설명 | 스크립트/흐름 |
|------|------|----------------|
| **Version 1** | OpenAI 초안 → Grok 리뷰 → Gemini 검증 → OpenAI 최종 (4회 호출) | `본기능_동작_흐름.md` 참고. 초안 작성자가 OpenAI인 구조. |
| **Version 2** | Grok Alpha → Gemini Beta → GPT 최종 (3회 호출, 성장률 합의 중심) | `generate_portfolio_report_3ai.py` (2라운드 미포함 시 동일) |
| **Version 3** | 셋 다 **Base 시나리오** CAGR 예측 → R2 협상 → **GPT만 Bear/Bull 반영**해 최종 (5회 호출, 다중 라운드) | **현재 구현.** `generate_portfolio_report_3ai.py` |

---

# Version 3 (현재 구조 — 다중 라운드 협상)

## 1. 개요

- **목적:** 포트폴리오 구성·실시간 데이터를 바탕으로 **Grok·Gemini·GPT 셋 다 동일한 Base 시나리오(기본 시나리오)** 기준으로 CAGR을 예측하고, **2라운드에서 Grok·Gemini가 수용·반박**한 뒤, **GPT만 세 Base 비교 후 Bear/Bull을 반영**하여 최종 CAGR 및 보고서를 산출한다.
- **호출 수:** AI API **최대 5회** (Grok R1, Gemini R1, Grok R2, Gemini R2, OpenAI). R2 실패 시 해당 R2만 생략하고 Step 3 진행.
- **협의 방식:** R1 → Grok 초안·Base CAGR, Gemini 감사·Base CAGR (동일 base 전제). **R2(협상)** → Grok·Gemini 수용/반박. **R3** → GPT가 자신의 Base 예측 + Grok Base + Gemini Base를 비교하고, **여기서만 Bear case·Bull case를 고려**해 최종 CAGR 확정.

## 2. 아키텍처

```
[입력]
  · prompts/portfolio_prompt.txt, config.json, 실시간 데이터 (Version 2와 동일)

[Step 1] Grok (데이터 분석관) — R1
  → 출력: 초안 + Base 시나리오 CAGR (JSON, alpha_cagr)

[Step 2] Gemini (리스크 감사관) — R1
  → 입력: Grok 초안 + Grok Base CAGR + 포트폴리오 요약
  → 출력: 감사 리포트 + Base 시나리오 CAGR (JSON, beta_cagr)

[Step 2b - Round 2 협상]
  [Step 2b-Grok] Grok (수용·반박)
    → 입력: Gemini 감사·비판 전문 (R1 출력)
    → 출력: 수용할 부분 / 반박할 부분만 정리 (전체 초안 재작성 금지)
  [Step 2b-Gemini] Gemini (수용·반박)
    → 입력: Grok R2 수용·반박 전문
    → 출력: 수용할 부분 / 반박할 부분만 정리 (전체 감사문 재작성 금지)

[Step 3] OpenAI (수석 매니저)
  → 입력: Grok Base·Gemini Base 수치, Grok 초안, Gemini 감사, **Grok R2 수용·반박**, **Gemini R2 수용·반박**, 포트폴리오
  → 지시: (1) 자신의 Base CAGR 예측 (2) 2라운드 합의·대립 요약 (3) 세 Base 비교 (4) **Bear/Bull 반영** 후 최종 CAGR·로드맵·복리 저해 경고
  → 출력: 최종 보고서

[저장]
  · report/portfolio_report_YYYYMMDD_HHMM_....md (최종 결과)
  · report/YYYYMMDD_HHMM/step1_grok.md, step2_gemini.md, step2b_grok.md, step2b_gemini.md(선택), step3_openai.md, README.md
```

## 3. 데이터 흐름 (Version 3)

| 단계 | 입력 | 출력 |
|------|------|------|
| **1. Grok R1** | 포트폴리오, 환율·미국주가, 날짜 | 초안, Base CAGR `alpha_cagr` (JSON) |
| **2. Gemini R1** | Grok 초안, Grok Base CAGR, 포트폴리오(앞 2000자) | 감사문, Base CAGR `beta_cagr`, `risk_level`, `audit_notes` (JSON) |
| **2b-Grok** | Gemini 감사·비판 전문 | 수용·반박 요약 (전문 아님) |
| **2b-Gemini** | Grok R2 수용·반박 전문 | 수용·반박 요약 (전문 아님) |
| **3. OpenAI** | Grok Base·Gemini Base, Grok 초안, Gemini 감사, Grok R2, Gemini R2, 포트폴리오 | 세 Base 비교 후 Bear/Bull 반영해 최종 보고서·CAGR |

## 4. 합의 메커니즘 (Version 3)

1. **Grok R1:** 포트폴리오 + 실시간 데이터 기반 **Base 시나리오** CAGR 예측.
2. **Gemini R1:** 동일 **Base 시나리오** 전제에서 독립 CAGR 예측 + 감사.
3. **Grok R2:** Gemini 감사 검토 → 수용할 점 / 반박할 점만 정리.
4. **Gemini R2:** Grok R2 검토 → 수용할 점 / 반박할 점만 정리.
5. **GPT(최종):** **(1) 자신의 Base CAGR 예측** → **(2) 2라운드 합의·대립 요약** → **(3) 세 Base 비교** → **(4) Bear/Bull 반영 후 최종 전략적 CAGR 확정** 및 로드맵·복리 저해 효과 경고.

## 5. 설정·프롬프트 (Version 3)

- **2라운드 시스템 프롬프트:** `prompts/step2b_grok_system.md`, `prompts/step2b_gemini_system.md`
- **2라운드 유저 템플릿:** `prompts/step2b_grok_user_template.md` (플레이스홀더 `{{gemini_audit_text}}`), `prompts/step2b_gemini_user_template.md` (플레이스홀더 `{{grok_r2_response}}`)
- **Step 3:** `step3_openai_system.md`, `step3_user_template.md`에 2라운드 입력 `{{grok_r2_response}}`, `{{gemini_r2_response}}` 및 **세 Base 비교 + Bear/Bull 반영** 지시 반영.

---

# Version 2 (이전 구조)

## 1. 개요

- **목적:** 포트폴리오 구성·실시간 데이터를 바탕으로 **Alpha(Grok) / Beta(Gemini)** 성장률 예측을 하고, **GPT가 자체 추측과 함께 종합**하여 최종 CAGR 및 보고서를 산출한다.
- **호출 수:** AI API **3회** (Grok 1회, Gemini 1회, OpenAI 1회).
- **협의 방식:** Grok·Gemini는 **서로 논의하지 않고** 각자 1회만 출력 → GPT가 두 의견 + 자신의 추측을 **취합·조정**하여 최종 결정. (2라운드 협의는 미구현.)

## 2. 아키텍처

```
[입력]
  · prompts/portfolio_prompt.txt (포트폴리오 구성·전략)
  · prompts/config.json (portfolio_prompt_file, us_tickers)
  · 실시간 데이터: 환율(API), 미국 주가(yfinance), 한국 주가는 AI 검색

[Step 1] Grok (데이터 분석관)
  → 입력: 포트폴리오 + 실시간 데이터
  → 출력: 초안 리포트 + Alpha CAGR (JSON)

[Step 2] Gemini (리스크 감사관)
  → 입력: Grok 초안 + Alpha CAGR + 포트폴리오 요약
  → 출력: 감사 리포트 + Beta CAGR (JSON)

[Step 3] OpenAI (수석 매니저)
  → 입력: Alpha/Beta 수치 + Grok 초안 전문 + Gemini 감사 전문 + 포트폴리오
  → 출력: 최종 보고서 (자체 추측 → Alpha·Beta 반영 → 최종 CAGR·로드맵·복리 저해 경고)

[저장]
  · report/portfolio_report_YYYYMMDD_HHMM_....md (최종 결과만)
  · report/YYYYMMDD_HHMM/step1_grok.md, step2_gemini.md, step3_openai.md (각 AI 프롬프트+출력)
```

## 3. 데이터 흐름

| 단계 | 입력 | 출력 |
|------|------|------|
| **1. Grok** | 포트폴리오 본문, 환율·미국주가(API), 날짜 | 초안(마크다운), `alpha_cagr`, `current_total_krw`, `market_data` (JSON) |
| **2. Gemini** | Grok 초안 전문, Alpha CAGR, 포트폴리오(앞 2000자) | 감사문(마크다운), `beta_cagr`, `risk_level`, `audit_notes` (JSON) |
| **3. OpenAI** | Alpha/Beta 수치, Grok 초안 전문, Gemini 감사 전문, 포트폴리오 | 최종 보고서(마크다운), 최종 CAGR 반영 |

- **JSON 파싱:** Grok/Gemini 출력 하단에서 정규식으로 JSON 블록 추출. 실패 시 해당 수치는 `N/A`로 전달.

## 4. 합의 메커니즘 (Version 2)

1. **Grok(Alpha):** 포트폴리오 구성 + 실시간 시장·경제 데이터 기반으로 **예상 CAGR** 제안.
2. **Gemini(Beta):** Grok 초안·Alpha를 비판적으로 검토, 거시·리스크 반영 **보수적 CAGR** 제안.
3. **GPT(최종):** **(1) 자체 추측** → **(2) Alpha·Beta 의견 검토** → **(3) 세 관점 종합**하여 최종 전략적 CAGR 확정 및 로드맵·복리 저해 효과 경고.

- Grok과 Gemini 간 **직접 협의(왕복)** 없음. GPT가 유일한 “취합·조정” 주체.

## 5. 입출력·저장

- **최종 결과:** `report/` 디렉터리에만 저장. 파일 1개: `portfolio_report_YYYYMMDD_HHMM_<모델접미사>.md`.
- **중간 데이터:** `report/YYYYMMDD_HHMM/` 하위에 **AI별 1파일** (시스템 프롬프트 + 유저 프롬프트 + 출력).
  - `step1_grok.md`, `step2_gemini.md`, `step3_openai.md`, `README.md`.

## 6. 설정·프롬프트 외부화

- **설정:** `prompts/config.json` — `portfolio_prompt_file`, `us_tickers` 등. 스크립트는 경로·종목을 여기서만 읽음.
- **시스템 프롬프트:** `prompts/step1_grok_system.md`, `step2_gemini_system.md`, `step3_openai_system.md`.
- **유저 템플릿:** `prompts/step1_user_template.md`, `step2_user_template.md`, `step3_user_template.md`.
- **폴백:** `prompts/fallback_grok_system.md`, `fallback_gemini_system.md`, `fallback_openai_system.md` (step N 파일 없을 때 사용).

## 7. 부가 기능

- **디버그 모드:** `--debug-step 1|2|3|4|5` — 1=Grok R1, 2=+Gemini R1, 3=+Grok R2, 4=+Gemini R2, 5=+OpenAI. 해당 단계까지 실행 후 **해당 AI와 추가 질문 대화** (동일 AI와 히스토리 유지).
- **데이터 조회 테스트:** `--test-data-fetch` — 환율·미국 주가 API만 호출, AI 미호출.
- **모델 검증:** `--test-models` — 각 AI에 짧은 프롬프트 1회 전송, 요청/실제 모델명만 출력.

## 8. 비용 참고

- 1회 생성 시 **약 $0.85** (Grok 4.1 Fast, Gemini 3 Flash, gpt-5.2 기준). 상세는 `docs/모델_가격_비교.md` 참고.

---

## 9. 관련 문서

- **성장률 합의 상세:** `docs/성장률_합의_프로세스.md`
- **모델·폴백·비용:** `docs/모델_가격_비교.md`, `docs/권장_모델_및_폴백.md`
- **프롬프트 폴더:** `prompts/README.md`
