#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포트폴리오 보고서 협업 생성 스크립트 (Gemini + Grok 협업)
1. Gemini가 프롬프트 기반으로 초안 작성
2. Grok이 초안을 리뷰하고 코멘트 제공
3. Gemini가 코멘트를 반영/반박하며 최종 보고서 완성
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import json
import requests

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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
    
    gemini_key = os.environ.get('GEMINI_API_KEY')
    grok_key = os.environ.get('GROK_API_KEY')
    
    if not gemini_key:
        print("[ERROR] GEMINI_API_KEY가 설정되지 않았습니다.")
        print(f"   {ENV_FILE} 파일에 GEMINI_API_KEY=your-key 형식으로 설정하세요.")
        sys.exit(1)
    
    if not grok_key:
        print("[ERROR] GROK_API_KEY가 설정되지 않았습니다.")
        print(f"   {ENV_FILE} 파일에 GROK_API_KEY=your-key 형식으로 설정하세요.")
        print("   참고: Grok API는 xAI에서 제공합니다.")
        sys.exit(1)
    
    return gemini_key, grok_key

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
    return f"portfolio_report_{date_str}_collaborative.md"

def create_initial_prompt(portfolio_prompt_content):
    """Gemini에게 보낼 초기 프롬프트를 생성합니다."""
    today = datetime.now()
    date_str = today.strftime("%Y년 %m월 %d일")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y년 %m월 %d일")
    
    prompt = f"""너는 '위웨이크 주식회사'의 포트폴리오 매니저야.

작성일: {date_str} (어제 종가 기준: {yesterday_str})

{portfolio_prompt_content}

위 지침에 따라 포트폴리오 보고서 초안을 작성해주세요. 보고서는 마크다운 형식으로 작성하고, 모든 섹션을 빠짐없이 포함해야 합니다.

보고서 구조:
1. 포트폴리오 운영 목표
2. 어제 기준 마켓 현황 (실시간 환율, 주요 종목 등락, 리스크 요인)
3. 어제 기준 자산 현황표 (모든 종목 포함)
4. 목표 달성 로드맵 점검
5. 정리 코멘트

중요: 환율과 주가는 웹 검색을 통해 최신 정보를 사용하되, 정확하지 않은 경우 이전 보고서의 패턴을 참고하여 작성하세요.
"""
    return prompt

def call_gemini_api(api_key, prompt, model_name='gemini-3-pro-preview'):
    """Gemini API를 호출합니다."""
    import time
    
    # 여러 모델을 순서대로 시도
    models_to_try = [
        'gemini-3-pro-preview',
        'gemini-2.5-pro',
        'gemini-2.5-flash',
        'gemini-pro',
    ]
    
    # 지정된 모델이 있으면 우선 시도
    if model_name in models_to_try:
        models_to_try.remove(model_name)
        models_to_try.insert(0, model_name)
    
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.95,
            "topK": 40,
            "maxOutputTokens": 16384,
        }
    }
    
    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        # 최대 3번 재시도
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=120)
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        if model != models_to_try[0]:
                            print(f"   Fallback 모델 사용: {model}")
                        return result['candidates'][0]['content']['parts'][0]['text']
                elif response.status_code == 503:
                    # 서버 오류 - 재시도
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # 2초, 4초, 6초 대기
                        print(f"   서버 오류 (503) - {wait_time}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        # 마지막 시도도 실패하면 다음 모델로
                        print(f"   모델 {model} 재시도 실패 - 다음 모델 시도")
                        break
                elif response.status_code == 429:
                    # 할당량 초과 - 다음 모델로
                    print(f"   모델 {model} 할당량 초과 - 다음 모델 시도")
                    break
                else:
                    response.raise_for_status()
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"   네트워크 오류 - {wait_time}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"   모델 {model} 호출 실패: {str(e)}")
                    break
    
    print(f"[ERROR] 모든 Gemini 모델 시도 실패")
    return None

def call_grok_api(api_key, prompt):
    """Grok API를 호출합니다."""
    # 여러 가능한 모델명 시도
    possible_models = [
        "grok-beta",
        "grok-2",
        "grok-2-latest",
        "grok-2-1212",
        "grok",
        "grok-1",
    ]
    
    # Grok API 엔드포인트 (xAI API 사용)
    base_url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    for model_name in possible_models:
        data = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 전문적인 포트폴리오 보고서 리뷰어입니다. 보고서의 정확성, 완성도, 논리성을 검토하고 구체적인 개선 사항을 제안합니다."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 8000
        }
        
        try:
            response = requests.post(base_url, headers=headers, json=data, timeout=120)
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    print(f"   Grok 모델 사용: {model_name}")
                    return result['choices'][0]['message']['content']
            elif response.status_code == 404:
                # 모델을 찾을 수 없음 - 다음 모델 시도
                continue
            elif response.status_code == 403:
                # 권한 오류 - 에러 메시지 출력 후 종료
                error_detail = response.text
                print(f"[ERROR] Grok API 권한 오류 (403)")
                print(f"   시도한 모델: {model_name}")
                print(f"   응답: {error_detail[:200]}")
                if model_name == possible_models[-1]:
                    # 마지막 모델도 실패하면 종료
                    print(f"   모든 모델 시도 실패. xAI 공식 문서에서 최신 모델명을 확인하세요.")
                    return None
                continue
            else:
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            if model_name == possible_models[-1]:
                # 마지막 모델도 실패하면 에러 출력
                print(f"[ERROR] Grok API 호출 실패: {str(e)}")
                print(f"   참고: Grok API 엔드포인트나 모델명이 변경되었을 수 있습니다.")
                print(f"   xAI 공식 문서 확인: https://docs.x.ai/")
            continue
    
    return None

