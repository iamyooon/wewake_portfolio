# Pre-commit hook - 커밋 전 검사 (Python 프로젝트)
# 스테이징된 .py 파일 문법 검사

$ErrorActionPreference = "Stop"

Write-Host "커밋 전 검사 시작..." -ForegroundColor Cyan

$stagedPy = git diff --cached --name-only --diff-filter=ACM | Where-Object { $_ -match '\.py$' }
if (-not $stagedPy) {
    Write-Host "스테이징된 Python 파일 없음. 검사 생략." -ForegroundColor Gray
    exit 0
}

$failed = $false
foreach ($f in $stagedPy) {
    if (-not (Test-Path $f)) { continue }
    $err = python -m py_compile $f 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "문법 오류: $f" -ForegroundColor Red
        Write-Host $err
        $failed = $true
    }
}

if ($failed) {
    Write-Host "Python 문법 검사 실패. 커밋을 중단합니다." -ForegroundColor Red
    exit 1
}

Write-Host "검사 통과." -ForegroundColor Green
exit 0
