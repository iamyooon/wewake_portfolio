# prompts/ 파일별 역할 정리

포트폴리오 보고서 생성 스크립트에서 사용하는 **프롬프트·구성 정보**를 이 폴더에서만 관리합니다.  
파일만 수정하면 다음 실행부터 적용되며, 스크립트 수정은 필요 없습니다.  
목표·숫자 등 **구체적 내용은 `portfolio_prompt.txt`에만** 두고, step 프롬프트는 역할·형식·절차만 정의합니다.

---

## 0. 설정

| 파일 | 역할 |
|------|------|
| **config.json** | 스크립트 공통 설정. `portfolio_prompt_file`(포트폴리오 파일명), `us_tickers`(미국 주가 조회 종목), `portfolio_holdings`(보유 종목·현금·API 평가용) 등. |

---

## 1. 포트폴리오 본문 (한 곳만 수정)

| 파일 | 역할 |
|------|------|
| **portfolio_prompt.txt** | **목표·계좌·종목·운영 전략·보고서 구조** 등 포트폴리오 전반. Persona, 실시간 데이터 지침, 보유 자산(Cost Basis), 운용 로직·제약, **스윙트레이딩 규칙**(현금 10%+TSLA 10%+MSTR 10% 활용, 매매 시점 조언 포함), 보고서 구조·출력 지침, Tone & Manner. Step1/2/3는 이 내용을 **참조만** 하고, 목표·숫자는 여기만 바꾸면 됨. |

---

## 2. 폴백 시스템 프롬프트 (파일 없을 때만 사용)

| 파일 | 역할 |
|------|------|
| **fallback_grok_system.md** | Step1 시스템 파일(`step1_grok_system.md`)이 없을 때 쓰는 **Grok용 최소 시스템** (데이터 분석관 + JSON 출력 지시). |
| **fallback_gemini_system.md** | Step2 시스템 파일이 없을 때 쓰는 **Gemini용 최소 시스템** (리스크 감사관 + JSON 출력 지시). |
| **fallback_openai_system.md** | Step3 시스템 파일이 없을 때 쓰는 **OpenAI용 최소 시스템** (수석 매니저 + 포맷 지시). |

---

## 3. 1라운드 — Step 1 (Grok, 데이터 분석관)

| 파일 | 역할 |
|------|------|
| **step1_grok_system.md** | Grok **시스템** 역할: 데이터 분석관, 전 종목 테이블화·실시간 환율·종가 반영, **Base 시나리오 CAGR** 예측, **스윙트레이딩 매매 조언**(언제 매도·매수할지 가격대/구간/트리거), 출력 하단 JSON(`alpha_cagr`, `current_total_krw`, `market_data`) 지시. |
| **step1_user_template.md** | Grok **유저** 메시지 템플릿. 치환: `{{date_str}}`, `{{yesterday_str}}`, `{{realtime_data}}`, `{{portfolio_prompt_content}}`. 초안 구조·실시간 데이터 사용·CAGR·JSON 형식 지시. |

---

## 4. 1라운드 — Step 2 (Gemini, 리스크 감사관)

| 파일 | 역할 |
|------|------|
| **step2_gemini_system.md** | Gemini **시스템** 역할: 리스크 감사관, Grok와 **동일 Base 시나리오** 전제로 **독립 CAGR** 예측, Grok **스윙 매매 조언 검토**(타이밍·과매매 리스크, 동의/이견), 출력 JSON(`beta_cagr`, `risk_level`, `audit_notes`) 지시. |
| **step2_user_template.md** | Gemini **유저** 메시지 템플릿. 치환: `{{alpha_cagr}}`, `{{draft_report}}`, `{{portfolio_prompt_content}}`(앞 2000자만). Base 시나리오·2라운드 입력용 Grok 초안 전문 포함. |

---

## 5. 2라운드 — Step 2b (Grok·Gemini 수용·반박)

| 파일 | 역할 |
|------|------|
| **step2b_grok_system.md** | Grok **시스템**: Gemini 비판 검토 후 **수용 목록 + 반박만** 출력, 초안 재작성 금지. |
| **step2b_grok_user_template.md** | Grok **유저** 템플릿. 치환: `{{gemini_audit_text}}`(Gemini 감사·비판 전문). |
| **step2b_gemini_system.md** | Gemini **시스템**: Grok 수용·반박 검토 후 **수용 목록 + 반박만** 출력, 감사문 재작성 금지. |
| **step2b_gemini_user_template.md** | Gemini **유저** 템플릿. 치환: `{{grok_r2_response}}`(Grok 2라운드 응답). |

---

## 6. 3라운드 — Step 3 (OpenAI, 수석 매니저)

