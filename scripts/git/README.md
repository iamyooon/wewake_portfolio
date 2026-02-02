# Git 스크립트

## 훅 설치

```powershell
.\scripts\git\install-git-hooks.ps1
```

- **pre-commit**: 커밋 전 스테이징된 `.py` 파일에 대해 `python -m py_compile` 문법 검사를 실행합니다.
- **post-commit**: 커밋 후 Jira 이슈에 코멘트를 자동으로 추가합니다. (Node.js 필요, `.env`에 Jira 설정 필요)

## Jira 연동

- **환경 변수**: `.env` 또는 `.env.local` 에 `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `DEFAULT_ISSUE_KEY` 를 넣습니다.
- **이슈 번호**: `DEFAULT_ISSUE_KEY` 에 이 프로젝트용 Jira 이슈 키(예: `PDR-1`)를 지정합니다.  
  다른 프로젝트(예: english-write-study-app-main)의 `.env` 에서 JIRA_URL/EMAIL/TOKEN 을 복사하고, 이슈 번호만 바꾸면 됩니다.
- **수동 실행**: `node scripts/git/jira.mjs post-commit` / `node scripts/git/jira.mjs comment "내용"` / `node scripts/git/jira.mjs summary --file jira-comment.txt` 등. `node scripts/git/jira.mjs` 로 도움말 확인.

## 커밋 방식 (COMMIT_GUIDE.md 참고)

- **권장**: 루트의 `.\commit.ps1` 사용. 또는 `commit-message.txt` 작성 후 `git commit -F commit-message.txt`
- 한글 커밋 메시지 인코딩 문제를 피하려면 `-m` 대신 `-F 파일` 사용을 권장합니다.
