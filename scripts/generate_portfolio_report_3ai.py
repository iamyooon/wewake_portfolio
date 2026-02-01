#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포트폴리오 보고서 3-AI 협업 생성 스크립트 (Grok + Gemini + OpenAI)
성장률 합의 프로세스: Grok(1차 예측) → Gemini(2차 예측) → GPT(최종 결정)
1. 환율·미국주가 API 조회 (exchangerate.host + yfinance)
2. Grok: 데이터 분석관, Alpha CAGR 예측 + 초안 작성 (web_search)
3. Gemini: 리스크 감사관, Beta CAGR 예측 + 감사 (Google Search)
4. OpenAI: 수석 매니저, Alpha/Beta 대조 후 최종 CAGR 확정 및 보고서 완성

사용법:
    python generate_portfolio_report_3ai.py [옵션]

옵션:
    --openai-model MODEL     OpenAI 모델 지정 (기본값: gpt-5.2)
    --grok-model MODEL       Grok 모델 지정 (기본값: grok-4-1-fast-reasoning)
    --gemini-model MODEL     Gemini 모델 지정 (기본값: gemini-3-flash-preview)
    --prompt-file FILE        프롬프트 파일 경로 (기본값: portfolio_prompt.txt)
    --output-file FILE        결과 파일 경로 (기본값: 자동 생성)
    --no-grok-web-search     Grok web_search 비활성화
    --test-stock-price       주가 실시간 조회 테스트만 실행
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import requests
import time

# yfinance 임포트 (없으면 설치 필요: pip install yfinance)
try:
    import yfinance as yf
    import pandas as pd
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[WARNING] yfinance 미설치. 미국 주가 조회 불가. 설치: pip install yfinance pandas")

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
REPORTS_DIR = PROJECT_ROOT
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# 시스템 프롬프트 파일명 (prompts/ 폴더 내)
PROMPT_FILE_GROK = "step1_grok_system.md"
PROMPT_FILE_GEMINI = "step2_gemini_system.md"
PROMPT_FILE_OPENAI = "step3_openai_system.md"

def load_system_prompt(step_key):
    """prompts/ 폴더의 MD 파일에서 시스템 프롬프트를 읽는다. step_key: 'grok'|'gemini'|'openai'. 실패 시 None."""
    name_map = {"grok": PROMPT_FILE_GROK, "gemini": PROMPT_FILE_GEMINI, "openai": PROMPT_FILE_OPENAI}
    filename = name_map.get(step_key)
    if not filename:
        return None
    path = PROMPTS_DIR / filename
    try:
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                return text
    except Exception as e:
        print(f"[WARNING] 시스템 프롬프트 로드 실패 ({filename}): {e}")
    return None

# MD 파일 없을 때 사용할 최소 폴백 (prompts/ 파일이 없어도 동작)
FALLBACK_GROK_SYSTEM = "너는 '위웨이크 주식회사'의 데이터 분석관이다. 전 종목 테이블화, web_search로 환율·종가 반영, Alpha CAGR 산출. 출력 하단에 JSON 포함: {\"alpha_cagr\": 0.0, \"current_total_krw\": 0, \"market_data\": {}}"
FALLBACK_GEMINI_SYSTEM = "너는 '위웨이크 주식회사'의 리스크 감사관이다. Grok 초안·Alpha 검토, Beta CAGR 산출(보수적). 출력 하단에 JSON 포함: {\"beta_cagr\": 0.0, \"risk_level\": \"low/mid/high\", \"audit_notes\": \"...\"}"
FALLBACK_OPENAI_SYSTEM = "너는 '위웨이크 주식회사'의 수석 포트폴리오 매니저다. Alpha·Beta 대조 후 최종 CAGR 확정, 전 종목 포함, 복리 저해 효과 경고. HTML 금지, 등락 기호·볼드만 사용."

def fetch_usd_krw_rate():
    """exchangerate.host API로 USD/KRW 환율 조회. 실패 시 None 반환."""
    try:
        url = "https://api.exchangerate.host/latest?base=USD&symbols=KRW"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            rate = data.get('rates', {}).get('KRW')
            if rate:
                return round(rate, 2)
    except Exception as e:
        print(f"[WARNING] 환율 조회 실패: {str(e)}")
    return None

def fetch_us_stock_prices(tickers):
    """yfinance로 미국 주식 가격 조회. 딕셔너리 {ticker: {prices}} 반환. 실패 시 빈 dict."""
    if not YFINANCE_AVAILABLE:
        return {}
    try:
        result = {}
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                prices = {}
                # 프리마켓 (장 시작 전)
                if 'preMarketPrice' in info and info['preMarketPrice']:
                    prices['pre'] = round(info['preMarketPrice'], 2)
                
                # 정규장 종가
                if 'regularMarketPrice' in info and info['regularMarketPrice']:
                    prices['regular'] = round(info['regularMarketPrice'], 2)
                elif 'currentPrice' in info and info['currentPrice']:
                    prices['regular'] = round(info['currentPrice'], 2)
                
                # 애프터마켓 (장 마감 후)
                if 'postMarketPrice' in info and info['postMarketPrice']:
                    prices['post'] = round(info['postMarketPrice'], 2)
                
                if prices:
                    result[ticker] = prices
            except Exception as e:
                print(f"[WARNING] {ticker} 조회 실패: {str(e)}")
                continue
        
        return result
    except Exception as e:
        print(f"[WARNING] 미국 주가 조회 실패: {str(e)}")
        return {}

