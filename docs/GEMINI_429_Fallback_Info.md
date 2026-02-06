# Gemini만 폴백되는 경우 – URL·호출 방식·에러 전문

## 1. 폴백 여부

**예. 지금은 Gemini만 폴백됩니다.**

- **OpenAI**: 요청 모델(gpt-5.2-pro) = 실제 사용 → 동일
- **Grok**: 요청 모델(grok-4-1-fast-reasoning) = 실제 사용 → 동일
- **Gemini**: 요청 모델(gemini-3-pro-preview) → 429 발생 → **gemini-2.5-flash**로 폴백

---

## 2. Gemini 호출에 사용한 URL (키 제외)

**도메인+경로만 (API 키는 쿼리 `?key=...` 에 붙어 있음, 아래에는 미포함):**

```
https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent
```

**요청했던 모델별 URL 예:**

- gemini-3-pro-preview  
  `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-preview:generateContent`
- gemini-2.5-pro  
  `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent`
- gemini-2.5-flash (폴백 성공 시)  
  `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`

실제 요청 시에는 위 URL 뒤에 `?key=YOUR_API_KEY` 가 붙습니다.

---

## 3. 호출 방식 (SDK/언어)

- **언어**: Python 3
- **HTTP 클라이언트**: `requests` (표준 라이브러리 아님, pip 패키지)
- **SDK**: **Google 공식 Gemini SDK 미사용**  
  → `requests.post(url, headers=..., json=...)` 로 REST API 직접 호출

---

## 4. 429 에러 시 응답 본문 전문 (JSON)

아래는 **gemini-3-pro-preview** 로 호출했을 때 429가 났을 때의 응답 본문 예시입니다. (실제 실행에서 캡처한 내용과 동일한 형식.)

```json
{
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 0, model: gemini-3-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 0, model: gemini-3-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_input_token_count, limit: 0, model: gemini-3-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_input_token_count, limit: 0, model: gemini-3-pro\nPlease retry in 7.811233656s.",
    "status": "RESOURCE_EXHAUSTED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.Help",
        "links": [
          {
            "description": "Learn more about Gemini API quotas",
            "url": "https://ai.google.dev/gemini-api/docs/rate-limits"
          }
        ]
      },
      {
        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
        "violations": [
          {
            "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
            "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
            "quotaDimensions": {
              "location": "global",
              "model": "gemini-3-pro"
            }
          },
          {
            "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
            "quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier",
            "quotaDimensions": {
              "location": "global",
              "model": "gemini-3-pro"
            }
          },
          {
            "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_input_token_count",
            "quotaId": "GenerateContentInputTokensPerModelPerMinute-FreeTier",
            "quotaDimensions": {
              "location": "global",
              "model": "gemini-3-pro"
            }
          },
          {
            "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_input_token_count",
            "quotaId": "GenerateContentInputTokensPerModelPerDay-FreeTier",
            "quotaDimensions": {
              "location": "global",
              "model": "gemini-3-pro"
            }
          }
        ]
      },
      {
        "@type": "type.googleapis.com/google.rpc.RetryInfo",
        "retryDelay": "7s"
      }
    ]
  }
}
```

**요약:**

- **code**: 429  
- **status**: `RESOURCE_EXHAUSTED`  
- **원인**: Free Tier 한도 초과  
  - `generate_content_free_tier_requests` (일/분당 요청 수)  
  - `generate_content_free_tier_input_token_count` (일/분당 입력 토큰)  
  - `limit: 0` 은 해당 Free Tier에서 **gemini-3-pro** (및 gemini-2.5-pro) 에 대한 할당이 0이라는 의미로 해석 가능  
- **retryDelay**: 예) `"7s"` → 표시된 시간 이후 재시도 권장

---

429 발생 시 스크립트는 위와 동일한 URL·Python/requests 호출로 요청하며, 콘솔에 위와 같은 에러 전문이 출력되고, 마지막 429 응답은 `wewake_portfolio/gemini_last_error.txt` 에도 저장됩니다.
