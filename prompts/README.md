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
| **portfolio_prompt.txt** | **목표·계좌·종목·운영 전략·보고서 구조** 등 포트폴리오 전반. Persona, 실시간 데이터 지침, 보유 자산(Cost Basis), 운용 로직·제약, 보고서 구조·출력 지침, Tone & Manner. Step1/2/3는 이 내용을 **참조만** 하고, 목표·숫자는 여기만 바꾸면 됨. |

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
| **step1_grok_system.md** | Grok **시스템** 역할: 데이터 분석관, 전 종목 테이블화·실시간 환율·종가 반영, **Base 시나리오 CAGR** 예측(연단위·다년도), 출력 하단 JSON(`alpha_cagr`, `current_total_krw`, `market_data`) 지시. |
| **step1_user_template.md** | Grok **유저** 메시지 템플릿. 치환: `{{date_str}}`, `{{yesterday_str}}`, `{{realtime_data}}`, `{{portfolio_prompt_content}}`. 초안 구조·실시간 데이터 사용·CAGR·JSON 형식 지시. |

---

## 4. 1라운드 — Step 2 (Gemini, 리스크 감사관)

| 파일 | 역할 |
|------|------|
| **step2_gemini_system.md** | Gemini **시스템** 역할: 리스크 감사관, Grok와 **동일 Base 시나리오** 전제로 **독립 CAGR** 예측, 장기 관점·구조적 리스크, 출력 JSON(`beta_cagr`, `risk_level`, `audit_notes`) 지시. |
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
| **step3_openai_system.md** | OpenAI **시스템** 역할: 수석 매니저, 자신의 Base CAGR 예측 → **세 Base 비교** → Bear/Bull 반영해 **최종 CAGR 확정**, 전 종목 포함·로드맵·복리 경고, 포맷·**출력 간결화** 지침. |
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
| **1** | Grok | 초안 작성 + CAGR(α) 예측 |
| **2** | Gemini | Step 1 초안 **감사** + CAGR(β) 예측 |
| **3** | Grok | Step 2 감사 내용에 대한 **수용 + 반박** (초안 재작성 없음) |
| **4** | Gemini | Step 3(Grok 2라운드) 내용에 대한 **수용 + 반박** (감사문 재작성 없음) |
| **5** | OpenAI | (자기) CAGR 예측 + Grok·Gemini α·β·협의 내용 반영해 **보고서 최종 완성** (세 Base 비교 → Bear/Bull 반영 → 최종 CAGR 확정) |

- Step 1·2: 숫자로는 **CAGR(α, β)** 확보, 텍스트로는 **초안·감사문** 생성.
- Step 3·4: **수용 목록 + 반박**만 출력, 재작성 없음.
- Step 5: 프롬프트의 **나머지 요청사항**(4가지 지출 시나리오, 연도별 자산 추이, 가족 부양 등)을 **최종 형태로** OpenAI가 채움.

---

## 요약 흐름

- **config.json** → 어떤 포트폴리오 파일·종목·보유 데이터 쓸지 결정.  
- **portfolio_prompt.txt** → “무엇을 목표로, 어떤 자산·규칙으로 보고서를 만들지”의 **단일 원천**.  
- **step1** → Grok가 **초안 + Base CAGR(alpha)** 생성.  
- **step2** → Gemini가 **초안 감사 + 독립 Base CAGR(beta)** 생성.  
- **step2b** → Grok·Gemini가 서로 **수용·반박만** 정리.  
- **step3** → OpenAI가 **세 Base 비교 + Bear/Bull 반영 + 최종 보고서** 작성.  
- **fallback_*.md** → 해당 step의 시스템 파일이 없을 때만 쓰는 **최소 역할·형식** 지시.