def load_env():
    """환경 변수 로드 (.env 파일에서)"""
    if ENV_FILE.exists():
        encodings = ['utf-8-sig', 'utf-8', 'cp949', 'latin-1']  # utf-8-sig 먼저 (BOM 제거)
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
                    key = key.strip().lstrip('\ufeff')  # BOM 제거
                    os.environ[key] = value.strip()
    
    openai_key = os.environ.get('OPENAI_API_KEY')
    grok_key = os.environ.get('GROK_API_KEY')
    gemini_key = os.environ.get('GEMINI_API_KEY')
    
    if not openai_key:
        print("[ERROR] OPENAI_API_KEY가 설정되지 않았습니다.")
        print(f"   {ENV_FILE} 파일에 OPENAI_API_KEY=your-key 형식으로 설정하세요.")
        sys.exit(1)
    
    if not grok_key:
        print("[ERROR] GROK_API_KEY가 설정되지 않았습니다.")
        print(f"   {ENV_FILE} 파일에 GROK_API_KEY=your-key 형식으로 설정하세요.")
        sys.exit(1)
    
    if not gemini_key:
        print("[ERROR] GEMINI_API_KEY가 설정되지 않았습니다.")
        print(f"   {ENV_FILE} 파일에 GEMINI_API_KEY=your-key 형식으로 설정하세요.")
        sys.exit(1)
    
    return openai_key, grok_key, gemini_key

def read_portfolio_prompt(prompt_file_path):
    """프롬프트 파일을 읽어옵니다."""
    try:
        prompt_path = Path(prompt_file_path)
        if not prompt_path.is_absolute():
            prompt_path = PROJECT_ROOT / prompt_path
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] 프롬프트 파일을 찾을 수 없습니다: {prompt_path}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 프롬프트 파일 읽기 실패: {str(e)}")
        sys.exit(1)

def generate_report_filename(openai_model=None, grok_model=None, gemini_model=None, output_file=None):
    """보고서 파일명을 생성합니다."""
    if output_file:
        output_path = Path(output_file)
        if not output_path.is_absolute():
            output_path = REPORTS_DIR / output_path
        return output_path.name, output_path
    
    # 자동 생성
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    time_str = today.strftime("%H%M")
    
    model_parts = []
    if openai_model:
        openai_model_clean = openai_model.replace('-', '').replace('_', '')
        model_parts.append(f"openai-{openai_model_clean}")
    if grok_model:
        grok_model_clean = grok_model.replace('_', '-')
        model_parts.append(f"grok-{grok_model_clean}")
    if gemini_model:
        gemini_model_clean = gemini_model.replace('_', '-')
        model_parts.append(f"gemini-{gemini_model_clean}")
    
    model_suffix = "_".join(model_parts) if model_parts else "3ai"
    
    filename = f"portfolio_report_{date_str}_{time_str}_{model_suffix}.md"
    filepath = REPORTS_DIR / filename
    return filename, filepath

def create_initial_prompt(portfolio_prompt_content, usd_krw_rate=None, us_stock_prices=None):
    """초기 프롬프트를 생성합니다. 환율·미국주가를 주입합니다."""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    date_str = today.strftime("%Y년 %m월 %d일")
    yesterday_str = yesterday.strftime("%Y년 %m월 %d일")
    yesterday_iso = yesterday.strftime("%Y-%m-%d")
    
    # 실시간 데이터 블록 생성
    realtime_data = "\n\n## [제공된 실시간 데이터 - 반드시 이 값을 사용할 것]\n\n"
    
    if usd_krw_rate:
        realtime_data += f"**USD/KRW 환율** ({yesterday_iso} 기준): **{usd_krw_rate}원**\n"
        realtime_data += "- 위 환율을 그대로 사용하세요. 별도로 검색하지 마세요.\n\n"
    else:
        realtime_data += f"**USD/KRW 환율**: 조회 실패 → 웹 검색으로 {yesterday_iso} 환율을 찾으세요.\n\n"
    
    if us_stock_prices:
        realtime_data += f"**미국 주식 가격** (최신 조회):\n"
        for ticker, prices in us_stock_prices.items():
            realtime_data += f"- {ticker}:\n"
            if 'pre' in prices:
                realtime_data += f"  • 프리마켓: ${prices['pre']}\n"
            if 'regular' in prices:
                realtime_data += f"  • 정규장: ${prices['regular']}\n"
            if 'post' in prices:
                realtime_data += f"  • 애프터마켓: ${prices['post']}\n"
        realtime_data += "\n위 주가를 그대로 사용하세요. 가장 최근 가격(애프터마켓 > 정규장 > 프리마켓)을 우선 사용하세요.\n\n"
    else:
        realtime_data += "**미국 주식 가격**: 조회 실패 → 웹 검색으로 찾으세요.\n\n"
    
    realtime_data += f"**한국 주식 종가** (SK하이닉스, 삼성전자, 풍산, 파마리서치): 웹 검색으로 {yesterday_iso} 종가를 찾으세요.\n"
    
    # Step 1 전용: 데이터 분석관 역할 — 전 종목 테이블화, 실시간 데이터 반영, Alpha CAGR 산출
    prompt = f"""[Step 1 - 데이터 분석관용] 아래 포트폴리오 전 종목을 누락 없이 테이블화하고, web_search로 실시간 환율·종가를 반영한 뒤, Alpha 성장률 예측(출력 하단 JSON 포함)을 수행하라.

작성일: {date_str} (어제 종가 기준: {yesterday_str})
{realtime_data}

---
**포트폴리오 및 운영 지침 (참고)**:
{portfolio_prompt_content}
---

**보고서 초안 구조:** 1) 포트폴리오 운영 목표 2) 어제 기준 마켓 현황(실시간 환율, 종목 등락, 리스크) 3) 어제 기준 자산 현황표(전 종목) 4) 목표 달성 로드맵 점검 5) 정리 코멘트. 마크다운 형식, 모든 섹션 포함.
**중요:** [제공된 실시간 데이터]의 환율·미국주가는 그대로 사용하고, 한국 주가는 웹 검색하라.
**Alpha 성장률 예측:** 포트폴리오 구성과 실시간 시장 센티먼트를 결합하여 예상 CAGR(Alpha)를 산출하고, 산출 근거를 데이터로 제시하라.
**출력 하단에 반드시 다음 JSON을 포함하라:** {{"alpha_cagr": 0.0, "current_total_krw": 0, "market_data": {{...}}}}
"""
    return prompt

