#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포트폴리오 보고서 자동 생성 스크립트 (Google Gemini API 버전)
매일 아침 8시에 portfolio_prompt.txt 기반으로 보고서를 자동 생성합니다.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import json

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Google Gemini API 사용
try:
    import google.genai as genai
except ImportError:
    try:
        import google.generativeai as genai
        print("[WARNING] google.generativeai는 deprecated되었습니다. google-genai로 업그레이드하세요.")
    except ImportError:
        print("[ERROR] google-genai 또는 google-generativeai 라이브러리가 설치되지 않았습니다.")
        print("다음 명령으로 설치하세요: pip install google-genai")
        sys.exit(1)

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
ENV_FILE = PROJECT_ROOT / ".env"
REPORTS_DIR = PROJECT_ROOT

def get_portfolio_prompt_path():
    """prompts/config.json의 portfolio_prompt_file을 읽어 경로 반환. 없으면 prompts/portfolio_prompt.txt."""
    try:
        cfg_path = PROMPTS_DIR / "config.json"
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("portfolio_prompt_file"):
                return PROMPTS_DIR / data["portfolio_prompt_file"]
    except Exception:
        pass
    return PROMPTS_DIR / "portfolio_prompt.txt"

def load_env():
    """환경 변수 로드 (.env 파일에서)"""
    if ENV_FILE.exists():
        # 여러 인코딩 시도
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
    
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("[ERROR] GEMINI_API_KEY가 설정되지 않았습니다.")
        print(f"   {ENV_FILE} 파일에 GEMINI_API_KEY=your-key 형식으로 설정하세요.")
        print("   API 키 발급: https://makersuite.google.com/app/apikey")
        sys.exit(1)
    
    return api_key

def read_portfolio_prompt():
    """포트폴리오 프롬프트 파일을 읽어옵니다 (경로는 config.json 기준)."""
    path = get_portfolio_prompt_path()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] {path} 파일을 찾을 수 없습니다.")
        sys.exit(1)

def generate_report_filename():
    """보고서 파일명을 생성합니다."""
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    return f"portfolio_report_{date_str}_auto.md"

def create_report_prompt(portfolio_prompt_content):
    """보고서 생성을 위한 프롬프트를 생성합니다."""
    today = datetime.now()
    date_str = today.strftime("%Y년 %m월 %d일")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y년 %m월 %d일")
    
    prompt = f"""너는 '위웨이크 주식회사'의 포트폴리오 매니저야.

작성일: {date_str} (어제 종가 기준: {yesterday_str})

{portfolio_prompt_content}

위 지침에 따라 포트폴리오 보고서를 작성해주세요. 보고서는 마크다운 형식으로 작성하고, 모든 섹션을 빠짐없이 포함해야 합니다.

보고서 구조:
1. 포트폴리오 운영 목표
2. 어제 기준 마켓 현황 (실시간 환율, 주요 종목 등락, 리스크 요인)
3. 어제 기준 자산 현황표 (모든 종목 포함)
4. 목표 달성 로드맵 점검
5. 정리 코멘트

중요: 환율과 주가는 웹 검색을 통해 최신 정보를 사용하되, 정확하지 않은 경우 이전 보고서의 패턴을 참고하여 작성하세요.
"""
    return prompt

