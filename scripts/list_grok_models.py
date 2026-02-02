#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grok API에서 사용 가능한 모든 모델 목록 조회"""

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

print("=" * 60)
print("Grok API 사용 가능한 모델 목록 조회")
print("=" * 60)

# 방법 1: Models API 엔드포인트 사용
models_url = "https://api.x.ai/v1/models"
headers = {
    "Authorization": f"Bearer {grok_key}",
    "Content-Type": "application/json"
}

try:
    print("\n[방법 1] Models API 엔드포인트로 조회 중...")
    response = requests.get(models_url, headers=headers, timeout=30)
    
    if response.status_code == 200:
        models_data = response.json()
        print(f"✅ 성공! 사용 가능한 모델 수: {len(models_data.get('data', []))}")
        print("\n사용 가능한 모델 목록:")
        print("-" * 60)
        
        for model in models_data.get('data', []):
            model_id = model.get('id', 'Unknown')
            created = model.get('created', 'Unknown')
            owned_by = model.get('owned_by', 'Unknown')
            print(f"  • {model_id}")
            print(f"    - 생성일: {created}")
            print(f"    - 소유자: {owned_by}")
            print()
    elif response.status_code == 404:
        print("❌ Models API 엔드포인트를 찾을 수 없습니다.")
    else:
        print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
except Exception as e:
    print(f"❌ 오류 발생: {str(e)}")

# 방법 2: 직접 테스트 (최신 모델명 시도)
print("\n" + "=" * 60)
print("[방법 2] 최신 모델명 직접 테스트")
print("=" * 60)

# 최신 모델명 후보들
latest_models = [
    "grok-2",
    "grok-2-latest",
    "grok-2-2025",
    "grok-2-beta",
    "grok-2.5",
    "grok-2.5-beta",
    "grok-2.5-latest",
    "grok-3",
    "grok-3-beta",
    "grok-beta",
    "grok-2-vision-1212",  # 현재 사용 중인 모델
    "grok-2-1212",
]

base_url = "https://api.x.ai/v1/chat/completions"
working_models = []

for model_name in latest_models:
    data = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "test"
            }
        ],
        "max_tokens": 5
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            print(f"✅ {model_name}: 사용 가능")
            working_models.append(model_name)
        elif response.status_code == 404:
            print(f"❌ {model_name}: 모델을 찾을 수 없음")
        elif response.status_code == 403:
            print(f"⚠️  {model_name}: 권한 오류 (크레딧 부족 또는 접근 불가)")
        else:
            print(f"❌ {model_name}: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ {model_name}: 예외 - {str(e)[:50]}")

print("\n" + "=" * 60)
print("결과 요약")
print("=" * 60)
if working_models:
    print(f"\n✅ 사용 가능한 모델 ({len(working_models)}개):")
    for model in working_models:
        print(f"   - {model}")
else:
    print("\n❌ 테스트한 모델 중 사용 가능한 모델이 없습니다.")
