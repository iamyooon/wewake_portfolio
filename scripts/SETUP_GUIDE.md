# 포트폴리오 보고서 완전 자동화 설정 가이드

## ✅ 완료된 작업

1. ✅ OpenAI API 키 설정 (`.env` 파일에 저장됨)
2. ✅ 완전 자동화 스크립트 생성 (`generate_portfolio_report_openai.py`)
3. ✅ Windows Task Scheduler 등록 스크립트 준비

## 📋 설정 단계

### 1단계: Python 패키지 설치

PowerShell을 열고 다음 명령을 실행하세요:

```powershell
cd C:\Users\iamyo\wewake_portfolio
python -m pip install openai
```

또는 Python3가 설치되어 있다면:

```powershell
python3 -m pip install openai
```

### 2단계: 스크립트 테스트

수동으로 한 번 실행해서 정상 작동하는지 확인:

```powershell
cd C:\Users\iamyo\wewake_portfolio
python scripts\generate_portfolio_report_openai.py
```

정상 작동하면 `portfolio_report_YYYYMMDD_auto.md` 파일이 생성됩니다.

### 3단계: Windows Task Scheduler 등록

관리자 권한으로 PowerShell을 실행하고:

```powershell
cd C:\Users\iamyo\wewake_portfolio\scripts
.\setup_daily_report.ps1
```

이제 매일 아침 8시에 자동으로 보고서가 생성됩니다!

## 🔍 확인 방법

### 작업이 등록되었는지 확인

```powershell
Get-ScheduledTask -TaskName PortfolioDailyReport
```

### 수동 실행 (테스트)

```powershell
Start-ScheduledTask -TaskName PortfolioDailyReport
```

### 실행 로그 확인

작업 스케줄러에서 확인:
1. Windows 키 + R → `taskschd.msc` 입력
2. "작업 스케줄러 라이브러리" → "PortfolioDailyReport" 찾기
3. "실행 기록" 탭에서 로그 확인

## ⚙️ 설정 파일 위치

- **API 키**: `C:\Users\iamyo\wewake_portfolio\.env`
- **포트폴리오 프롬프트**: `C:\Users\iamyo\wewake_portfolio\portfolio_prompt.txt`
- **생성된 보고서**: `C:\Users\iamyo\wewake_portfolio\portfolio_report_YYYYMMDD_auto.md`

## 💰 비용 정보

- **모델**: GPT-4o-mini (비용 효율적)
- **예상 토큰**: 약 5,000~10,000 tokens/보고서
- **예상 비용**: 약 $0.015~0.03/보고서
- **월 예상 비용**: 약 $0.45~0.90 (30일 기준)

## 🛠️ 문제 해결

### Python을 찾을 수 없는 경우

1. Python 설치 확인:
   ```powershell
   python --version
   ```

2. Python이 없다면 설치:
   - https://www.python.org/downloads/ 에서 다운로드
   - 설치 시 "Add Python to PATH" 체크

### OpenAI API 오류

1. API 키 확인:
   ```powershell
   type C:\Users\iamyo\wewake_portfolio\.env
   ```

2. API 키가 올바른지 확인:
   - https://platform.openai.com/api-keys 에서 확인

### 보고서가 생성되지 않는 경우

1. 스크립트를 수동 실행하여 오류 메시지 확인
2. `.env` 파일이 올바른 위치에 있는지 확인
3. `portfolio_prompt.txt` 파일이 존재하는지 확인

## 📝 참고사항

- 보고서는 매일 아침 8시에 자동 생성됩니다
- 같은 날짜의 보고서가 이미 있으면 덮어씁니다
- API 비용은 OpenAI 계정에서 확인할 수 있습니다
- `.env` 파일은 Git에 커밋되지 않습니다 (보안)