def generate_report_with_gemini(api_key, prompt):
    """Google Gemini API를 사용하여 보고서를 생성합니다."""
    print("Google Gemini API 호출 중...")
    
    try:
        # REST API 직접 호출 (가장 안정적)
        import requests
        
        # 먼저 사용 가능한 모델 확인
        try:
            models_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            models_response = requests.get(models_url, timeout=30)
            if models_response.status_code == 200:
                models_data = models_response.json()
                available_models = [m['name'].split('/')[-1] for m in models_data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
                print(f"   사용 가능한 모델: {', '.join(available_models[:5])}")
                
                # Gemini 3 Pro를 우선적으로 찾기
                preferred_models = ['gemini-3-pro-preview', 'gemini-3-pro']
                model_names = []
                
                # 우선 모델이 있으면 먼저 추가
                for preferred in preferred_models:
                    if preferred in available_models:
                        model_names.append(preferred)
                        print(f"   Gemini 3 Pro 발견: {preferred}")
                
                # 나머지 모델 추가
                for model in available_models[:5]:
                    if model not in model_names:
                        model_names.append(model)
                
                if not model_names:
                    model_names = available_models[:3] if available_models else []
            else:
                model_names = []
        except:
            model_names = []
        
        # 기본 모델 목록 (fallback) - Gemini 3 Pro 우선
        if not model_names:
            model_names = [
                'gemini-3-pro-preview',  # Gemini 3 Pro 우선 사용
                'gemini-2.5-pro',
                'gemini-2.5-flash',
                'gemini-2.0-flash',
                'gemini-pro'
            ]
        
        for model_name in model_names:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                data = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "topP": 0.95,
                        "topK": 40,
                        "maxOutputTokens": 16384,  # 더 긴 보고서를 위해 증가
                    }
                }
                
                print(f"   모델 시도: {model_name}")
                response = requests.post(url, headers=headers, json=data, timeout=120)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        report_content = result['candidates'][0]['content']['parts'][0]['text']
                        print(f"   성공: {model_name}")
                        return report_content
                    else:
                        print(f"   응답 형식 오류: {response.text[:200]}")
                elif response.status_code == 404:
                    # 모델을 찾을 수 없음, 다음 모델 시도
                    print(f"   404 오류: {model_name}")
                    continue
                else:
                    # 다른 오류
                    print(f"   오류 ({response.status_code}): {response.text[:200]}")
                    if response.status_code != 404:
                        response.raise_for_status()
                    
            except requests.exceptions.RequestException as e:
                print(f"   요청 오류: {str(e)[:100]}")
                if '404' not in str(e):
                    continue  # 다음 모델 시도
        
        # 모든 모델 실패
        raise Exception("사용 가능한 Gemini 모델을 찾을 수 없습니다. API 키를 확인해주세요.")
        
    except Exception as e:
        print(f"[ERROR] Google Gemini API 호출 실패")
        print(f"   {str(e)}")
        return None

def main():
    """메인 함수"""
    print("=" * 60)
    print("포트폴리오 보고서 자동 생성 스크립트 (Google Gemini API)")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 환경 변수 로드
    print("\n[1/4] 환경 변수 로드 중...")
    api_key = load_env()
    print("[OK] API 키 로드 완료")
    
    print("\n[2/4] 포트폴리오 프롬프트 파일 읽는 중...")
    portfolio_prompt = read_portfolio_prompt()
    print("[OK] 파일 읽기 완료")
    
    # 보고서 파일명 생성
    report_filename = generate_report_filename()
    report_path = REPORTS_DIR / report_filename
    
    # 이미 보고서가 존재하는지 확인
    if report_path.exists():
        print(f"\n[WARNING] {report_filename} 파일이 이미 존재합니다.")
        print("   자동 모드: 기존 파일을 덮어씁니다.")
    
    # 프롬프트 생성
    print("\n[3/4] 보고서 프롬프트 생성 중...")
    report_prompt = create_report_prompt(portfolio_prompt)
    
    # Gemini API로 보고서 생성
    print("\n[4/4] Google Gemini API로 보고서 생성 중...")
    report_content = generate_report_with_gemini(api_key, report_prompt)
    
    if report_content:
        # 보고서 저장
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# 위웨이크 주식회사 포트폴리오 보고서\n")
            f.write(f"**작성일: {datetime.now().strftime('%Y년 %m월 %d일')} (어제 종가 기준: {(datetime.now() - timedelta(days=1)).strftime('%Y년 %m월 %d일')})**\n\n")
            f.write("---\n\n")
            f.write(report_content)
        
        print(f"\n[SUCCESS] 보고서 생성 완료: {report_filename}")
        print(f"   파일 위치: {report_path}")
        print(f"   파일 크기: {len(report_content)} 문자")
        return 0
    else:
        print("\n[ERROR] 보고서 생성 실패")
        return 1

if __name__ == "__main__":
    sys.exit(main())
