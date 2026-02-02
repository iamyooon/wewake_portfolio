# Git 스크립트

## 훅 설치

```powershell
.\scripts\git\install-git-hooks.ps1
```

- **pre-commit**: 커밋 전 스테이징된 `.py` 파일에 대해 `python -m py_compile` 문법 검사를 실행합니다.

## 커밋 방식 (COMMIT_GUIDE.md 참고)

- **권장**: 루트의 `.\commit.ps1` 사용. 또는 `commit-message.txt` 작성 후 `git commit -F commit-message.txt`
- 한글 커밋 메시지 인코딩 문제를 피하려면 `-m` 대신 `-F 파일` 사용을 권장합니다.
