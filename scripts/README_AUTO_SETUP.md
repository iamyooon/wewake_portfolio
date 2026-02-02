# 자동화 등록 완료 가이드

## ✅ 현재 상태

- ✅ Python 3.12 설치 완료
- ✅ openai 패키지 설치 완료  
- ✅ 스크립트 테스트 성공 (보고서 생성 확인)
- ⚠️ Windows Task Scheduler 등록 필요 (관리자 권한 필요)

## 🔧 자동화 등록 방법

### 방법 1: 관리자 권한 PowerShell 사용 (권장)

1. **시작 메뉴**에서 "PowerShell" 검색
2. **우클릭** → **"관리자 권한으로 실행"** 선택
3. 다음 명령 실행:

```powershell
cd C:\Users\iamyo\wewake_portfolio\scripts
.\register_task_admin.ps1
```

### 방법 2: 수동 등록

관리자 권한 PowerShell에서:

```powershell
$TaskName = "PortfolioDailyReport"
$ScriptPath = "C:\Users\iamyo\wewake_portfolio\scripts\generate_report_with_cursor.ps1"
$ProjectPath = "C:\Users\iamyo\wewake_portfolio"

$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`" -ProjectPath `"$ProjectPath`""

$trigger = New-ScheduledTaskTrigger -Daily -At "08:00"

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Generate portfolio report daily at 8:00 AM" `
    -RunLevel Highest
```

## ✅ 등록 확인

등록 후 다음 명령으로 확인:

```powershell
Get-ScheduledTask -TaskName PortfolioDailyReport
```

## 🧪 수동 테스트

등록 전에 수동으로 실행해보기:

```powershell
cd C:\Users\iamyo\wewake_portfolio\scripts
.\generate_report_with_cursor.ps1
```

## 📋 작업 관리 명령어

### 작업 확인
```powershell
Get-ScheduledTask -TaskName PortfolioDailyReport
```

### 수동 실행
```powershell
Start-ScheduledTask -TaskName PortfolioDailyReport
```

### 작업 삭제
```powershell
Unregister-ScheduledTask -TaskName PortfolioDailyReport -Confirm:$false
```

### 실행 기록 확인
1. Windows 키 + R → `taskschd.msc` 입력
2. "작업 스케줄러 라이브러리" → "PortfolioDailyReport" 찾기
3. "실행 기록" 탭에서 로그 확인

## 📝 참고사항

- **실행 시간**: 매일 오전 8시
- **보고서 위치**: `C:\Users\iamyo\wewake_portfolio\portfolio_report_YYYYMMDD_auto.md`
- **로그**: 작업 스케줄러에서 확인 가능
- **에러 발생 시**: 작업 스케줄러의 실행 기록에서 오류 메시지 확인
