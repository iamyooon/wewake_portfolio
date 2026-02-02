# 커밋 가이드

## 한글 인코딩

PowerShell에서 `git commit -m "한글"` 을 쓰면 인코딩 문제가 날 수 있으므로, **메시지 파일**을 사용해 커밋하는 방식을 권장합니다.

## 1) 스크립트로 커밋 (권장)

```powershell
# 메시지 인자로 넘기기
.\commit.ps1 "커밋 메시지 내용"

# 메시지 없이 실행 시: commit-message.txt 또는 .git-commit-template.txt 사용
.\commit.ps1
```

## 2) 파일로 직접 커밋

1. **commit-message.txt** 또는 **.git-commit-template.txt** 에 커밋 메시지를 UTF-8로 작성합니다.
2. 스테이징 후 파일을 사용해 커밋합니다.

```powershell
git add -A
git commit -F commit-message.txt
```

## Git Hook (pre-commit)

커밋 전에 스테이징된 Python 파일 문법 검사가 자동으로 실행되도록 하려면:

```powershell
.\scripts\git\install-git-hooks.ps1
```

설치 후 `git commit` 할 때마다 `scripts/git/pre-commit.ps1` 이 실행됩니다.  
자세한 내용은 `scripts/git/README.md` 를 참고하세요.
