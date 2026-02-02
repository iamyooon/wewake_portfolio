#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포트폴리오 보고서 협업 생성 스크립트 (OpenAI + Grok 협업)
1. OpenAI가 프롬프트 기반으로 초안 작성
2. Grok이 초안을 리뷰하고 코멘트 제공
3. OpenAI가 코멘트를 반영/반박하며 최종 보고서 완성

사용법:
    python generate_portfolio_report_openai_grok.py [옵션]

옵션:
    --openai-model MODEL     OpenAI 모델 지정 (기본값: gpt-5.2)
    --grok-model MODEL       Grok 모델 지정 (기본값: grok-4)
    --prompt-file FILE        프롬프트 파일 경로 (기본값: prompts/config.json의 portfolio_prompt_file)
    --output-file FILE        결과 파일 경로 (기본값: 자동 생성)
"""

import os
import sys
import argparse
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

def get_default_prompt_file():
    """기본 포트폴리오 프롬프트 경로 (prompts/config.json 기준)."""
    try:
        cfg_path = PROMPTS_DIR / "config.json"
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("portfolio_prompt_file"):
                name = data["portfolio_prompt_file"].strip() or "portfolio_prompt.txt"
                return "prompts/" + name if not name.startswith("prompts/") else name
    except Exception:
        pass
    return "prompts/portfolio_prompt.txt"

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
    
    openai_key = os.environ.get('OPENAI_API_KEY')
    grok_key = os.environ.get('GROK_API_KEY')
    
    if not openai_key:
        print("[ERROR] OPENAI_API_KEY가 설정되지 않았습니다.")
        print(f"   {ENV_FILE} 파일에 OPENAI_API_KEY=your-key 형식으로 설정하세요.")
        sys.exit(1)
    
    if not grok_key:
        print("[ERROR] GROK_API_KEY가 설정되지 않았습니다.")
        print(f"   {ENV_FILE} 파일에 GROK_API_KEY=your-key 형식으로 설정하세요.")
        sys.exit(1)
    
    return openai_key, grok_key

def read_portfolio_prompt(prompt_file_path):
    """프롬프트 파일을 읽어옵니다."""
    try:
        prompt_path = Path(prompt_file_path)
        if not prompt_path.is_absolute():
            # 상대 경로인 경우 프로젝트 루트 기준으로 해석
            prompt_path = PROJECT_ROOT / prompt_path
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] 프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 프롬프트 파일 읽기 실패: {str(e)}")
        sys.exit(1)

def generate_report_filename(openai_model=None, grok_model=None, output_file=None):
    """보고서 파일명을 생성합니다."""
    if output_file:
        # 사용자가 지정한 파일명 사용
        output_path = Path(output_file)
        if not output_path.is_absolute():
            output_path = REPORTS_DIR / output_path
        return output_path.name, output_path
    
    # 자동 생성
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    time_str = today.strftime("%H%M")
    
    # 모델명을 파일명에 사용 가능한 형식으로 변환
    model_parts = []
    if openai_model:
        # gpt-4o -> gpt4o, gpt-4-turbo -> gpt4turbo
        openai_model_clean = openai_model.replace('-', '').replace('_', '')
        model_parts.append(f"openai-{openai_model_clean}")
    if grok_model:
        # grok-4-1-fast-reasoning -> grok-4-1-fast-reasoning (하이픈 유지)
        grok_model_clean = grok_model.replace('_', '-')
        model_parts.append(f"grok-{grok_model_clean}")
    
    model_suffix = "_".join(model_parts) if model_parts else "openai_grok"
    
    filename = f"portfolio_report_{date_str}_{time_str}_{model_suffix}.md"
    filepath = REPORTS_DIR / filename
    return filename, filepath

def create_initial_prompt(portfolio_prompt_content):
    """OpenAI에게 보낼 초기 프롬프트를 생성합니다."""
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

def call_openai_api(api_key, prompt, model='gpt-5.2', preferred_model=None):
    """OpenAI API를 호출합니다. 사용된 모델명을 반환합니다."""
    import time
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 여러 모델을 순서대로 시도
    models_to_try = [
        'gpt-5.2',  # 최신 모델 (최우선)
        'gpt-4o',
        'gpt-4-turbo',
        'gpt-4',
        'gpt-3.5-turbo',
    ]
    
    # 사용자가 지정한 모델이 있으면 최우선
    if preferred_model:
        if preferred_model in models_to_try:
            models_to_try.remove(preferred_model)
        models_to_try.insert(0, preferred_model)
    elif model in models_to_try:
        models_to_try.remove(model)
        models_to_try.insert(0, model)
    
    data_template = {
        "messages": [
            {
                "role": "system",
                "content": "당신은 전문적인 포트폴리오 매니저입니다. 정확하고 상세한 포트폴리오 보고서를 작성합니다."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 16000
    }
    
    for model_name in models_to_try:
        data = data_template.copy()
        data["model"] = model_name
        
        # 최대 3번 재시도
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=180)
                if response.status_code == 200:
                    result = response.json()
                    if 'choices' in result and len(result['choices']) > 0:
                        if model_name != models_to_try[0]:
                            print(f"   Fallback 모델 사용: {model_name}")
                        return result['choices'][0]['message']['content'], model_name
                elif response.status_code == 503 or response.status_code == 429:
                    # 서버 오류 또는 할당량 초과 - 재시도
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"   서버 오류 ({response.status_code}) - {wait_time}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"   모델 {model_name} 재시도 실패 - 다음 모델 시도")
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
                    print(f"   모델 {model_name} 호출 실패: {str(e)}")
                    break
    
    print(f"[ERROR] 모든 OpenAI 모델 시도 실패")
    return None, None

def call_grok_api(api_key, prompt, preferred_model=None):
    """Grok API를 호출합니다. 사용된 모델명을 반환합니다."""
    import time
    
    # grok-4 모델 우선 사용
    possible_models = [
        "grok-4",  # grok-4 기본 모델 (최우선)
        "grok-4-1-fast-reasoning",  # grok-4 최신 버전 (2025년 11월)
        "grok-4-1-fast-non-reasoning",  # grok-4 최신 버전 (2025년 11월)
        "grok-4-fast-reasoning",  # grok-4 (2025년 9월)
        "grok-4-fast-non-reasoning",  # grok-4 (2025년 9월)
        "grok-4-0709",  # grok-4 (2025년 7월)
        "grok-3",  # 폴백
        "grok-3-mini",  # 폴백
        "grok-3-beta",  # 폴백
        "grok-code-fast-1",  # 코드 전용
        "grok-2-image-1212",  # 폴백
        "grok-2-vision-1212",  # 폴백
    ]
    
    # 사용자가 지정한 모델이 있으면 최우선
    if preferred_model:
        if preferred_model in possible_models:
            possible_models.remove(preferred_model)
        possible_models.insert(0, preferred_model)
    
    # Grok API 엔드포인트 (xAI API 사용)
    base_url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    last_error = None
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
        
        # 최대 3번 재시도
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(base_url, headers=headers, json=data, timeout=180)
                if response.status_code == 200:
                    result = response.json()
                    if 'choices' in result and len(result['choices']) > 0:
                        print(f"   Grok 모델 사용: {model_name}")
                        return result['choices'][0]['message']['content'], model_name
                elif response.status_code == 404:
                    # 모델을 찾을 수 없음 - 다음 모델 시도
                    last_error = f"모델 {model_name}을 찾을 수 없음 (404)"
                    break
                elif response.status_code == 403:
                    # 권한 오류 - 에러 메시지 출력 후 종료
                    error_detail = response.text
                    try:
                        error_json = response.json()
                        if 'error' in error_json:
                            last_error = f"권한 오류 (403): {error_json['error']}"
                        else:
                            last_error = f"권한 오류 (403): {error_detail[:200]}"
                    except:
                        last_error = f"권한 오류 (403): {error_detail[:200]}"
                    
                    if model_name == possible_models[-1]:
                        print(f"[ERROR] Grok API 권한 오류 (403)")
                        print(f"   시도한 모델: {model_name}")
                        print(f"   에러: {last_error}")
                        print(f"   모든 모델 시도 실패. xAI 공식 문서에서 최신 모델명을 확인하세요.")
                        print(f"   또는 크레딧이 충분한지 확인하세요: https://console.x.ai/")
                        return None, None
                    break
                elif response.status_code == 503 or response.status_code == 429:
                    # 서버 오류 또는 할당량 초과 - 재시도
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"   서버 오류 ({response.status_code}) - {wait_time}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        last_error = f"서버 오류 ({response.status_code}) - 재시도 실패"
                        print(f"   모델 {model_name} 재시도 실패 - 다음 모델 시도")
                        break
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    response.raise_for_status()
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"   네트워크 오류 - {wait_time}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    last_error = f"네트워크 오류: {str(e)}"
                    if model_name == possible_models[-1]:
                        print(f"[ERROR] Grok API 호출 실패: {str(e)}")
                        print(f"   참고: Grok API 엔드포인트나 모델명이 변경되었을 수 있습니다.")
                        print(f"   xAI 공식 문서 확인: https://docs.x.ai/")
                    break
            except Exception as e:
                last_error = f"예외 발생: {str(e)}"
                if model_name == possible_models[-1]:
                    print(f"[ERROR] Grok API 예외 발생: {str(e)}")
                    import traceback
                    print(f"   상세: {traceback.format_exc()[:500]}")
                break
    
    if last_error:
        print(f"[WARNING] Grok API 호출 실패: {last_error}")
    return None, None

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
    """OpenAI에게 보낼 수정 프롬프트를 생성합니다."""
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

def parse_arguments():
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='포트폴리오 보고서 협업 생성 스크립트 (OpenAI + Grok)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 기본 사용
  python generate_portfolio_report_openai_grok.py
  
  # 모델 지정
  python generate_portfolio_report_openai_grok.py --openai-model gpt-4-turbo --grok-model grok-3
  
  # 프롬프트 파일 및 출력 파일 지정
  python generate_portfolio_report_openai_grok.py --prompt-file my_prompt.txt --output-file my_report.md
        """
    )
    
    parser.add_argument(
        '--openai-model',
        type=str,
        default='gpt-5.2',
        help='OpenAI 모델 지정 (기본값: gpt-5.2)'
    )
    
    parser.add_argument(
        '--grok-model',
        type=str,
        default='grok-4',
        help='Grok 모델 지정 (기본값: grok-4)'
    )
    
    parser.add_argument(
        '--prompt-file',
        type=str,
        default=None,
        help='프롬프트 파일 경로 (기본값: prompts/config.json의 portfolio_prompt_file)'
    )
    
    parser.add_argument(
        '--output-file',
        type=str,
        default=None,
        help='결과 파일 경로 (기본값: 자동 생성)'
    )
    
    return parser.parse_args()

