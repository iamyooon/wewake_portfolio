# 포트폴리오 보고서 자동 생성 가이드

매일 아침 8시에 `portfolio_prompt.txt` 기반으로 포트폴리오 보고서를 자동으로 생성하는 시스템입니다.

## 설정 방법

### 1. Windows Task Scheduler 등록

관리자 권한으로 PowerShell을 실행하고 다음 명령을 실행하세요:

```powershell
cd C:\Users\iamyo\wewake_portfolio\scripts
.\setup_daily_report.ps1
```

또는 수동으로 등록하려면:

```powershell
# 작업 액션 생성
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File `"C:\Users\iamyo\wewake_portfolio\scripts\generate_report_with_cursor.ps1`""

# 트리거 생성 (매일 아침 8시)
$trigger = New-ScheduledTaskTrigger -Daily -At "08:00"

# 작업 등록
Register-ScheduledTask -TaskName "PortfolioDailyReport" `
    -Action $action `
    -Trigger $trigger `
    -Description "매일 아침 8시에 포트폴리오 보고서를 자동으로 생성합니다."
```

### 2. 작업 확인

```powershell
Get-ScheduledTask -TaskName PortfolioDailyReport
```

### 3. 수동 실행

```powershell
Start-ScheduledTask -TaskName PortfolioDailyReport
```

### 4. 작업 삭제

```powershell
Unregister-ScheduledTask -TaskName PortfolioDailyReport -Confirm:$false
```

## 작동 방식

1. **매일 아침 8시**에 Windows Task Scheduler가 스크립트를 실행합니다.
2. 스크립트는 `portfolio_prompt.txt` 파일을 읽습니다.
3. 현재 날짜 기준으로 보고서 파일명을 생성합니다 (`portfolio_report_YYYYMMDD_auto.md`).
4. 보고서 생성 프롬프트를 준비합니다.

## 주의사항

⚠️ **현재 버전은 보고서 생성 프롬프트를 준비하는 단계까지 수행합니다.**

실제 보고서 생성은 다음 중 하나의 방법으로 수행해야 합니다:

### 방법 1: Cursor AI 사용 (권장)
- Cursor에서 생성된 프롬프트 파일을 사용하여 보고서를 생성합니다.
- 프롬프트 파일: `report_prompt_YYYYMMDD.txt`

### 방법 2: OpenAI API 통합 (향후 구현)
- Python 스크립트에 OpenAI API 호출 기능을 추가하여 완전 자동화할 수 있습니다.
- 이 경우 `.env` 파일에 `OPENAI_API_KEY`를 설정해야 합니다.

## 파일 구조

```
scripts/
├── generate_portfolio_report.py      # Python 보고서 생성 스크립트
├── generate_report_with_cursor.ps1   # PowerShell 래퍼 스크립트
├── setup_daily_report.ps1            # Task Scheduler 등록 스크립트
└── README_REPORT_AUTO.md             # 이 파일
```

## 문제 해결

### Python을 찾을 수 없는 경우

Python이 설치되어 있고 PATH에 등록되어 있는지 확인하세요:

```powershell
python --version
# 또는
python3 --version
```

### 권한 오류

관리자 권한으로 PowerShell을 실행하세요:

1. 시작 메뉴에서 "PowerShell" 검색
2. "관리자 권한으로 실행" 선택

### 작업이 실행되지 않는 경우

작업 상태 확인:

```powershell
Get-ScheduledTask -TaskName PortfolioDailyReport | Format-List
```

작업 실행 기록 확인:

```powershell
Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational | 
    Where-Object {$_.Message -like "*PortfolioDailyReport*"} | 
    Select-Object -First 10
```

## 향후 개선 사항

- [ ] OpenAI API 통합으로 완전 자동화
- [ ] 보고서 생성 후 자동으로 Git 커밋 및 푸시
- [ ] 이메일 알림 기능 추가
- [ ] 보고서 생성 실패 시 재시도 로직
- [ ] 보고서 템플릿 커스터마이징 옵션