def parse_alpha_json(text):
    """Grok 출력에서 Alpha CAGR JSON을 추출. alpha_cagr, current_total_krw, market_data 반환."""
    if not text:
        return None, None, None
    # ```json ... ``` 또는 마지막 {...} 블록 찾기
    for pattern in (r'```(?:json)?\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\s*```', r'(\{"alpha_cagr"\s*:\s*[^}]+\})'):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1).strip())
                return (
                    data.get("alpha_cagr"),
                    data.get("current_total_krw"),
                    data.get("market_data")
                )
            except (json.JSONDecodeError, TypeError):
                pass
    # 단순 alpha_cagr 숫자만 찾기
    m = re.search(r'"alpha_cagr"\s*:\s*([\d.]+)', text)
    if m:
        try:
            return float(m.group(1)), None, None
        except ValueError:
            pass
    return None, None, None

def parse_beta_json(text):
    """Gemini 출력에서 Beta CAGR JSON을 추출. beta_cagr, risk_level, audit_notes 반환."""
    if not text:
        return None, None, None
    for pattern in (r'```(?:json)?\s*(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})\s*```', r'(\{"beta_cagr"\s*:\s*[^}]+\})'):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1).strip())
                return (
                    data.get("beta_cagr"),
                    data.get("risk_level"),
                    data.get("audit_notes")
                )
            except (json.JSONDecodeError, TypeError):
                pass
    m = re.search(r'"beta_cagr"\s*:\s*([\d.]+)', text)
    if m:
        try:
            return float(m.group(1)), None, None
        except ValueError:
            pass
    return None, None, None

# Chat Completions이 아닌 Responses API(v1/responses)를 써야 하는 모델 (Thinking/Reasoning 지원)
OPENAI_RESPONSES_API_MODELS = ("gpt-5.2", "gpt-5.2-2025-12-11", "gpt-5.2-pro", "gpt-5.2-pro-2025-12-11")

def _openai_responses_api(api_key, prompt, model_name, instructions=None, max_retries=3):
    """Responses API(v1/responses)로 호출. input + instructions 사용."""
    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # gpt-5.2 / gpt-5.2-pro 계열: reasoning_effort로 Thinking 강도 조절 (수석 매니저 의사결정용)
    body = {
        "model": model_name,
        "input": prompt,
        "max_output_tokens": 16000,
    }
    if instructions:
        body["instructions"] = instructions
    # reasoning_effort: medium — 복리 페널티 등 논리 계산 (API 지원 모델만 적용)
    body["reasoning"] = {"effort": "medium"}
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=body, timeout=300)
            if response.status_code == 400 and "reasoning" in body:
                body = {k: v for k, v in body.items() if k != "reasoning"}
                response = requests.post(url, headers=headers, json=body, timeout=300)
            if response.status_code != 200:
                return (None, response.status_code, response.text)
            result = response.json()
            # output: [{ "type": "message", "role": "assistant", "content": [{ "type": "output_text", "text": "..." }] }]
            for item in result.get("output") or []:
                if item.get("type") == "message" and item.get("role") == "assistant":
                    for c in item.get("content") or []:
                        if c.get("type") == "output_text" and c.get("text"):
                            return (c["text"], model_name, None)
            return (None, 200, "output_text not found")
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep((attempt + 1) * 2)
                continue
            return (None, 0, str(e))
    return (None, 0, "max_retries")

