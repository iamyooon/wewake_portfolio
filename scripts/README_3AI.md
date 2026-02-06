# 3-AI 협업 포트폴리오 보고서 생성 시스템

OpenAI, Grok, Gemini 세 개의 AI 서비스를 활용하여 더욱 정확하고 견고한 포트폴리오 보고서를 생성하는 시스템입니다.

## 🎯 개요

### 협업 워크플로우 (Version 3)

```
포트폴리오 데이터 + 환율·주가
    ↓
[Step 1] Grok: 초안 + Base 시나리오 CAGR (구간별 감쇠 제안 포함)
    ↓
[Step 2] Gemini: 감사 + Base CAGR (감쇠 검토·제안)
    ↓
[Step 2b] Grok / Gemini: 수용·반박 요약 (선택)
    ↓
[Step 3] OpenAI: 세 Base 비교 + Bear/Bull 반영 → 최종 보고서
    ↓
최종 보고서 (마크다운)
```

- 모든 AI 호출은 **temperature=0**으로 CAGR 변동을 완화합니다.

### AI 역할 분담

- **Grok**: 데이터 분석관 — 초안 작성, Base CAGR·구간별 감쇠 제안, 2라운드 수용·반박
- **Gemini**: 리스크 감사관 — 감사, Base CAGR·감쇠 검토·제안, 2라운드 수용·반박
- **OpenAI**: 수석 매니저 — 세 Base 비교, Bear/Bull 반영, 최종 CAGR·보고서 완성

## 📋 사전 요구사항

### 1. Python 환경
- Python 3.7 이상
- 필요한 패키지: `requests`

### 2. API 키 설정

`.env` 파일에 다음 API 키들을 설정해야 합니다:

```env
OPENAI_API_KEY=your-openai-api-key
GROK_API_KEY=your-grok-api-key
GEMINI_API_KEY=your-gemini-api-key
```

#### API 키 발급 방법

1. **OpenAI API 키**
   - https://platform.openai.com/api-keys
   - 계정 생성 후 API 키 발급

2. **Grok API 키 (xAI)**
   - https://console.x.ai/
   - 계정 생성 후 API 키 발급

3. **Gemini API 키 (Google)**
   - https://makersuite.google.com/app/apikey
   - Google 계정으로 로그인 후 API 키 발급

## 🚀 사용 방법

### 기본 사용

```bash
cd c:\Users\iamyo\wewake_portfolio
python scripts\generate_portfolio_report_3ai.py
```

### 옵션 지정

```bash
# 모델 지정
python scripts\generate_portfolio_report_3ai.py \
    --openai-model gpt-4-turbo \
    --grok-model grok-4 \
    --gemini-model gemini-2.5-pro

# 프롬프트 파일 지정
python scripts\generate_portfolio_report_3ai.py \
    --prompt-file portfolio_prompt.txt

# 출력 파일 지정
python scripts\generate_portfolio_report_3ai.py \
    --output-file my_report.md
```

### 사용 가능한 옵션

- `--openai-model`: OpenAI 모델 지정 (기본값: `gpt-4o`)
  - 예: `gpt-4o`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo`
  
- `--grok-model`: Grok 모델 지정 (기본값: `grok-4`)
  - 예: `grok-4`, `grok-4-1-fast-reasoning`, `grok-3`
  
- `--gemini-model`: Gemini 모델 지정 (기본값: `gemini-2.5-pro`)
  - 예: `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-3-pro-preview`
  
- `--prompt-file`: 프롬프트 파일 경로 (기본값: `portfolio_prompt.txt`)
  
- `--output-file`: 결과 파일 경로 (기본값: 자동 생성)

**유틸·테스트 옵션:**
- `--check-prices`: 환율·미국 주가만 조회 후 종료 (AI 미호출)
- `--test-data-fetch`: 환율·주가 API 테스트 후 종료
- `--test-models`: 각 AI에 짧은 요청 1회, 모델명 확인만
- `--test-cagr-only`: CAGR 예측만 1회 (Grok→Gemini→OpenAI), 보고서 미생성
- `--test-cagr-runs N`: CAGR 예측만 N회 연속 후 요약 표 출력 (변동 확인용)
- `--debug-step 1|2|3|4|5`: 해당 단계까지 실행 후 대화 모드 (Step 0: 디버그 시 맨 앞 환율·주가 출력)

## 📄 출력 파일 형식

생성된 보고서 파일은 다음 구조를 가집니다:

```markdown
# 위웨이크 주식회사 포트폴리오 보고서 (3-AI 협업)
**작성일: YYYY년 MM월 DD일 HH시 MM분**

