# 포트폴리오 보고서 자동 생성 PowerShell 스크립트
# 매일 아침 8시에 실행되도록 Windows Task Scheduler에 등록
# 3-AI(Grok + Gemini + OpenAI) 스크립트만 실행

param(
    [string]$ProjectPath = "C:\Users\iamyo\wewake_portfolio"
)

$ErrorActionPreference = "Stop"

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
Write-Host "포트폴리오 보고서 자동 생성 (3-AI)" -ForegroundColor Cyan
Write-Host "실행 시간: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 3-AI 스크립트만 실행 (Grok + Gemini + OpenAI, 2라운드 협상 후 GPT 최종)
$pythonScript = Join-Path $ProjectPath "scripts\generate_portfolio_report_3ai.py"
Write-Host "사용 스크립트: generate_portfolio_report_3ai.py (3-AI)" -ForegroundColor Cyan

if (Test-Path $pythonScript) {
    Write-Host "`nPython 스크립트 실행 중..." -ForegroundColor Yellow
    
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
                    Write-Host "Python 발견: $pythonExe" -ForegroundColor Green
                    break
                }
            }
            if ($python) { break }
        }
    }
    
    if ($python) {
        Write-Host "Python 실행: $($python.Source)" -ForegroundColor Green
        & $python.Source $pythonScript
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) {
            Write-Host "`n❌ 스크립트 실행 실패 (종료 코드: $exitCode)" -ForegroundColor Red
            exit $exitCode
        }
    } else {
        Write-Host "❌ 오류: Python을 찾을 수 없습니다." -ForegroundColor Red
        Write-Host "`nPython 설치 방법:" -ForegroundColor Yellow
        Write-Host "1. https://www.python.org/downloads/ 에서 Python 다운로드" -ForegroundColor White
        Write-Host "2. 설치 시 'Add Python to PATH' 옵션 체크" -ForegroundColor White
        Write-Host "3. 또는 Microsoft Store에서 'Python' 검색하여 설치" -ForegroundColor White
        exit 1
    }
} else {
    Write-Host "❌ 오류: Python 스크립트를 찾을 수 없습니다: $pythonScript" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ 스크립트 실행 완료" -ForegroundColor Green
