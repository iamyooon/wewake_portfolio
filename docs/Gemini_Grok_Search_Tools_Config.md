# Gemini / Grok 검색 도구 설정 (Google Search Grounding, Web Search)

## 개요

- **OpenAI**: 우리 스크립트는 텍스트만 보내므로 web_search를 수행하지 않음. (도구 미지원 또는 별도 설정 필요)
- **Gemini**: API 요청에 `tools: [{"google_search": {}}]` 를 넣으면 **Google Search Grounding** 이 활성화되어 실시간 웹 검색 결과를 반영한 답변을 받을 수 있음.
- **Grok (xAI)**: **Responses API** (`/v1/responses`) 에 `tools` 에 `web_search` 를 넣으면 서버가 웹 검색을 수행한 뒤 결과를 반영한 답변을 반환함.

이 문서는 위 내용을 정리하고, 스크립트에서의 적용 방법을 설명합니다.

---

## 1. Gemini – Google Search Grounding

### 설정 방법

요청 body에 **`tools`** 를 추가합니다.

**REST 예시**
```json
"tools": [{"google_search": {}}]
```

**동작**
- 모델이 필요하다고 판단하면 검색 쿼리를 생성하고 Google Search를 실행한 뒤, 그 결과를 반영해 답변합니다.
- 응답에 `groundingMetadata` (검색 쿼리, 출처, 인용 정보)가 포함될 수 있습니다.

### 지원 모델

- Gemini 2.5 Pro / 2.5 Flash / 2.5 Flash-Lite  
- Gemini 2.0 Flash  
- Gemini 1.5 Pro / 1.5 Flash  

(문서 기준. 실험/프리뷰 모델은 공식 모델 개요 참고.)

### 과금

- **Gemini 2.5 등 (기존 모델)**: 프롬프트 단위 과금.
- **Gemini 3**: 2026년 1월 5일부터 Grounding with Google Search는 **검색 쿼리 실행 횟수별** 과금.

### 참고

- [Grounding with Google Search (Gemini API)](https://ai.google.dev/gemini-api/docs/grounding)

---

## 2. Grok (xAI) – Search Tools (web_search)

### 설정 방법

- **Responses API** (`POST https://api.x.ai/v1/responses`) 를 사용합니다.
- 요청에 **`tools`** 파라미터를 넣고, 그 안에 **`web_search`** 를 포함합니다.
- 기존 **Chat Completions** (`/v1/chat/completions`) 는 검색 도구를 지원하지 않습니다.

**도구 종류**
- **web_search**: 웹 검색 및 페이지 브라우징.
- **x_search**: X(트위터) 게시물/유저/키워드 검색 (선택).

**동작**
- 서버가 검색·추가 쿼리·페이지 확인을 수행한 뒤, 그 결과를 반영한 최종 답변을 반환합니다.
- `response.citations` 로 출처 URL 목록, 옵션으로 `inline_citations` 로 본문 인용을 받을 수 있습니다.

### 모델

- 검색(에이전트) 용도로는 **grok-4-1-fast** 등 도구 호출을 지원하는 모델 사용이 권장됩니다.
- 지원 모델: grok-4, grok-4-fast, grok-4-1-fast 등 (xAI 문서의 Tools 호환 모델 참고).

### 주의사항

- 예전 방식인 **Live Search API** / `search_parameters` 는 **2026년 1월 12일** 부로 410 Gone 예정 → **도구 기반 `tools`** 방식으로 이전 필요.
- xAI Python SDK 사용 시 **1.3.1 이상** 필요.

### 참고

- [Search Tools (xAI)](https://docs.x.ai/docs/guides/live-search)
- [Tools Overview (xAI)](https://docs.x.ai/docs/guides/tools/overview)
- [Responses API (xAI)](https://docs.x.ai/docs/guides/chat)

---

## 3. 스크립트에서의 적용

### Gemini

- `generate_portfolio_report_3ai.py` 의 **Gemini 호출** (`call_gemini_api`) 에서  
  `generateContent` 요청 body에  
  `"tools": [{"google_search": {}}]`  
  를 추가하여 Google Search Grounding을 켭니다.
- 모든 Gemini 호출(검증 단계 등)에 적용됩니다.

### Grok

- **기본 동작**: Grok 호출 시 먼저 **Responses API** (`/v1/responses`) + `tools: [{"type": "web_search"}]` 로 시도합니다. 실패 시 기존 **Chat Completions** (`/v1/chat/completions`) 로 폴백합니다.
- **web_search 끄기**: `--no-grok-web-search` 옵션을 주면 처음부터 Chat Completions만 사용합니다. (Responses API·도구 미지원 환경에서 사용.)

### OpenAI

- 현재 스크립트는 텍스트만 전송하며, web_search 등 도구를 붙이지 않습니다.
- 실시간 환율/종가는 **스크립트에서 API로 조회한 뒤 프롬프트에 주입**하는 방식으로 보완합니다. (관련: `docs/web_search_Data_Constraints.md`)

---

## 4. 요약 표

| 대상    | 검색 사용 방법                    | API/엔드포인트        | 비고 |
|--------|-----------------------------------|----------------------|------|
| Gemini | `tools: [{"google_search": {}}]`  | generateContent      | Grounding 지원 모델만 |
| Grok   | `tools` 에 `web_search` 포함      | /v1/responses        | Chat Completions는 검색 미지원 |
| OpenAI | 도구 미사용 (텍스트만)             | chat/completions 등  | 실시간 데이터는 앱에서 조회 후 주입 |