def main():
    """메인 함수"""
    args = parse_arguments()
    if args.prompt_file is None:
        args.prompt_file = get_default_prompt_file()
    
    print("=" * 60)
    print("포트폴리오 보고서 협업 생성 스크립트 (OpenAI + Grok)")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 설정 정보 출력
    print("\n[설정]")
    print(f"  OpenAI 모델: {args.openai_model or 'gpt-5.2 (기본값)'}")
    print(f"  Grok 모델: {args.grok_model or 'grok-4 (기본값)'}")
    print(f"  프롬프트 파일: {args.prompt_file}")
    print(f"  출력 파일: {args.output_file or '자동 생성'}")
    
    # 환경 변수 로드
    print("\n[1/5] 환경 변수 로드 중...")
    openai_key, grok_key = load_env()
    print("[OK] API 키 로드 완료")
    
    # 프롬프트 파일 읽기
    print(f"\n[2/5] 프롬프트 파일 읽는 중: {args.prompt_file}")
    portfolio_prompt = read_portfolio_prompt(args.prompt_file)
    print("[OK] 파일 읽기 완료")
    
    # Step 1: OpenAI가 초안 작성
    print("\n[3/5] OpenAI가 보고서 초안 작성 중...")
    initial_prompt = create_initial_prompt(portfolio_prompt)
    draft_result = call_openai_api(openai_key, initial_prompt, preferred_model=args.openai_model)
    
    if draft_result[0] is None:
        print("[ERROR] 초안 작성 실패")
        return 1
    
    draft_report, openai_model_draft = draft_result
    print(f"[OK] 초안 작성 완료 ({len(draft_report)} 문자)")
    
    # Step 2: Grok이 리뷰
    print("\n[4/5] Grok이 초안 리뷰 중...")
    review_prompt = create_review_prompt(draft_report, portfolio_prompt)
    # Grok 모델 지정 (기본값: grok-4)
    grok_model_to_use = args.grok_model if args.grok_model else 'grok-4'
    review_result = call_grok_api(grok_key, review_prompt, preferred_model=grok_model_to_use)
    
    review_comments = review_result[0]
    grok_model = review_result[1]
    
    if not review_comments:
        print("[WARNING] Grok 리뷰 실패 - 초안을 그대로 사용합니다.")
        review_comments = "리뷰를 받지 못했습니다."
        final_report = draft_report
        openai_model_final = openai_model_draft
    else:
        print(f"[OK] 리뷰 완료 ({len(review_comments)} 문자)")
        
        # Step 3: OpenAI가 리뷰 반영하여 최종 보고서 작성
        print("\n[5/5] OpenAI가 리뷰 반영하여 최종 보고서 작성 중...")
        revision_prompt = create_revision_prompt(draft_report, review_comments, portfolio_prompt)
        final_result = call_openai_api(openai_key, revision_prompt, preferred_model=args.openai_model)
        
        if final_result[0] is None:
            print("[WARNING] 최종 보고서 작성 실패 - 초안을 사용합니다.")
            final_report = draft_report
            openai_model_final = openai_model_draft
        else:
            final_report, openai_model_final = final_result
    
    # 보고서 파일명 생성 (모델 정보 포함)
    report_filename, report_path = generate_report_filename(
        openai_model_final, 
        grok_model, 
        output_file=args.output_file
    )
    
    if report_path.exists():
        print(f"\n[WARNING] {report_filename} 파일이 이미 존재합니다.")
        print("   자동 모드: 기존 파일을 덮어씁니다.")
    
    # 보고서 저장
    now = datetime.now()
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 위웨이크 주식회사 포트폴리오 보고서 (OpenAI + Grok 협업)\n")
        f.write(f"**작성일: {now.strftime('%Y년 %m월 %d일 %H시 %M분')} (어제 종가 기준: {(now - timedelta(days=1)).strftime('%Y년 %m월 %d일')})**\n\n")
        f.write(f"**사용 모델:**\n")
        f.write(f"- OpenAI: `{openai_model_final or 'N/A'}`\n")
        f.write(f"- Grok: `{grok_model or 'N/A'}`\n\n")
        f.write("---\n\n")
        f.write("## 최종 보고서\n\n")
        f.write(final_report)
        f.write("\n\n---\n\n")
        f.write("## 리뷰 과정 (참고용)\n\n")
        f.write("### 초안 (OpenAI 작성)\n\n")
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
