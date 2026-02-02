# Gemini API 설정 가이드

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Google Gemini API 설정" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "1. API 키 발급:" -ForegroundColor Yellow
Write-Host "   https://makersuite.google.com/app/apikey" -ForegroundColor White
Write-Host "   또는 https://aistudio.google.com/app/apikey" -ForegroundColor White

Write-Host ""
Write-Host "2. .env 파일에 추가:" -ForegroundColor Yellow
Write-Host "   GEMINI_API_KEY=your-api-key-here" -ForegroundColor White

Write-Host ""
Write-Host "3. 패키지 설치:" -ForegroundColor Yellow
Write-Host "   pip install google-generativeai" -ForegroundColor White

Write-Host ""
Write-Host "4. 테스트 실행:" -ForegroundColor Yellow
Write-Host "   python scripts\generate_portfolio_report_gemini.py" -ForegroundColor White

Write-Host ""
Write-Host "5. 자동화 스크립트에서 Gemini 사용:" -ForegroundColor Yellow
Write-Host "   .env 파일에 PORTFOLIO_MODEL=gemini 추가" -ForegroundColor White
Write-Host "   또는 환경 변수로 설정:" -ForegroundColor White
Write-Host "   `$env:PORTFOLIO_MODEL='gemini'" -ForegroundColor Gray
