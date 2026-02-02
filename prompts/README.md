# prompts 디렉토리

포트폴리오 보고서 생성 스크립트에서 사용하는 **프롬프트·구성 정보**를 모아 둔 폴더입니다.  
**포트폴리오·프롬프트 관련 내용은 스크립트에 두지 않고 모두 이 폴더에서만 관리**합니다.  
파일만 수정하면 다음 실행부터 적용됩니다. (스크립트 수정 불필요)

**역할 분리:** 사용자별 **구체적·개인적 목표**(연도·금액·인출 계획·종목 등)는 **`portfolio_prompt.txt`에만** 두고, step1/2/3 시스템·유저 프롬프트는 **역할(role)·출력 형식·절차**만 정의합니다. 목표·숫자는 "포트폴리오에 명시된 …"처럼 참조만 하면 수정 시 한 곳만 바꾸면 됩니다.

---

## 0. 설정 (config.json)

| 파일 | 용도 |
|------|------|
| **`config.json`** | **경로·종목 목록 등**을 한곳에서 관리. 스크립트는 이 파일만 읽고, 포트폴리오/프롬프트 파일명·종목 리스트를 하드코딩하지 않습니다. |

**config.json 예시:**

- **`portfolio_prompt_file`** — 포트폴리오 본문 파일명 (prompts/ 기준). 예: `"portfolio_prompt.txt"`
- **`us_tickers`** — 미국 주가 API(yfinance)로 조회할 종목 코드 배열. 예: `["TSLA", "MAGS", "SMH", "MSTR", "MELI", "NU"]`
- **`stock_price_test_prompt`** — (선택) 주가 실시간 조회 테스트용 프롬프트 문구. 없으면 기본 문구 사용.

---

## 1. 포트폴리오 구성 정보

| 파일 | 용도 |
|------|------|
| **`portfolio_prompt.txt`** | **포트폴리오 구성·운영 전략** 본문. 목표, 법인/개인 계좌 종목·수량·평단가, 운영 전략, 보고서 구조·수행 지침, 톤앤매너 등. 실제 파일명은 `config.json`의 `portfolio_prompt_file`로 지정합니다. |

- **기본 파일명:** `config.json`에 없으면 `portfolio_prompt.txt`를 사용합니다.
- **인코딩:** UTF-8
- **구체적 목표(연도·금액·마일스톤 등)는 이 파일에만 두세요.** step1/2/3 템플릿에는 목표 숫자를 적지 말고, "포트폴리오에 명시된 목표"처럼만 참조하면 수정 시 한 곳만 바꾸면 됩니다.

---

## 2. 3-AI 폴백 시스템 프롬프트 (역할 지시 보조)

step1/2/3 시스템 프롬프트 MD 파일이 없을 때 사용하는 **폴백**입니다.  
역할·회사명 등 문구를 바꾸려면 이 파일들을 수정하면 됩니다. (스크립트에 문구 없음)

| 파일 | 용도 |
|------|------|
| **`fallback_grok_system.md`** | Grok — 데이터 분석관 (step1_grok_system.md 없을 때) |
| **`fallback_gemini_system.md`** | Gemini — 리스크 감사관 (step2_gemini_system.md 없을 때) |
| **`fallback_openai_system.md`** | OpenAI — 수석 매니저 (step3_openai_system.md 없을 때) |

---

## 3. 3-AI 협업용 시스템 프롬프트 (역할 지시)

각 AI의 **역할·성격**을 정하는 시스템 프롬프트입니다.

| 파일 | 용도 |
|------|------|
| **`step1_grok_system.md`** | **Grok** — 데이터 분석관. 전 종목 테이블화, 실시간 환율·종가 반영, **Base 시나리오** CAGR 예측. 출력 하단 JSON(`alpha_cagr`, `current_total_krw`, `market_data`) 포함 지시. |
| **`step2_gemini_system.md`** | **Gemini** — 리스크 감사관. Grok 초안 참고, **동일 Base 시나리오** 기준 독립 CAGR 산출. 출력 하단 JSON(`beta_cagr`, `risk_level`, `audit_notes`) 포함 지시. |
| **`step3_openai_system.md`** | **OpenAI** — 수석 매니저. 세 Base CAGR 비교 후 **Bear/Bull 반영**해 최종 CAGR 확정, 전 종목 포함, 복리 저해 효과 경고. HTML 금지, 등락 기호·볼드만 사용. |

---

## 4. 3-AI 협업용 유저 프롬프트 템플릿 (본문 + 치환자)

각 단계에서 AI에게 넘기는 **유저 메시지** 템플릿입니다. 아래 치환자가 실행 시 채워집니다.

| 파일 | 용도 | 치환자 |
|------|------|--------|
| **`step1_user_template.md`** | Grok에 넘길 유저 메시지 | `{{date_str}}`, `{{yesterday_str}}`, `{{realtime_data}}`, `{{portfolio_prompt_content}}` |
| **`step2_user_template.md`** | Gemini에 넘길 유저 메시지 | `{{alpha_cagr}}`, `{{draft_report}}`, `{{portfolio_prompt_content}}` (앞 2000자) |
| **`step3_user_template.md`** | OpenAI에 넘길 유저 메시지 | `{{alpha_cagr}}`(Grok Base), `{{beta_cagr}}`(Gemini Base), `{{grok_draft}}`, `{{gemini_audit_text}}`, `{{portfolio_prompt_content}}` |

- **`{{portfolio_prompt_content}}`** → 위 `portfolio_prompt.txt` 내용이 주입됩니다.
- **인코딩:** UTF-8. MD만 편집하면 다음 실행부터 적용됩니다.

---

## 요약

| 구분 | 파일 | 설명 |
|------|------|------|
| 설정 | `config.json` | 포트폴리오 파일명, US 종목 목록, (선택) 주가 테스트 프롬프트 |
| 구성 정보 | `portfolio_prompt.txt` | 포트폴리오 종목·전략·보고서 지침 (파일명은 config에서 지정) |
| 폴백 (3-AI) | `fallback_grok_system.md`, `fallback_gemini_system.md`, `fallback_openai_system.md` | step N 시스템 MD 없을 때 사용할 역할 문구 |
| Step 1 (Grok) | `step1_grok_system.md`, `step1_user_template.md` | 데이터 분석관 역할 + 유저 메시지 템플릿 |
| Step 2 (Gemini) | `step2_gemini_system.md`, `step2_user_template.md` | 리스크 감사관 역할 + 유저 메시지 템플릿 |
| Step 3 (OpenAI) | `step3_openai_system.md`, `step3_user_template.md` | 수석 매니저 역할 + 유저 메시지 템플릿 |

시스템 프롬프트 MD가 없으면 **fallback_*_system.md**를 사용하고, 그것도 없으면 스크립트의 최소 문구를 사용합니다.