**사용 모델:**
- OpenAI: `gpt-4o`
- Grok: `grok-4`
- Gemini: `gemini-2.5-pro`

---

## 최종 보고서

[최종 보고서 내용]

---

## 협업 과정 (참고용)

### 초안 (OpenAI 작성)
[초안 내용]

### 리뷰 코멘트 (Grok 작성)
[리뷰 코멘트]

### 데이터 검증 결과 (Gemini 작성)
[검증 결과]
```

## 🔍 각 AI의 역할 상세 (Version 3)

### Grok (데이터 분석관 · 1차)

**역할**: 
- 포트폴리오·실시간 데이터 기반 초안 작성, Base 시나리오 CAGR 예측
- 구간별 감쇠율 제안(근거 포함), 2라운드에서 Gemini 감사에 대한 수용·반박 정리

**강점**: 시장 모멘텀·기술적 분석, 비판적 검토

### Gemini (리스크 감사관 · 2차)

**역할**:
- Grok 초안·Base CAGR 검토, 거시·리스크 반영 감사
- Beta(Base) CAGR 제안, 구간별 감쇠 검토·제안, 2라운드에서 Grok R2에 대한 수용·반박 정리

**강점**: 수치·데이터 일관성 검증, 보수적 성장률 검토

### OpenAI (수석 매니저 · 최종)

**역할**:
- Grok·Gemini Base CAGR 및 2라운드 합의 요약 반영
- 세 Base 비교 후 Bear/Bull 반영해 최종 CAGR 확정, 보고서 완성(구조: 실행요약→현황→CAGR→시나리오→자산추이→추가분석→액션플랜)

**강점**: 구조화된 문서, 복잡한 정보 통합, 최종 의사결정

## ⚠️ 주의사항

### API 비용

- **OpenAI**: 토큰 사용량에 따라 과금 (약 $0.01-0.03 per report)
- **Grok**: 토큰 사용량에 따라 과금 (약 $0.01-0.02 per report)
- **Gemini**: 무료 티어 제공 (일일 제한 있음)

### 실행 시간

- 전체 프로세스: 약 3-5분
- 각 AI 호출: 약 30-60초
- 네트워크 상태에 따라 변동 가능

### 에러 처리

- API 호출 실패 시 자동으로 Fallback 모델 시도
- 일부 AI 실패 시에도 나머지 AI 결과로 보고서 생성
- 전체 실패 시 명확한 에러 메시지 제공

## 🐛 문제 해결

### API 키 오류

```
[ERROR] OPENAI_API_KEY가 설정되지 않았습니다.
```

**해결 방법**:
1. `.env` 파일이 프로젝트 루트에 있는지 확인
2. API 키가 올바르게 설정되었는지 확인
3. 파일 인코딩이 UTF-8인지 확인

### 모델 호출 실패

```
[ERROR] 모든 OpenAI 모델 시도 실패
```

**해결 방법**:
1. API 키가 유효한지 확인
2. 인터넷 연결 상태 확인
3. API 할당량 확인 (특히 Gemini 무료 티어)
4. 다른 모델로 시도 (`--openai-model gpt-4-turbo`)

### 타임아웃 오류

**해결 방법**:
1. 네트워크 연결 상태 확인
2. VPN 사용 중이면 해제 후 재시도
3. 더 빠른 모델 사용 (예: `gemini-2.5-flash`)

## 📊 성능 비교

| 항목 | 단일 AI | 2-AI 협업 | 3-AI 협업 |
|------|---------|-----------|-----------|
| 정확도 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 완성도 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 검증 강도 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 실행 시간 | 1-2분 | 2-3분 | 3-5분 |
| 비용 | 낮음 | 중간 | 높음 |

## 🔄 향후 개선 계획

- [ ] 로깅 시스템 추가
- [ ] 캐싱 기능으로 비용 절감
- [ ] 병렬 처리로 실행 시간 단축
- [ ] 웹 인터페이스 연동
- [ ] 배치 처리 기능

## 📝 참고 자료

- [PDR 문서](../PDR_Multi_AI_Portfolio_Report.md)
- [설계·동작 흐름](../docs/3AI_Report_Design.md), [본기능 동작 흐름](../docs/Main_Flow.md)
- [추가·변경 기능 이력](../docs/Changelog.md)
- [포트폴리오 프롬프트](../portfolio_prompt.txt)
- [보고서 생성 규칙](../.portfolio-rules)

---

**작성일**: 2026년 1월 26일  
**버전**: 1.1 (2026-02: Version 3 워크플로우, temperature=0, 감쇠 제안, CLI 옵션 반영)