def call_openai_api(api_key, prompt, preferred_model=None, system_content=None):
    """OpenAI API를 호출합니다. gpt-5.2-pro 계열은 v1/responses, 나머지는 v1/chat/completions."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    instructions = system_content if system_content is not None else "당신은 전문적인 포트폴리오 매니저입니다. 정확하고 상세한 포트폴리오 보고서를 작성합니다."
    
    # 기본(gpt-5.2)보다 비싼 폴백은 사용하지 않음 (5.2-pro 제외)
    models_to_try = [
        'gpt-5.2',
        'gpt-5.2-2025-12-11',
        'gpt-4o',
        'gpt-4-turbo',
        'gpt-4',
        'gpt-3.5-turbo',
    ]
    
    if preferred_model:
        if preferred_model in models_to_try:
            models_to_try.remove(preferred_model)
        models_to_try.insert(0, preferred_model)
    
    chat_data_template = {
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 16000
    }
    
    for model_name in models_to_try:
        # gpt-5.2-pro 계열은 Responses API 사용
        if model_name in OPENAI_RESPONSES_API_MODELS:
            text, status_or_name, err = _openai_responses_api(api_key, prompt, model_name, instructions=instructions)
            if text is not None:
                if model_name != models_to_try[0]:
                    print(f"   Fallback 모델 사용: {model_name}")
                return text, model_name
            # 실패 시 다음 모델로 (원인 출력)
            if status_or_name == 404:
                print(f"   [404] Responses API URL: https://api.openai.com/v1/responses")
                print(f"   [404] 응답 본문: {err}")
            elif status_or_name != 200:
                print(f"   [Responses API] {model_name} 실패: HTTP {status_or_name} - {str(err)[:200]}")
            continue
        
        # 나머지는 Chat Completions
        url = "https://api.openai.com/v1/chat/completions"
        data = {**chat_data_template, "model": model_name}
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=180)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('choices') and len(result['choices']) > 0:
                        if model_name != models_to_try[0]:
                            print(f"   Fallback 모델 사용: {model_name}")
                        return result['choices'][0]['message']['content'], model_name
                elif response.status_code == 404:
                    print(f"   [404] 요청 URL: {url}")
                    print(f"   [404] 응답 본문: {response.text}")
                    break
                elif response.status_code in (503, 429):
                    if attempt < max_retries - 1:
                        time.sleep((attempt + 1) * 2)
                        continue
                    break
                else:
                    response.raise_for_status()
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                print(f"   모델 {model_name} 호출 실패: {str(e)}")
                break
    
    print("[ERROR] 모든 OpenAI 모델 시도 실패")
    return None, None

def _grok_responses_api_with_web_search(api_key, prompt, preferred_model=None, system_content=None):
    """Grok Responses API (/v1/responses) + web_search 도구로 호출. 실패 시 (None, None) 반환."""
    # 도구 호출 지원 모델 (xAI 문서 기준)
    # 기본(4.1-fast-reasoning)보다 비싼 폴백 미사용 (grok-4, 4-0709 제외)
    base_models = [
        "grok-4-1-fast-reasoning",
        "grok-4-1-fast",
        "grok-4-1-fast-non-reasoning",
        "grok-4-fast-reasoning",
        "grok-4-fast",
        "grok-4-fast-non-reasoning",
        "grok-3",
        "grok-3-mini",
    ]
    web_search_models = list(base_models)
    if preferred_model:
        if preferred_model in web_search_models:
            web_search_models.remove(preferred_model)
        web_search_models.insert(0, preferred_model)
    default_system = FALLBACK_GROK_SYSTEM
    system_text = system_content if system_content is not None else default_system
    url = "https://api.x.ai/v1/responses"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    for model_name in web_search_models:
        body = {
            "model": model_name,
            "input": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": prompt}
            ],
            "max_output_tokens": 8000,
            "temperature": 0.2,
            "tools": [{"type": "web_search"}]
        }
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=300)
            if resp.status_code != 200:
                if resp.status_code in (404, 400, 422):
                    break
                continue
            result = resp.json()
            for item in (result.get("output") or []):
                if item.get("type") == "message" and item.get("role") == "assistant":
                    for c in (item.get("content") or []):
                        if c.get("type") == "output_text" and c.get("text"):
                            print(f"   Grok 모델 사용 (web_search): {model_name}")
                            return c["text"], model_name
            break
        except requests.exceptions.RequestException:
            continue
    return None, None

def call_grok_api(api_key, prompt, preferred_model=None, use_web_search=True, system_content=None):
    """Grok API를 호출합니다. use_web_search=True이면 Responses API+web_search 시도 후 실패 시 Chat Completions로 폴백."""
    if use_web_search:
        content, model_name = _grok_responses_api_with_web_search(api_key, prompt, preferred_model, system_content=system_content)
        if content is not None:
            return content, model_name
    # 폴백: Chat Completions (검색 도구 없음)
    # Chat Completions 폴백: 기본보다 비싼 4/4-0709 제외
    possible_models = [
        "grok-4-1-fast-reasoning",
        "grok-4-1-fast-non-reasoning",
        "grok-4-fast-reasoning",
        "grok-4-fast-non-reasoning",
        "grok-3",
        "grok-3-mini",
    ]
    if preferred_model:
        if preferred_model in possible_models:
            possible_models.remove(preferred_model)
        possible_models.insert(0, preferred_model)
    base_url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    for model_name in possible_models:
        system_text = system_content if system_content is not None else FALLBACK_GROK_SYSTEM
        data = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_text},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 8000
        }
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
                    break
                elif response.status_code == 403:
                    if model_name == possible_models[-1]:
                        print(f"[ERROR] Grok API 권한 오류 (403)")
                        return None, None
                    break
                elif response.status_code == 503 or response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"   서버 오류 ({response.status_code}) - {wait_time}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
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
                    break
    print(f"[ERROR] 모든 Grok 모델 시도 실패")
    return None, None

def call_gemini_api(api_key, prompt, preferred_model=None, system_content=None):
    """Gemini API를 호출합니다. 사용된 모델명을 반환합니다. system_content는 리스크 감사관 등 역할 지시용."""
    # 기본(3-flash)보다 비싼 폴백 미사용 (2.5-pro, 3-pro 계열 제외)
    possible_models = [
        'gemini-3-flash-preview',
        'gemini-3-flash',
        'gemini-2.5-flash',
        'gemini-pro',
    ]
    
    if preferred_model:
        if preferred_model in possible_models:
            possible_models.remove(preferred_model)
        possible_models.insert(0, preferred_model)
    
    base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    headers = {"Content-Type": "application/json"}
    
    for model_name in possible_models:
        url = f"{base_url}/{model_name}:generateContent?key={api_key}"
        
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8000},
            "tools": [{"google_search": {}}]
        }
        if system_content:
            data["systemInstruction"] = {"parts": [{"text": system_content}]}
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=180)
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        content = result['candidates'][0]['content']['parts'][0]['text']
                        print(f"   Gemini 모델 사용: {model_name}")
                        return content, model_name
                elif response.status_code == 400:
                    # 모델을 찾을 수 없음 - 다음 모델 시도
                    break
                elif response.status_code == 503 or response.status_code == 429:
                    # 폴백 시 원인 확인용: 요청 URL(키 제외), 호출 방식, 응답 전문 출력 및 파일 저장
                    url_without_key = f"{base_url}/{model_name}:generateContent"
                    err_detail = (
                        f"[Gemini {response.status_code}] 요청 URL(키 제외): {url_without_key}\n"
                        f"[Gemini] 호출 방식: Python, requests (공식 SDK 미사용)\n"
                        f"[Gemini] 응답 본문 전문:\n{response.text}"
                    )
                    print(err_detail)
                    try:
                        (REPORTS_DIR / "gemini_last_error.txt").write_text(err_detail, encoding="utf-8")
                    except Exception:
                        pass
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"   서버 오류 ({response.status_code}) - {wait_time}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
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
    
    print(f"[ERROR] 모든 Gemini 모델 시도 실패")
    return None, None

def create_audit_prompt(draft_report, alpha_cagr, portfolio_prompt_content):
    """Gemini(리스크 감사관) 전용: Beta CAGR 감사 프롬프트. 거시 리스크·블랙스완 검색, 보수적 Beta 산출."""
    alpha_str = f"{alpha_cagr}%" if alpha_cagr is not None else "(미제시)"
    prompt = f"""[Step 2 - 리스크 감사관용] 아래 Grok 초안과 Alpha CAGR({alpha_str})을 검토하라. 구글 서칭으로 거시 경제·블랙스완을 확인한 뒤, Grok보다 보수적인 Beta CAGR을 독립 산출하라.

