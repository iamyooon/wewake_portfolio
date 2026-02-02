# Grok API 설정 가이드

Grok API를 사용하여 Gemini와 협업하는 포트폴리오 보고서 생성 시스템입니다.

## Grok API 키 발급

1. **xAI 개발자 포털 접속**
   - https://console.x.ai/ 또는
   - https://x.ai/api (공식 문서 확인)

2. **API 키 생성**
   - 계정 생성 또는 로그인
   - API Keys 섹션에서 새 키 생성
   - 생성된 키 복사

3. **API 엔드포인트 확인**
   - 현재 사용: `https://api.x.ai/v1/chat/completions`
   - 모델: `grok-beta` 또는 최신 모델명 확인

## .env 파일 설정

```
GEMINI_API_KEY=your-gemini-api-key
GROK_API_KEY=your-grok-api-key
```

## 사용 방법

```powershell
cd C:\Users\iamyo\wewake_portfolio
python scripts\generate_portfolio_report_collaborative.py
```

## 협업 프로세스

1. **Gemini**: 프롬프트 기반으로 보고서 초안 작성
2. **Grok**: 초안을 리뷰하고 코멘트 제공
3. **Gemini**: 리뷰 코멘트를 반영/반박하며 최종 보고서 완성

## 출력 파일

- 파일명: `portfolio_report_YYYYMMDD_collaborative.md`
- 내용:
  - 최종 보고서
  - 초안 (참고용)
  - 리뷰 코멘트 (참고용)

## 참고사항

- Grok API가 아직 공개되지 않은 경우, 대체 리뷰 시스템 사용 가능
- API 엔드포인트나 모델명이 변경될 수 있으니 공식 문서 확인 필요
