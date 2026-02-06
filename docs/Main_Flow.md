# 3-AI 포트폴리오 보고서 본기능 동작 흐름

## 왜 몇 분 걸리나?

**AI API를 순서대로 최대 5번** 호출하기 때문입니다. 각 호출이 30초~2분 정도 걸리고, **전부 동기(순차)** 로 실행됩니다. (Version 3: Grok → Gemini → [2라운드 Grok·Gemini] → OpenAI)

---

## 단계별 흐름 (현재 구현: Version 3)

```
[0] (선택) Debug Step 0    환율·미국 주가 확인만 출력              → 즉시
[1/5] Grok R1              포트폴리오+데이터 → 초안 + Base CAGR     → 1~2분
[2/5] Gemini R1            Grok 초안+CAGR → 감사 + Base CAGR       → 30초~1분
[2b]  Grok R2 / Gemini R2  수용·반박만 정리 (각 1회, 선택)         → 각 30초~1분
[3/5] OpenAI               세 Base 비교 + Bear/Bull → 최종 보고서   → 1~2분

      → 마크다운 파일 저장 + 모델 사용 현황 출력
```

- **환경:** [1] 환경 변수 로드(.env), [2] 프롬프트·설정 읽기(`portfolio_prompt.txt`, `config.json`) 후 Step 1부터 진행.
- **2라운드(Step 2b):** 실패 시 해당 R2만 생략하고 Step 3 진행.

---

## 각 단계가 하는 일

| 단계 | AI | 입력 | 출력 | 대략 소요 |
|------|-----|------|------|------------|
| **0** | (없음) | — | 환율·미국 주가(정규/애프터) 출력 | 즉시 |
| **1** | **Grok** | 포트폴리오, 환율·주가, 날짜 | 초안 + Base CAGR(JSON) | 1~2분 |
| **2** | **Gemini** | Grok 초안, Grok Base CAGR, 포트폴리오 요약 | 감사문 + Base CAGR(JSON) | 30초~1분 |
| **2b** | **Grok / Gemini** | 상대방 R1 또는 R2 출력 | 수용·반박 요약(전문 아님) | 각 30초~1분 |
| **3** | **OpenAI** | Grok·Gemini Base, 초안·감사·R2, 포트폴리오 | 최종 보고서(마크다운) | 1~2분 |

- **1, 3**이 가장 무겁습니다. 긴 프롬프트 + 긴 생성이라 1~2분씩 걸립니다.
- 모든 AI 호출은 **temperature=0**으로 CAGR 변동을 완화합니다.

---

## CLI 옵션 요약

| 옵션 | 동작 |
|------|------|
| (없음) | 본기능 전체 실행 (Grok → Gemini → [2b] → OpenAI) |
| `--debug-step 1\|2\|3\|4\|5` | 해당 단계까지 실행 후 대화 모드. **Step 0**은 디버그 시 맨 앞에 환율·주가 출력 |
| `--check-prices` | 환율·미국 주가만 조회 후 종료 (AI 미호출) |
| `--test-data-fetch` | 환율·주가 API 테스트 후 종료 |
| `--test-models` | 각 AI에 짧은 요청 1회, 모델명 확인만 |
| `--test-cagr-only` | CAGR 예측만 1회 (Grok→Gemini→OpenAI), 보고서 미생성 |
| `--test-cagr-runs N` | CAGR 예측만 N회 연속 후 요약 표 출력 (변동 확인용) |

---

## 요약

- **본기능 = AI 호출 최대 5번** (Grok R1, Gemini R1, Grok R2, Gemini R2, OpenAI)을 **한 번에 순서대로** 실행합니다.
- **테스트:** `--test-models`(모델 확인), `--test-cagr-only`(CAGR 1회), `--test-cagr-runs N`(CAGR N회), `--check-prices`(환율·주가만).
- 본기능은 **초안 → 감사 → 2라운드 합의 → 최종 보고서**까지 만들어 **총 3~5분** 정도 걸리는 구조입니다.
- 상세 설계·변경 이력: `docs/3AI_Report_Design.md`, `docs/Changelog.md`