**핵심 임무:**
1. 구글 서칭을 통해 거시 경제 지표(금리, 물가, 지정학적 리스크)를 확인하라.
2. **Beta 성장률 예측:** Grok의 Alpha CAGR({alpha_str})을 비판적으로 검토하고, 거시 리스크를 반영한 **독립적인 예상 CAGR(Beta)**를 산출하라. (Grok보다 보수적인 관점을 유지할 것)
3. 이번 주 블랙스완 요인을 검색하여 리스크 섹션을 작성하라.

**출력 하단에 반드시 다음 JSON을 포함하라:** {{"beta_cagr": 0.0, "risk_level": "low/mid/high", "audit_notes": "..."}}

---

**Grok 초안 (Alpha CAGR 포함)**:
{draft_report}

---

**포트폴리오 참고 (앞 2000자)**:
{portfolio_prompt_content[:2000]}
"""
    return prompt

def create_final_prompt(grok_draft, alpha_cagr, gemini_audit_text, beta_cagr, portfolio_prompt_content):
    """OpenAI(수석 매니저) 전용: Alpha·Beta 대조 후 최종 CAGR 확정, 2030년 25억 냉정 평가, 복리 저해 효과 경고."""
    alpha_str = f"{alpha_cagr}%" if alpha_cagr is not None else "(미제시)"
    beta_str = f"{beta_cagr}%" if beta_cagr is not None else "(미제시)"
    prompt = f"""[Step 3 - 수석 매니저용] Alpha({alpha_str})와 Beta({beta_str})를 비교하여 최종 전략적 CAGR을 결정하고, 2030년 25억 목표 달성 가능성을 냉정하게 리포트하라.

**Grok 분석 (Alpha):** Alpha CAGR {alpha_str} / 보고서 초안은 아래 전문.
**Gemini 감사 (Beta):** Beta CAGR {beta_str} / 감사 보고서는 아래 전문.

**지시:** 위웨이크의 '보수적 리스크 중심' 철학에 따라 **가장 합리적이고 안전한 최종 CAGR**을 확정하라. 결정 이유를 Gemini의 비판을 근거로 설명할 것. 전 종목을 단 하나도 누락하지 말고 포함하고, 확정한 최종 CAGR로 로드맵을 작성한 뒤, **월 1,100만 원 인출에 따른 복리 저해 효과(Compounding Penalty)**를 정밀 계산하여 경고하라.

---

**Grok 초안 전문**:
{grok_draft}

---

**Gemini 감사 결과 전문**:
{gemini_audit_text}

---

**포트폴리오 프롬프트 (참고용)**:
{portfolio_prompt_content}
"""
    return prompt

def parse_arguments():
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='포트폴리오 보고서 3-AI 협업 생성 스크립트 (OpenAI + Grok + Gemini)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 기본 사용
  python generate_portfolio_report_3ai.py
  
  # 모델 지정
  python generate_portfolio_report_3ai.py --openai-model gpt-4-turbo --grok-model grok-4 --gemini-model gemini-2.5-pro
  
  # 프롬프트 파일 및 출력 파일 지정
  python generate_portfolio_report_3ai.py --prompt-file my_prompt.txt --output-file my_report.md
        """
    )
    
    parser.add_argument(
        '--openai-model',
        type=str,
        default='gpt-5.2',
        help='OpenAI 모델 지정 (기본값: gpt-5.2, 폴백: gpt-5.2-pro)'
    )
    
    parser.add_argument(
        '--grok-model',
        type=str,
        default='grok-4-1-fast-reasoning',
        help='Grok 모델 지정 (기본값: grok-4-1-fast-reasoning)'
    )
    
    parser.add_argument(
        '--gemini-model',
        type=str,
        default='gemini-3-flash-preview',
        help='Gemini 모델 지정 (기본값: gemini-3-flash-preview, 폴백: gemini-3-pro-preview)'
    )
    
    parser.add_argument(
        '--prompt-file',
        type=str,
        default='portfolio_prompt.txt',
        help='프롬프트 파일 경로 (기본값: portfolio_prompt.txt)'
    )
    
    parser.add_argument(
        '--output-file',
        type=str,
        default=None,
        help='결과 파일 경로 (기본값: 자동 생성)'
    )
    
    parser.add_argument(
        '--test-models',
        action='store_true',
        help='모델명만 검증: 각 AI에 짧은 테스트 프롬프트를 보내 요청/실제 사용 모델명만 출력 후 종료'
    )
    
    parser.add_argument(
        '--list-models',
        action='store_true',
        help='AI별 사용 가능한 모델 목록만 조회 후 종료 (보고서 생성 안 함)'
    )
    parser.add_argument(
        '--no-grok-web-search',
        action='store_true',
        help='Grok 호출 시 web_search 도구 비활성화 (Responses API 대신 Chat Completions만 사용)'
    )
    parser.add_argument(
        '--test-stock-price',
        action='store_true',
        help='세 AI(OpenAI/Grok/Gemini)에 포트폴리오 주가 실시간 조회 테스트 후 응답만 출력 후 종료'
    )
    parser.add_argument(
        '--test-data-fetch',
        action='store_true',
        help='환율·미국주가 API 조회만 테스트 (AI 호출 없이 데이터만 출력 후 종료)'
    )
    
    return parser.parse_args()

# 테스트용 최소 프롬프트 (빠른 응답용)
TEST_PROMPT = "Reply with exactly: OK"

