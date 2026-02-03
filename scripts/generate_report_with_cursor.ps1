# 포트폴리오 보고서 자동 생성 PowerShell 스크립트
# 매일 아침 8시에 실행되도록 Windows Task Scheduler에 등록
# 3-AI(Grok + Gemini + OpenAI) 스크립트만 실행
# 콘솔에는 영어만 출력 (한글 깨짐 방지). 상세 한글 로그는 report\daily_*.log (UTF-8) 참고.

param(
    [string]$ProjectPath = "C:\Users\iamyo\wewake_portfolio"
)

$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

# 프로젝트 디렉토리로 이동
Set-Location $ProjectPath

# .env 파일에서 환경 변수 로드
$envFile = Join-Path $ProjectPath ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Portfolio Report Auto-Generation (3-AI)" -ForegroundColor Cyan
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 3-AI 스크립트만 실행 (Grok + Gemini + OpenAI, 2라운드 협상 후 GPT 최종)
$pythonScript = Join-Path $ProjectPath "scripts\generate_portfolio_report_3ai.py"
Write-Host "Script: generate_portfolio_report_3ai.py (3-AI)" -ForegroundColor Cyan

if (Test-Path $pythonScript) {
    Write-Host "`nRunning Python script..." -ForegroundColor Yellow
    
    # Python 경로 확인 (여러 방법 시도)
    $python = $null
    
    # 방법 1: PATH에서 찾기
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        $python = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $python) {
        $python = Get-Command py -ErrorAction SilentlyContinue
    }
    
    # 방법 2: 일반적인 설치 위치에서 찾기
    if (-not $python) {
        $commonPaths = @(
            "$env:LOCALAPPDATA\Programs\Python\Python*",
            "$env:ProgramFiles\Python*",
            "$env:ProgramFiles(x86)\Python*",
            "C:\Python*"
        )
        
        foreach ($pathPattern in $commonPaths) {
            $pythonDirs = Get-ChildItem $pathPattern -Directory -ErrorAction SilentlyContinue
            foreach ($dir in $pythonDirs) {
                $pythonExe = Join-Path $dir.FullName "python.exe"
                if (Test-Path $pythonExe) {
                    $python = @{Source = $pythonExe}
                    Write-Host "Python found: $pythonExe" -ForegroundColor Green
                    break
                }
            }
            if ($python) { break }
        }
    }
    
    if ($python) {
        Write-Host "Python: $($python.Source)" -ForegroundColor Green
        # Save full output to UTF-8 log file (Korean OK). Do not echo to console to avoid garbled text.
        $logDir = Join-Path $ProjectPath "report"
        if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
        $logFile = Join-Path $logDir ("daily_$(Get-Date -Format 'yyyyMMdd_HHmmss').log")
        $scriptOutput = & $python.Source $pythonScript 2>&1
        $scriptOutput | Out-File -FilePath $logFile -Encoding utf8
        Write-Host "Output saved to log (UTF-8): $logFile" -ForegroundColor Gray
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            Write-Host "`nFailed (exit code: $exitCode). See log for details." -ForegroundColor Red
            exit $exitCode
        }

        # Post final report to Jira (WWI-59 by default)
        $jiraReportIssue = if ($env:JIRA_REPORT_ISSUE_KEY) { $env:JIRA_REPORT_ISSUE_KEY } else { "WWI-59" }
        $reportDir = Join-Path $ProjectPath "report"
        $latestReport = Get-ChildItem (Join-Path $reportDir "portfolio_report_*.md") -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latestReport) {
            $relativeReportPath = "report\" + $latestReport.Name
            $jiraScript = Join-Path $ProjectPath "scripts\git\jira.mjs"
            if (Test-Path $jiraScript) {
                try {
                    & node $jiraScript summary --file $relativeReportPath --issue $jiraReportIssue 2>&1 | Out-Null
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "Jira comment posted: $jiraReportIssue" -ForegroundColor Gray
                    } else {
                        Write-Host "Jira post skipped (check JIRA_* in .env)." -ForegroundColor Gray
                    }
                } catch {
                    Write-Host "Jira post skipped: $($_.Exception.Message)" -ForegroundColor Gray
                }
            }
        }
    } else {
        Write-Host "Error: Python not found." -ForegroundColor Red
        Write-Host "Install from https://www.python.org/downloads/ (check Add to PATH)." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "Error: Script not found: $pythonScript" -ForegroundColor Red
    exit 1
}

Write-Host "`nDone." -ForegroundColor Green
