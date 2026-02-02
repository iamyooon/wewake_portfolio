# Git hooks 설치 스크립트
# pre-commit hook을 설치하여 커밋 전 검사 실행

Write-Host "Git hooks 설치 중..." -ForegroundColor Cyan

$hooksDir = ".git\hooks"
$preCommitHook = "$hooksDir\pre-commit"
if (-not (Test-Path $hooksDir)) {
    Write-Host ".git/hooks 디렉토리를 찾을 수 없습니다." -ForegroundColor Red
    exit 1
}

# pre-commit hook: sh 스크립트 (Git은 저장소 루트에서 실행)
$hookContent = @"
#!/bin/sh
# Git pre-commit hook - 커밋 전 검사
if [ -f "scripts/git/pre-commit.ps1" ]; then
    powershell.exe -ExecutionPolicy Bypass -NoProfile -File "scripts/git/pre-commit.ps1"
    exit `$?
fi
exit 0
"@

$hookContent | Out-File -FilePath $preCommitHook -Encoding ASCII -NoNewline

if (Get-Command chmod -ErrorAction SilentlyContinue) {
    chmod +x $preCommitHook
}

Write-Host "pre-commit hook이 설치되었습니다." -ForegroundColor Green
Write-Host "커밋할 때마다 scripts/git/pre-commit.ps1 이 실행됩니다." -ForegroundColor Cyan