# 주가 실시간 조회 테스트용 프롬프트 (Gemini는 Google Search, Grok은 web_search 사용)
STOCK_PRICE_TEST_PROMPT = """오늘 기준 Tesla(TSLA) 주가를 USD로 알려줘. 
가능하면 현재가 또는 최근 종가 하나의 숫자(예: 450.00)와 "USD"만 짧게 써줘. 
실시간 조회가 불가능하면 "조회 불가"라고만 답해줘."""

def run_test_models(openai_key, grok_key, gemini_key, args):
    """각 AI에 짧은 테스트 프롬프트를 보내 요청 모델 vs 실제 사용 모델만 출력한다."""
    print("\n[모델 검증] 짧은 테스트 프롬프트로 각 AI 호출 중...\n")
    
    results = []
    
    # OpenAI
    print("  OpenAI 호출 중...", end=" ")
    content, actual = call_openai_api(openai_key, TEST_PROMPT, preferred_model=args.openai_model)
    status = "OK" if content else "실패"
    print(status)
    results.append(("OpenAI", args.openai_model, actual or "N/A"))
    
    # Grok
    print("  Grok 호출 중...", end=" ")
    content, actual = call_grok_api(grok_key, TEST_PROMPT, preferred_model=args.grok_model, use_web_search=not args.no_grok_web_search)
    status = "OK" if content else "실패"
    print(status)
    results.append(("Grok", args.grok_model, actual or "N/A"))
    
    # Gemini
    print("  Gemini 호출 중...", end=" ")
    content, actual = call_gemini_api(gemini_key, TEST_PROMPT, preferred_model=args.gemini_model)
    status = "OK" if content else "실패"
    print(status)
    results.append(("Gemini", args.gemini_model, actual or "N/A"))
    
    print("\n" + "=" * 60)
    print("[모델 사용 현황]")
    print("=" * 60)
    for name, requested, actual in results:
        same = " (동일)" if requested == actual else " (폴백)"
        print(f"  {name}:")
        print(f"    요청 모델: {requested}")
        print(f"    실제 사용: {actual}{same}")
    print("=" * 60)
    return 0

def run_test_data_fetch():
    """환율·미국주가 API 조회만 테스트. AI 호출 없음."""
    print("\n[데이터 조회 테스트] 환율·미국주가 API 조회만 실행\n")
    print("=" * 60)
    
    # 환율 조회
    print("\n1. USD/KRW 환율 조회 (exchangerate.host)")
    print("-" * 60)
    usd_krw_rate = fetch_usd_krw_rate()
    if usd_krw_rate:
        print(f"✅ 성공: {usd_krw_rate}원")
    else:
        print("❌ 실패: 환율 조회 불가")
    
    # 미국 주가 조회
    print("\n2. 미국 주가 조회 (yfinance)")
    print("-" * 60)
    us_tickers = ["TSLA", "MAGS", "SMH", "MSTR", "MELI", "NU"]
    print(f"조회 종목: {', '.join(us_tickers)}")
    print()
    
    us_stock_prices = fetch_us_stock_prices(us_tickers)
    if us_stock_prices:
        print(f"✅ 성공: {len(us_stock_prices)}개 종목 조회")
        for ticker, prices in us_stock_prices.items():
            price_parts = []
            if 'pre' in prices:
                price_parts.append(f"프리마켓 ${prices['pre']}")
            if 'regular' in prices:
                price_parts.append(f"정규장 ${prices['regular']}")
            if 'post' in prices:
                price_parts.append(f"애프터마켓 ${prices['post']}")
            print(f"  • {ticker}: {' | '.join(price_parts)}")
    else:
        print("❌ 실패: 주가 조회 불가 (yfinance 미설치 또는 네트워크 오류)")
    
    print("\n" + "=" * 60)
    print("\n[참고] 한국 주가는 AI 검색으로 조회됩니다 (API 없음).")
    print("       종목: SK하이닉스, 삼성전자, 풍산, 파마리서치")
    print("=" * 60)
    return 0

def run_test_stock_price(openai_key, grok_key, gemini_key, args):
    """세 AI에 포트폴리오 주가(TSLA) 실시간 조회 프롬프트를 보내 응답을 출력한다."""
    print("\n[주가 실시간 조회 테스트] TSLA 현재가 요청 → 각 AI 응답 확인\n")
    print("프롬프트:", STOCK_PRICE_TEST_PROMPT.strip()[:80] + "...")
    print()
    max_show = 500  # 응답 길이 제한

    # OpenAI
    print("--- OpenAI ---")
    content, actual = call_openai_api(openai_key, STOCK_PRICE_TEST_PROMPT, preferred_model=args.openai_model)
    if content:
        show = content.strip()[:max_show] + ("..." if len(content) > max_show else "")
        print(show)
        print(f"  (모델: {actual}, 길이: {len(content)}자)")
    else:
        print("  (응답 없음)")
    print()

    # Grok (web_search 사용 시도)
    print("--- Grok ---")
    content, actual = call_grok_api(grok_key, STOCK_PRICE_TEST_PROMPT, preferred_model=args.grok_model, use_web_search=not args.no_grok_web_search)
    if content:
        show = content.strip()[:max_show] + ("..." if len(content) > max_show else "")
        print(show)
        print(f"  (모델: {actual}, 길이: {len(content)}자)")
    else:
        print("  (응답 없음)")
    print()

    # Gemini (Google Search Grounding 사용)
    print("--- Gemini ---")
    content, actual = call_gemini_api(gemini_key, STOCK_PRICE_TEST_PROMPT, preferred_model=args.gemini_model)
    if content:
        show = content.strip()[:max_show] + ("..." if len(content) > max_show else "")
        print(show)
        print(f"  (모델: {actual}, 길이: {len(content)}자)")
    else:
        print("  (응답 없음)")
    print()
    print("=" * 60)
    return 0

