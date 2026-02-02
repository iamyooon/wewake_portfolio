#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사용 가능한 Gemini 모델 목록 조회 스크립트
"""

import os
import sys
import requests
from pathlib import Path

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

def load_api_key():
    """환경 변수에서 API 키 로드"""
    api_key = os.environ.get('GEMINI_API_KEY')
    
    if not api_key and ENV_FILE.exists():
        # .env 파일에서 읽기
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
                if line.startswith('GEMINI_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    break
    
    if not api_key:
        print("[ERROR] GEMINI_API_KEY가 설정되지 않았습니다.")
        print(f"   {ENV_FILE} 파일에 GEMINI_API_KEY=your-key 형식으로 설정하세요.")
        sys.exit(1)
    
    return api_key

def list_models(api_key):
    """사용 가능한 모델 목록 조회"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        models = data.get('models', [])
        
        # generateContent를 지원하는 모델만 필터링
        generation_models = [
            m for m in models 
            if 'generateContent' in m.get('supportedGenerationMethods', [])
        ]
        
        print("=" * 80)
        print("사용 가능한 Gemini 모델 목록")
        print("=" * 80)
        print()
        
        for i, model in enumerate(generation_models, 1):
            model_name = model['name'].split('/')[-1]
            display_name = model.get('displayName', 'N/A')
            description = model.get('description', 'N/A')
            input_tokens = model.get('inputTokenLimit', 'N/A')
            output_tokens = model.get('outputTokenLimit', 'N/A')
            methods = ', '.join(model.get('supportedGenerationMethods', []))
            
            print(f"[{i}] {model_name}")
            print(f"    표시명: {display_name}")
            print(f"    설명: {description}")
            print(f"    입력 토큰 제한: {input_tokens:,}" if isinstance(input_tokens, int) else f"    입력 토큰 제한: {input_tokens}")
            print(f"    출력 토큰 제한: {output_tokens:,}" if isinstance(output_tokens, int) else f"    출력 토큰 제한: {output_tokens}")
            print(f"    지원 메서드: {methods}")
            print()
        
        print("=" * 80)
        print(f"총 {len(generation_models)}개 모델 사용 가능")
        print("=" * 80)
        
        # 추천 모델
        print("\n추천 모델:")
        print("  - gemini-2.5-flash: 빠르고 효율적 (일반 보고서용)")
        print("  - gemini-2.5-pro: 고품질 생성 (상세 분석용)")
        print("  - gemini-2.0-flash: 빠른 응답 (간단한 작업용)")
        
    except Exception as e:
        print(f"[ERROR] 모델 목록 조회 실패: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    api_key = load_api_key()
    list_models(api_key)