| 파일 | 역할 |
|------|------|
| **step3_openai_system.md** | OpenAI **시스템** 역할: 수석 매니저, 자신의 Base CAGR 예측 → **세 Base 비교** → Bear/Bull 반영해 **최종 CAGR 확정**, **스윙트레이딩 매매 조언** 섹션(언제 매도·매수 제안) 포함, 전 종목·로드맵·복리 경고, 포맷·**출력 간결화** 지침. |
| **step3_user_template.md** | OpenAI **유저** 메시지 템플릿. 치환: `{{alpha_cagr}}`, `{{beta_cagr}}`, `{{grok_draft}}`, `{{gemini_audit_text}}`, `{{grok_r2_response}}`, `{{gemini_r2_response}}`, `{{portfolio_prompt_content}}`(앞 3000자). 시스템 지침 준수·간결 작성 요약. |

---

## 7. 문서

| 파일 | 역할 |
|------|------|
| **README.md** | 위와 같은 **역할 분리·파일 용도** 설명, config·portfolio·폴백·step1/2/2b/3 사용법 안내. |

---

## Step별 진행 요약

| Step | 담당 | 하는 일 |
|------|------|--------|
| **1** | Grok | **CAGR(α) + 시장 해석·리스크 논의** (보고서 초안 전체 X) |
| **2** | Gemini | Step 1 논의 **검토** + **CAGR(β) + 시장·리스크 검토 논의** (감사문 전문 X) |
| **3** | Grok | Step 2 검토에 대한 **수용 + 반박**만 |
| **4** | Gemini | Step 3(Grok 2라운드)에 대한 **수용 + 반박**만 |
| **5** | OpenAI | (자기) CAGR 예측 + α·β·논의 반영 → **세 Base 비교·Bear/Bull 확정** + **보고서 전문 작성** |

- Step 1~4: **CAGR 예측**과 **시장 해석·리스크 논의**만. 보고서 본문은 쓰지 않음.
- Step 5: 논의 내용을 반영해 **보고서 전체**(자산현황, 지출 시나리오, 연도별 추이, 가족 부양 등)를 **한 번에** 작성.

---

## 요약 흐름

- **config.json** → 어떤 포트폴리오 파일·종목·보유 데이터 쓸지 결정.  
- **portfolio_prompt.txt** → “무엇을 목표로, 어떤 자산·규칙으로 보고서를 만들지”의 **단일 원천**.  
- **step1** → Grok가 **CAGR(α) + 시장해석·리스크 논의** 출력.  
- **step2** → Gemini가 **검토 논의 + CAGR(β)** 출력.  
- **step2b** → Grok·Gemini가 서로 **수용·반박만** 정리.  
- **step3** → OpenAI가 **세 Base 비교·Bear/Bull 확정 + 보고서 전문** 작성.  
- **fallback_*.md** → 해당 step의 시스템 파일이 없을 때만 쓰는 **최소 역할·형식** 지시.

---

## 플로우 변경 (CAGR·논의 중심) 및 비용 변화

**변경 요약:** Step 1·2에서 "보고서 초안 전문"·"감사문 전문"을 쓰지 않고, **CAGR + 시장 해석·리스크 논의**만 출력하도록 바꿨다. 시장 해석·리스크는 CAGR 논의 과정에서 이미 다루어지므로, Step 5(OpenAI)가 이 논의를 참고해 보고서 전문을 한 번에 작성해도 결과는 기존과 크게 다르지 않다.

| 구분 | 변경 전 | 변경 후 | 비용 영향 |
|------|--------|--------|-----------|
| **Step 1 (Grok)** | 초안 전문(목표·마켓·자산표·로드맵 등 전체) + α + JSON | 자산 요약·시장 해석·CAGR 근거(시장·리스크) + α + JSON | **출력 토큰 감소** (긴 초안 제거) |
| **Step 2 (Gemini)** | 초안 전문 입력 + 감사문 전문 출력 + β + JSON | Grok 논의(짧은 입력) + 검토 논의(짧은 출력) + β + JSON | **입·출력 토큰 감소** |
| **Step 3·4 (2라운드)** | 수용·반박 | 수용·반박 (동일) | 변화 없음 |
| **Step 5 (OpenAI)** | 초안·감사문 전문 + α·β·2라운드 + portfolio → 최종 보고서 | Grok·Gemini 논의(짧은 입력) + α·β·2라운드 + portfolio → 최종 보고서 | **입력 토큰 감소** |

**예상 효과:** 1회 실행 시 Grok 출력·Gemini 입·출력·OpenAI 입력이 줄어 **전체 토큰 사용량 감소**. 절감 폭은 기존 초안·감사문 길이에 따라 다르며, **수천~수만 토큰** 규모 절감 가능.