def _list_openai_models(api_key):
    """OpenAI API로 사용 가능한 모델 ID 목록 반환."""
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        data = r.json()
        ids = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
        return sorted(ids), None
    except Exception as e:
        return None, str(e)

def _list_grok_models(api_key):
    """Grok(xAI) API로 사용 가능한 모델 목록 반환."""
    url = "https://api.x.ai/v1/models"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        data = r.json()
        ids = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
        return sorted(ids), None
    except Exception as e:
        return None, str(e)

def _list_gemini_models(api_key):
    """Gemini API로 사용 가능한 모델 목록 반환 (generateContent 지원만)."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        data = r.json()
        models = data.get("models", [])
        ids = []
        for m in models:
            if "generateContent" in m.get("supportedGenerationMethods", []):
                name = m.get("name", "")
                if "/" in name:
                    name = name.split("/")[-1]
                if name:
                    ids.append(name)
        return sorted(ids), None
    except Exception as e:
        return None, str(e)

def run_list_models(openai_key, grok_key, gemini_key):
    """AI별 사용 가능한 모델 목록을 조회해 출력한다."""
    print("\n[AI별 사용 가능한 모델 목록]\n")
    
    # OpenAI
    print("OpenAI")
    print("-" * 50)
    ids, err = _list_openai_models(openai_key)
    if err:
        print(f"  조회 실패: {err}")
    elif ids:
        for m in ids:
            print(f"  • {m}")
        print(f"  (총 {len(ids)}개)")
    else:
        print("  (목록 없음)")
    print()
    
    # Grok
    print("Grok (xAI)")
    print("-" * 50)
    ids, err = _list_grok_models(grok_key)
    if err:
        print(f"  조회 실패: {err}")
    elif ids:
        for m in ids:
            print(f"  • {m}")
        print(f"  (총 {len(ids)}개)")
    else:
        print("  (목록 없음)")
    print()
    
    # Gemini
    print("Gemini (Google)")
    print("-" * 50)
    ids, err = _list_gemini_models(gemini_key)
    if err:
        print(f"  조회 실패: {err}")
    elif ids:
        for m in ids:
            print(f"  • {m}")
        print(f"  (총 {len(ids)}개)")
    else:
        print("  (목록 없음)")
    print("=" * 50)
    return 0

def main():
    """메인 함수"""
    args = parse_arguments()
    
    print("=" * 60)
    print("포트폴리오 보고서 3-AI 협업 생성 스크립트")
    print("(OpenAI + Grok + Gemini)")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 환경 변수 로드 (먼저 수행)
    print("\n[1/6] 환경 변수 로드 중...")
    openai_key, grok_key, gemini_key = load_env()
    print("[OK] API 키 로드 완료")
    
    # --test-data-fetch: 환율·주가 API 조회만 테스트 (AI 호출 없음)
    if args.test_data_fetch:
        return run_test_data_fetch()
    # --test-models: 짧은 테스트로 요청/실제 모델명만 출력 후 종료
    if args.test_models:
        return run_test_models(openai_key, grok_key, gemini_key, args)
    # --test-stock-price: 세 AI에 주가 실시간 조회 테스트 후 응답만 출력 후 종료
    if args.test_stock_price:
        return run_test_stock_price(openai_key, grok_key, gemini_key, args)
    # --list-models: AI별 사용 가능한 모델 목록만 조회 후 종료
    if args.list_models:
        return run_list_models(openai_key, grok_key, gemini_key)
    
    print("\n[설정]")
    print(f"  OpenAI 모델: {args.openai_model}")
    print(f"  Grok 모델: {args.grok_model}")
    print(f"  Gemini 모델: {args.gemini_model}")
    print(f"  프롬프트 파일: {args.prompt_file}")
    print(f"  출력 파일: {args.output_file or '자동 생성'}")
    
    # 프롬프트 파일 읽기
    print(f"\n[2/6] 프롬프트 파일 읽는 중: {args.prompt_file}")
    portfolio_prompt = read_portfolio_prompt(args.prompt_file)
    print("[OK] 파일 읽기 완료")
    
    # 실시간 데이터 조회 (환율 + 미국 주가)
    print("\n[2.5/6] 실시간 데이터 조회 중...")
    usd_krw_rate = fetch_usd_krw_rate()
    if usd_krw_rate:
        print(f"  USD/KRW 환율: {usd_krw_rate}원")
    else:
        print("  USD/KRW 환율: 조회 실패 (AI가 검색으로 대체)")
    
    us_tickers = ["TSLA", "MAGS", "SMH", "MSTR", "MELI", "NU"]
    us_stock_prices = fetch_us_stock_prices(us_tickers)
    if us_stock_prices:
        print(f"  미국 주가: {len(us_stock_prices)}개 조회 성공")
        for ticker, prices in us_stock_prices.items():
            price_str = []
            if 'pre' in prices:
                price_str.append(f"프리 ${prices['pre']}")
            if 'regular' in prices:
                price_str.append(f"정규 ${prices['regular']}")
            if 'post' in prices:
                price_str.append(f"애프터 ${prices['post']}")
            print(f"    {ticker}: {', '.join(price_str)}")
    else:
        print("  미국 주가: 조회 실패 (AI가 검색으로 대체)")
    print("[OK] 데이터 조회 완료")
    
    # Step 1: Grok 1차 예측 (Alpha CAGR) + 초안 작성
    grok_system = load_system_prompt("grok") or FALLBACK_GROK_SYSTEM
    print("\n[3/4] Grok(데이터 분석관) 1차 예측·초안 작성 중 (Alpha CAGR, web_search)...")
    initial_prompt = create_initial_prompt(portfolio_prompt, usd_krw_rate, us_stock_prices)
    draft_result = call_grok_api(grok_key, initial_prompt, preferred_model=args.grok_model, use_web_search=not args.no_grok_web_search, system_content=grok_system)
    
    if draft_result[0] is None:
        print("[ERROR] 초안 작성 실패")
        return 1
    
    draft_report, grok_model = draft_result
    alpha_cagr, current_total_krw, market_data = parse_alpha_json(draft_report)
    if alpha_cagr is not None:
        print(f"  Alpha CAGR: {alpha_cagr}%")
    print(f"[OK] 초안 작성 완료 ({len(draft_report)} 문자)")
    
    # Step 2: Gemini 2차 예측 (Beta CAGR) + 리스크 감사
    gemini_system = load_system_prompt("gemini") or FALLBACK_GEMINI_SYSTEM
    print("\n[4/4] Gemini(리스크 감사관) 2차 예측·감사 중 (Beta CAGR, Google Search)...")
    audit_prompt = create_audit_prompt(draft_report, alpha_cagr, portfolio_prompt)
    audit_result = call_gemini_api(gemini_key, audit_prompt, preferred_model=args.gemini_model, system_content=gemini_system)
    
    audit_comments = audit_result[0] if audit_result[0] else ""
    gemini_model = audit_result[1] if audit_result[1] else None
    beta_cagr, risk_level, audit_notes = parse_beta_json(audit_comments) if audit_comments else (None, None, None)
    
    if not audit_comments:
        print("[WARNING] Gemini 감사 실패 - 최종 단계로 진행합니다.")
        audit_comments = "감사를 받지 못했습니다."
    else:
        if beta_cagr is not None:
            print(f"  Beta CAGR: {beta_cagr}%")
        if risk_level:
            print(f"  리스크 수준: {risk_level}")
    
    print(f"[OK] 감사 완료 ({len(audit_comments)} 문자)")
    
    # Step 3: GPT 최종 결정 (Alpha/Beta 대조 후 최종 CAGR 확정)
    openai_system = load_system_prompt("openai") or FALLBACK_OPENAI_SYSTEM
    print("\n[5/4] OpenAI(수석 매니저) 최종 CAGR 확정·보고서 작성 중...")
    final_prompt = create_final_prompt(draft_report, alpha_cagr, audit_comments, beta_cagr, portfolio_prompt)
    final_result = call_openai_api(openai_key, final_prompt, preferred_model=args.openai_model, system_content=openai_system)
    
    if final_result[0] is None:
        print("[WARNING] 최종 보고서 작성 실패 - 초안을 사용합니다.")
        final_report = draft_report
        openai_model_final = "N/A"
    else:
        final_report, openai_model_final = final_result
        print(f"[OK] 최종 보고서 작성 완료 ({len(final_report)} 문자)")
    
    # 보고서 파일명 생성
    report_filename, report_path = generate_report_filename(
        openai_model_final, 
        grok_model, 
        gemini_model,
        output_file=args.output_file
    )
    
    if report_path.exists():
        print(f"\n[WARNING] {report_filename} 파일이 이미 존재합니다.")
        print("   기존 파일을 덮어씁니다.")
    
    # 보고서 저장
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 위웨이크 주식회사 포트폴리오 보고서 (3-AI 협업)\n")
        f.write(f"**작성일: {now.strftime('%Y년 %m월 %d일 %H시 %M분')} (어제 종가 기준: {yesterday.strftime('%Y년 %m월 %d일')})**\n\n")
        f.write(f"**실시간 데이터:**\n")
        if usd_krw_rate:
            f.write(f"- USD/KRW 환율: {usd_krw_rate}원 ({yesterday.strftime('%Y-%m-%d')} API 조회)\n")
        if us_stock_prices:
            f.write(f"- 미국 주가: {', '.join(us_stock_prices.keys())} ({yesterday.strftime('%Y-%m-%d')} API 조회)\n")
        f.write(f"\n**사용 모델:**\n")
        f.write(f"\n**성장률 합의:** Alpha(Grok) {alpha_cagr or 'N/A'}% → Beta(Gemini) {beta_cagr or 'N/A'}% → GPT 최종 확정\n")
        f.write(f"\n**사용 모델:**\n")
        f.write(f"- Grok (1차 예측·초안): `{grok_model or 'N/A'}`\n")
        f.write(f"- Gemini (2차 예측·감사): `{gemini_model or 'N/A'}`\n")
        f.write(f"- OpenAI (최종 결정): `{openai_model_final or 'N/A'}`\n\n")
        f.write("---\n\n")
        f.write("## 최종 보고서\n\n")
        f.write(final_report)
        f.write("\n\n---\n\n")
        f.write("## 협업 과정 (참고용)\n\n")
        f.write("### 1차 예측·초안 (Grok 작성)\n\n")
        f.write("<details>\n<summary>초안 보기</summary>\n\n")
        f.write(draft_report)
        f.write("\n\n</details>\n\n")
        f.write("### 2차 예측·감사 결과 (Gemini 작성)\n\n")
        f.write(audit_comments)
        f.write("\n\n")
    
    # AI별 요청 모델 vs 실제 사용 모델 출력
    print("\n[모델 사용 현황]")
    print("  Grok (1차 예측·초안):")
    print(f"    요청 모델: {args.grok_model}")
    print(f"    실제 사용: {grok_model or 'N/A'}")
    print("  Gemini (2차 예측·감사):")
    print(f"    요청 모델: {args.gemini_model}")
    print(f"    실제 사용: {gemini_model or 'N/A'}")
    print("  OpenAI (최종 결정):")
    print(f"    요청 모델: {args.openai_model}")
    print(f"    실제 사용: {openai_model_final or 'N/A'}")
    
    print(f"\n[SUCCESS] 3-AI 성장률 합의 보고서 생성 완료: {report_filename}")
    print(f"   파일 위치: {report_path}")
    print(f"   Alpha CAGR: {alpha_cagr or 'N/A'}% | Beta CAGR: {beta_cagr or 'N/A'}%")
    print(f"   최종 보고서 크기: {len(final_report)} 문자")
    print(f"   감사 결과 크기: {len(audit_comments)} 문자")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