def create_review_prompt(draft_report, portfolio_prompt_content):
    """Grok에게 보낼 리뷰 프롬프트를 생성합니다."""
    prompt = f"""다음은 포트폴리오 보고서 초안입니다. 이 보고서를 검토하고 다음 관점에서 코멘트를 제공해주세요:

1. **정확성**: 데이터와 계산이 정확한가?
2. **완성도**: 필수 섹션이 모두 포함되었는가?
3. **논리성**: 분석과 결론이 논리적으로 연결되어 있는가?
4. **개선점**: 더 명확하거나 구체적으로 개선할 수 있는 부분은?

아래 형식으로 코멘트를 제공해주세요:

## 리뷰 코멘트

### 강점
- (보고서의 잘된 부분)

### 개선 필요 사항
- (구체적인 개선 제안)

### 추가 제안
- (보고서에 추가하면 좋을 내용)

---

**포트폴리오 프롬프트 (참고용)**:
{portfolio_prompt_content[:500]}...

---

**보고서 초안**:
{draft_report}
"""
    return prompt

def create_revision_prompt(original_draft, review_comments, portfolio_prompt_content):
    """Gemini에게 보낼 수정 프롬프트를 생성합니다."""
    prompt = f"""다음은 당신이 작성한 포트폴리오 보고서 초안과 리뷰 코멘트입니다.

**원본 보고서**:
{original_draft}

**리뷰 코멘트**:
{review_comments}

리뷰 코멘트를 검토하고:
1. 타당한 지적은 반영하여 보고서를 개선하세요
2. 부적절하거나 불필요한 제안은 반박하며 원래 내용을 유지하세요
3. 추가 제안이 유용하면 반영하세요

최종 보고서를 작성해주세요. 모든 섹션을 빠짐없이 포함하고, 개선된 내용을 반영하세요.

**포트폴리오 프롬프트 (참고용)**:
{portfolio_prompt_content}
"""
    return prompt

def main():
    """메인 함수"""
    print("=" * 60)
    print("포트폴리오 보고서 협업 생성 스크립트 (Gemini + Grok)")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 환경 변수 로드
    print("\n[1/5] 환경 변수 로드 중...")
    gemini_key, grok_key = load_env()
    print("[OK] API 키 로드 완료")
    
    print("\n[2/5] 포트폴리오 프롬프트 파일 읽는 중...")
    portfolio_prompt = read_portfolio_prompt()
    print("[OK] 파일 읽기 완료")
    
    # 보고서 파일명 생성
    report_filename = generate_report_filename()
    report_path = REPORTS_DIR / report_filename
    
    if report_path.exists():
        print(f"\n[WARNING] {report_filename} 파일이 이미 존재합니다.")
        print("   자동 모드: 기존 파일을 덮어씁니다.")
    
    # Step 1: Gemini가 초안 작성
    print("\n[3/5] Gemini가 보고서 초안 작성 중...")
    initial_prompt = create_initial_prompt(portfolio_prompt)
    draft_report = call_gemini_api(gemini_key, initial_prompt)
    
    if not draft_report:
        print("[ERROR] 초안 작성 실패")
        return 1
    
    print(f"[OK] 초안 작성 완료 ({len(draft_report)} 문자)")
    
    # Step 2: Grok이 리뷰
    print("\n[4/5] Grok이 초안 리뷰 중...")
    review_prompt = create_review_prompt(draft_report, portfolio_prompt)
    review_comments = call_grok_api(grok_key, review_prompt)
    
    if not review_comments:
        print("[WARNING] Grok 리뷰 실패 - 초안을 그대로 사용합니다.")
        review_comments = "리뷰를 받지 못했습니다."
        final_report = draft_report
    else:
        print(f"[OK] 리뷰 완료 ({len(review_comments)} 문자)")
        
        # Step 3: Gemini가 리뷰 반영하여 최종 보고서 작성
        print("\n[5/5] Gemini가 리뷰 반영하여 최종 보고서 작성 중...")
        revision_prompt = create_revision_prompt(draft_report, review_comments, portfolio_prompt)
        final_report = call_gemini_api(gemini_key, revision_prompt)
        
        if not final_report:
            print("[WARNING] 최종 보고서 작성 실패 - 초안을 사용합니다.")
            final_report = draft_report
    
    # 보고서 저장
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 위웨이크 주식회사 포트폴리오 보고서 (Gemini + Grok 협업)\n")
        f.write(f"**작성일: {datetime.now().strftime('%Y년 %m월 %d일')} (어제 종가 기준: {(datetime.now() - timedelta(days=1)).strftime('%Y년 %m월 %d일')})**\n\n")
        f.write("---\n\n")
        f.write("## 최종 보고서\n\n")
        f.write(final_report)
        f.write("\n\n---\n\n")
        f.write("## 리뷰 과정 (참고용)\n\n")
        f.write("### 초안 (Gemini 작성)\n\n")
        f.write("<details>\n<summary>초안 보기</summary>\n\n")
        f.write(draft_report)
        f.write("\n\n</details>\n\n")
        f.write("### 리뷰 코멘트 (Grok 작성)\n\n")
        f.write(review_comments)
        f.write("\n\n")
    
    print(f"\n[SUCCESS] 협업 보고서 생성 완료: {report_filename}")
    print(f"   파일 위치: {report_path}")
    print(f"   최종 보고서 크기: {len(final_report)} 문자")
    print(f"   리뷰 코멘트 크기: {len(review_comments)} 문자")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
