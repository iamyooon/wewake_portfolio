# AI 모델 선택 가이드

포트폴리오 보고서 생성에 사용할 AI 모델을 선택할 수 있습니다.

## 사용 가능한 모델

### 1. OpenAI GPT (현재 사용 중)
- **모델**: GPT-4o-mini
- **장점**: 빠른 응답, 안정적
- **단점**: 실수 가능성
- **비용**: 약 $0.015~0.03/보고서

### 2. Google Gemini (추천)
- **모델**: Gemini 1.5 Pro
- **장점**: 정확도 높음, 긴 컨텍스트 지원
- **단점**: 응답 시간 다소 길 수 있음
- **비용**: 무료 (일일 제한 있음)

### 3. Grok (xAI)
- **모델**: Grok-2
- **장점**: 실시간 정보 접근
- **단점**: API 접근 제한적
- **비용**: 유료

## 설정 방법

### Gemini 사용하기

1. **API 키 발급**
   - https://makersuite.google.com/app/apikey 방문
   - API 키 생성

2. **.env 파일에 추가**
   ```
   GEMINI_API_KEY=your-gemini-api-key-here
   ```

3. **패키지 설치**
   ```powershell
   pip install google-generativeai
   ```

4. **스크립트 실행**
   ```powershell
   python scripts\generate_portfolio_report_gemini.py
   ```

### Grok 사용하기

Grok API는 현재 공개되지 않았습니다. 공개되면 추가하겠습니다.

## 모델 비교

| 모델 | 정확도 | 속도 | 비용 | 추천도 |
|------|--------|------|------|--------|
| GPT-4o-mini | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $ | ⭐⭐⭐ |
| Gemini 1.5 Pro | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 무료 | ⭐⭐⭐⭐⭐ |
| Grok | ⭐⭐⭐⭐ | ⭐⭐⭐ | $ | ⭐⭐⭐⭐ |

## 추천

**Gemini 1.5 Pro**를 추천합니다:
- 정확도가 높아 실수 감소
- 무료 사용 가능
- 긴 컨텍스트 지원으로 상세한 보고서 생성 가능
