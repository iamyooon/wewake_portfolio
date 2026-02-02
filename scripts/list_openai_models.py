#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenAI API에서 사용 가능한 모든 모델 목록 조회"""

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
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

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

api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    print("[ERROR] OPENAI_API_KEY가 설정되지 않았습니다.")
    print(f"   {ENV_FILE} 파일에 OPENAI_API_KEY=your-key 형식으로 설정하세요.")
    sys.exit(1)

print("=" * 60)
print("OpenAI API 사용 가능한 모델 목록 조회")
print("=" * 60)

# OpenAI Models API 엔드포인트
url = "https://api.openai.com/v1/models"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

try:
    print("\n[1] Models API 엔드포인트로 조회 중...")
    response = requests.get(url, headers=headers, timeout=30)
    
    if response.status_code == 200:
        models_data = response.json()
        models = models_data.get('data', [])
        print(f"✅ 성공! 사용 가능한 모델 수: {len(models)}")
        print("\n" + "=" * 60)
        print("사용 가능한 모델 목록")
        print("=" * 60)
        
        # 모델을 ID로 정렬
        models_sorted = sorted(models, key=lambda x: x.get('id', ''))
        
        # 카테고리별로 분류
        gpt_models = []
        other_models = []
        
        for model in models_sorted:
            model_id = model.get('id', 'Unknown')
            created = model.get('created', 'Unknown')
            owned_by = model.get('owned_by', 'Unknown')
            
            if 'gpt' in model_id.lower():
                gpt_models.append((model_id, created, owned_by))
            else:
                other_models.append((model_id, created, owned_by))
        
        # GPT 모델 출력
        if gpt_models:
            print("\n📝 GPT 모델:")
            print("-" * 60)
            for model_id, created, owned_by in gpt_models:
                # 타임스탬프를 날짜로 변환
                if isinstance(created, int):
                    from datetime import datetime
                    try:
                        created_date = datetime.fromtimestamp(created).strftime('%Y-%m-%d')
                    except:
                        created_date = str(created)
                else:
                    created_date = str(created)
                
                print(f"  • {model_id}")
                print(f"    - 생성일: {created_date}")
                print(f"    - 소유자: {owned_by}")
                print()
        
        # 기타 모델 출력
        if other_models:
            print("\n🔧 기타 모델:")
            print("-" * 60)
            for model_id, created, owned_by in other_models:
                if isinstance(created, int):
                    from datetime import datetime
                    try:
                        created_date = datetime.fromtimestamp(created).strftime('%Y-%m-%d')
                    except:
                        created_date = str(created)
                else:
                    created_date = str(created)
                
                print(f"  • {model_id}")
                print(f"    - 생성일: {created_date}")
                print(f"    - 소유자: {owned_by}")
                print()
        
        # 요약 정보
        print("=" * 60)
        print("요약")
        print("=" * 60)
        print(f"총 모델 수: {len(models)}")
        print(f"GPT 모델 수: {len(gpt_models)}")
        print(f"기타 모델 수: {len(other_models)}")
        
        # 최신 GPT 모델 추천
        if gpt_models:
            print("\n💡 추천 모델 (최신 순):")
            # 생성일 기준으로 정렬 (최신순)
            gpt_sorted = sorted(gpt_models, key=lambda x: x[1] if isinstance(x[1], int) else 0, reverse=True)
            for i, (model_id, _, _) in enumerate(gpt_sorted[:5], 1):
                print(f"  {i}. {model_id}")
        
    elif response.status_code == 401:
        print("❌ 인증 실패 (401): API 키가 유효하지 않습니다.")
        print(f"   응답: {response.text[:200]}")
    elif response.status_code == 403:
        print("❌ 권한 없음 (403): API 키에 모델 목록 조회 권한이 없습니다.")
        print(f"   응답: {response.text[:200]}")
    else:
        print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
        response.raise_for_status()
        
except requests.exceptions.RequestException as e:
    print(f"❌ 네트워크 오류: {str(e)}")
except Exception as e:
    print(f"❌ 오류 발생: {str(e)}")
    import traceback
    print(traceback.format_exc()[:500])
