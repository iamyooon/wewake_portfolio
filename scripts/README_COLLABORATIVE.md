# 포트폴리오 보고서 협업 생성 시스템

Gemini와 Grok이 협업하여 더욱 정확하고 완성도 높은 포트폴리오 보고서를 생성하는 시스템입니다.

## 작동 방식

1. **Gemini (초안 작성)**
   - `portfolio_prompt.txt` 기반으로 보고서 초안 작성
   - 모든 필수 섹션 포함

2. **Grok (리뷰 및 코멘트)**
   - 초안의 정확성, 완성도, 논리성 검토
   - 구체적인 개선 사항 제안

3. **Gemini (최종 완성)**
   - Grok의 코멘트를 검토
   - 타당한 지적은 반영, 부적절한 제안은 반박
   - 최종 보고서 완성

## 설정 방법

### 1. API 키 발급

#### Gemini API 키
- https://makersuite.google.com/app/apikey
- 또는 https://aistudio.google.com/app/apikey

#### Grok API 키
- https://console.x.ai/ 또는 https://x.ai/api
- xAI 개발자 포털에서 API 키 생성
- 모델: `grok-beta` (최신 모델명 확인 필요)

### 2. .env 파일 설정

```
GEMINI_API_KEY=your-gemini-api-key
GROK_API_KEY=your-grok-api-key
```

### 3. 필요한 Python 패키지 설치

```powershell
pip install requests
```

## 사용 방법

### 수동 실행

```powershell
cd C:\Users\iamyo\wewake_portfolio
python scripts\generate_portfolio_report_collaborative.py
```

### 자동 실행 (매일 아침 8시)

PowerShell 스크립트가 자동으로 협업 모드를 감지합니다:
- `.env` 파일에 `GEMINI_API_KEY`와 `GROK_API_KEY`가 모두 있으면 → 협업 모드
- 하나만 있으면 → 해당 모델만 사용

## 출력 파일

- 파일명: `portfolio_report_YYYYMMDD_collaborative.md`
- 내용:
  - **최종 보고서**: Gemini가 Grok의 리뷰를 반영하여 완성한 보고서
  - **초안**: Gemini가 처음 작성한 보고서 (참고용)
  - **리뷰 코멘트**: Grok이 제공한 리뷰 및 개선 제안 (참고용)

## 협업 프로세스 예시

```
[1] Gemini: "포트폴리오 보고서 초안 작성 완료"
    → 초안: 5,000자 보고서 생성

[2] Grok: "초안 검토 완료"
    → 리뷰: 
      - 강점: 자산 현황표가 상세함
      - 개선: CAGR 계산 근거를 더 구체적으로 설명 필요
      - 추가: 리스크 요인 분석 강화 제안

[3] Gemini: "리뷰 반영하여 최종 보고서 완성"
    → 최종: Grok의 제안을 반영하여 6,000자 보고서 완성
    → 반박: "CAGR 계산은 현재 포트폴리오 구성 기반으로 산출했으며, 
             추가 설명은 불필요하다고 판단합니다."
```

## 장점

1. **정확성 향상**: 두 AI가 서로 검토하여 오류 감소
2. **완성도 향상**: 리뷰를 통해 누락된 섹션 보완
3. **논리성 강화**: 분석과 결론의 연결성 검증
4. **투명성**: 초안과 리뷰 과정이 모두 기록되어 추적 가능

## 문제 해결

### Grok API 오류
- API 엔드포인트나 모델명이 변경되었을 수 있습니다
- `scripts/generate_portfolio_report_collaborative.py`의 `call_grok_api` 함수 확인
- xAI 공식 문서에서 최신 API 정보 확인

### Gemini 할당량 초과
- 자동으로 `gemini-2.5-pro` → `gemini-2.5-flash`로 폴백
- Gemini API 할당량 확인 필요

### 협업 모드가 자동으로 선택되지 않음
- `.env` 파일에 두 API 키가 모두 있는지 확인
- PowerShell 스크립트의 모델 선택 로직 확인
