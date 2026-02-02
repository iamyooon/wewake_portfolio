# 커밋 스크립트 - 한글 인코딩 방지 (파일로 커밋)
# 사용법: .\commit.ps1 "커밋 메시지"
# 또는:  .\commit.ps1  (메시지 입력 없으면 commit-message.txt / .git-commit-template.txt 사용)

param(
    [Parameter(Mandatory=$false)]
    [string]$Message
)

$msgFile = "commit-message.txt"
$templateFile = ".git-commit-template.txt"

if ($Message) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText((Join-Path $PSScriptRoot $msgFile), $Message, $utf8NoBom)
    $useFile = $msgFile
} else {
    if (Test-Path $msgFile) { $useFile = $msgFile }
    elseif (Test-Path $templateFile) { $useFile = $templateFile }
    else {
        Write-Host "커밋 메시지가 없습니다. .\commit.ps1 `"메시지`" 또는 commit-message.txt / .git-commit-template.txt 를 작성하세요." -ForegroundColor Red
        exit 1
    }
}

git commit -F $useFile
if ($LASTEXITCODE -eq 0) { Write-Host "커밋 완료." -ForegroundColor Green }
