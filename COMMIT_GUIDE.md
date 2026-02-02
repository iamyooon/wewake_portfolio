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

## Git Hook (pre-commit / post-commit)

```powershell
.\scripts\git\install-git-hooks.ps1
```

- **pre-commit**: 커밋 전 스테이징된 `.py` 문법 검사.
- **post-commit**: 커밋 후 Jira 이슈에 코멘트 자동 추가. (Node.js 필요, `.env`에 `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `DEFAULT_ISSUE_KEY` 설정. 다른 프로젝트 `.env`에서 키 복사 후 이슈 번호만 `DEFAULT_ISSUE_KEY`로 지정하면 됨.)

자세한 내용은 `scripts/git/README.md` 를 참고하세요.
