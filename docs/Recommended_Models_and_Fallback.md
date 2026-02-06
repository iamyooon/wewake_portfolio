# AI 서비스별 권장 모델 및 설정값

## 📋 권장 모델 (리스크 관리 중심)

| 단계 | 서비스 (Service) | 권장 모델명 (API ID) | 선정 사유 |
| --- | --- | --- | --- |
| **Step 1** | **Grok (xAI)** | **`grok-4-1-fast-reasoning`** | **실시간성 최강.** X(트위터) 및 실시간 뉴스 검색으로 1차 Alpha 성장률·시장 센티먼트를 뽑아내기에 가장 빠르고 정확함. 금융 데이터 구조화(테이블화) 능력 우수. |
| **Step 2** | **Gemini (Google)** | **`gemini-3-flash-preview`** | **팩트 체크 최적화.** 구글 서치 그라운딩(Search Grounding) 속도가 빠르며, 거시 경제 리스크 기반 Beta 성장률을 보수적으로 산출하는 '방어' 역할에 적합. |
| **Step 3** | **OpenAI** | **`gpt-5.2`** | **최종 의사결정.** 5.2 Pro 대비 비용이 저렴하면서도 Thinking/Reasoning을 지원해 복리 페널티 등 복잡한 논리 계산과 위웨이크 철학 반영에 적합. |

---

## 🛠️ 모델별 세부 설정 (스크립트 반영)

### 1. Grok (초안 작성기)

- **API 호출:** `temperature: 0.2` (수치 정확도를 위해 낮게 설정)
- **특이사항:** Grok 4.2 지연 시 **4.1 Fast-Reasoning** 유지. 금융 데이터 구조화 능력 우수.

### 2. Gemini (리스크 감사관)

- **API 호출:** `tools: [{"google_search": {}}]` (Google Search Grounding 활성화)
- **특이사항:** 하루 1건 생성 시 **3 Flash**가 속도 면에서 유리하며 리스크 비판 임무에 충분.

### 3. OpenAI (수석 매니저)

- **API 호출:** `reasoning: {"effort": "medium"}` (Responses API 사용 시, 지원 모델 한정)
- **특이사항:** **GPT-5.2** 시리즈 권장. 이전 모델(4o 등) 퇴역 예정에 따라 최신 버전 고정이 안정적.

---

## ⚠️ 백업(Fallback) 모델 전략

자산 관리 리포트는 단 하루도 끊기면 안 되므로, 메인 모델 장애 시 **비상용 모델**을 등록해 두는 것을 권장합니다.

| 상황 | 비상용 모델 | 비고 |
|------|-------------|------|
| **OpenAI 장애 시** | `claude-4.5-sonnet` (Anthropic) | 논리적 무결성·안전성 강점. 별도 API 키 및 연동 코드 필요. |
| **Gemini / Grok 장애 시** | `gemini-3-pro-preview` | 강한 추론으로 검색·검증 동시 수행 가능. 스크립트 내 폴백 목록에 포함됨. |

**폴백 원칙:** 기본 모델보다 **비싼 모델은 폴백 후보에 넣지 않음.** OpenAI는 5.2-pro 제외(4o·4·3.5만). Gemini는 2.5-pro·3-pro 계열 제외(3-flash·2.5-flash·gemini-pro만). Grok은 4·4-0709 제외(4.1-fast·4-fast·3·3-mini만).

### 스크립트 내 자동 폴백

- **OpenAI:** `gpt-5.2` 실패 시 **기본보다 비싼 모델은 폴백에 넣지 않음.** 시도 순서: `gpt-5.2-2025-12-11` → `gpt-4o` → `gpt-4-turbo` → `gpt-4` → `gpt-3.5-turbo` (gpt-5.2-pro 미포함).
- **Gemini:** `gemini-3-flash-preview` 실패 시 → `gemini-3-flash` → `gemini-2.5-pro` → `gemini-3-pro-preview` → … 순으로 시도.
- **Grok:** `grok-4-1-fast-reasoning` 실패 시 → 동일 Responses API 내 다른 4.1/4 계열 모델 순으로 시도.

Claude 연동이 필요하면 별도 스크립트 또는 `generate_portfolio_report_3ai.py`에 Anthropic API 호출 분기를 추가해야 합니다.
