#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grok API에서 사용 가능한 모델 목록 확인"""

import os
import sys
import requests
from pathlib import Path

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# .env 파일에서 API 키 로드
ENV_FILE = Path(__file__).parent.parent / ".env"
if ENV_FILE.exists():
    encodings = ['utf-8', 'utf-8-sig', 'cp949', 'latin-1']
    content = None
    for encoding in encodings:
        try:
            with open(ENV_FILE, 'r', encoding=encoding) as f:
                content = f.read()
                break
        except UnicodeDecodeError:
            continue
    
    if content:
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

grok_key = os.environ.get('GROK_API_KEY')
if not grok_key:
    print("[ERROR] GROK_API_KEY가 설정되지 않았습니다.")
    sys.exit(1)

# 가능한 모델명들
possible_models = [
    "grok-beta",
    "grok-2",
    "grok-2-latest",
    "grok-2-1212",
    "grok",
    "grok-1",
    "grok-2-vision-1212",
    "grok-2-1212-preview",
]

base_url = "https://api.x.ai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {grok_key}",
    "Content-Type": "application/json"
}

print("=" * 60)
print("Grok API 모델 테스트")
print("=" * 60)

working_models = []
failed_models = []

for model_name in possible_models:
    data = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "Hello"
            }
        ],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            print(f"✅ {model_name}: 성공")
            working_models.append(model_name)
        elif response.status_code == 404:
            print(f"❌ {model_name}: 모델을 찾을 수 없음 (404)")
            failed_models.append((model_name, "404"))
        elif response.status_code == 403:
            error_text = response.text[:200]
            print(f"⚠️  {model_name}: 권한 오류 (403) - {error_text}")
            failed_models.append((model_name, f"403: {error_text}"))
        else:
            print(f"❌ {model_name}: HTTP {response.status_code} - {response.text[:100]}")
            failed_models.append((model_name, f"HTTP {response.status_code}"))
    except Exception as e:
        print(f"❌ {model_name}: 예외 발생 - {str(e)}")
        failed_models.append((model_name, str(e)))

print("\n" + "=" * 60)
print("결과 요약")
print("=" * 60)
print(f"\n✅ 작동하는 모델 ({len(working_models)}개):")
for model in working_models:
    print(f"   - {model}")

if failed_models:
    print(f"\n❌ 실패한 모델 ({len(failed_models)}개):")
    for model, error in failed_models:
        print(f"   - {model}: {error}")
