# 포트폴리오 보고서 자동 생성 PowerShell 스크립트
# 매일 아침 8시에 실행되도록 Windows Task Scheduler에 등록

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
Write-Host "포트폴리오 보고서 자동 생성" -ForegroundColor Cyan
Write-Host "실행 시간: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 모델 선택 (openai, gemini, collaborative, 또는 openai_grok)
$model = $env:PORTFOLIO_MODEL
if (-not $model) {
    # .env 파일에서 확인
    $envFile = Join-Path $ProjectPath ".env"
    if (Test-Path $envFile) {
        $envContent = Get-Content $envFile -Raw
        # OpenAI와 Grok 키가 모두 있으면 OpenAI+Grok 협업 모드 (우선순위 1)
        if ($envContent -match "OPENAI_API_KEY=" -and $envContent -match "GROK_API_KEY=") {
            $model = "openai_grok"  # OpenAI + Grok 협업 모드
        }
        # Gemini와 Grok 키가 모두 있으면 Gemini+Grok 협업 모드 (우선순위 2)
        elseif ($envContent -match "GEMINI_API_KEY=" -and $envContent -match "GROK_API_KEY=") {
            $model = "collaborative"  # Gemini + Grok 협업 모드
        }
        # Gemini만 있으면 Gemini 단독 모드
        elseif ($envContent -match "GEMINI_API_KEY=") {
            $model = "gemini"  # Gemini만 사용
        }
        # OpenAI만 있으면 OpenAI 단독 모드
        elseif ($envContent -match "OPENAI_API_KEY=") {
            $model = "openai"  # OpenAI 사용
        } else {
            $model = "openai"  # 기본값: OpenAI
        }
    } else {
        $model = "openai"  # 기본값: OpenAI
    }
}

# Python 스크립트 선택
if ($model -eq "openai_grok") {
    $pythonScript = Join-Path $ProjectPath "scripts\generate_portfolio_report_openai_grok.py"
} elseif ($model -eq "collaborative") {
    $pythonScript = Join-Path $ProjectPath "scripts\generate_portfolio_report_collaborative.py"
} elseif ($model -eq "gemini") {
    $pythonScript = Join-Path $ProjectPath "scripts\generate_portfolio_report_gemini.py"
} else {
    $pythonScript = Join-Path $ProjectPath "scripts\generate_portfolio_report_openai.py"
}

Write-Host "사용 모델: $model" -ForegroundColor Cyan

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
