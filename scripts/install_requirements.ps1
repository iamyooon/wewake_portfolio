# 필요한 Python 패키지 설치 스크립트

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "포트폴리오 보고서 자동화 - 패키지 설치" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Python 경로 확인
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $python) {
    Write-Host "`n❌ 오류: Python을 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "Python을 설치하고 PATH에 추가하세요." -ForegroundColor Yellow
    exit 1
}

Write-Host "`nPython 버전 확인:" -ForegroundColor Yellow
& $python.Source --version

Write-Host "`n필요한 패키지 설치 중..." -ForegroundColor Yellow
& $python.Source -m pip install --upgrade pip
& $python.Source -m pip install openai

Write-Host "`n✅ 설치 완료!" -ForegroundColor Green
Write-Host "`n설치된 패키지 확인:" -ForegroundColor Yellow
& $python.Source -m pip list | Select-String "openai"
