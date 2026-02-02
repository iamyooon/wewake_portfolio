#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포트폴리오 보고서 3-AI 협업 생성 스크립트 (Grok + Gemini + OpenAI)
성장률 합의 프로세스: Grok·Gemini·GPT 각각 Base 시나리오 CAGR 예측 → GPT가 세 Base 비교 후 Bear/Bull 반영해 최종 확정
1. 환율·미국주가 API 조회 (open.er-api.com 무료 → exchangerate.host 키 있으면 보조, yfinance)
2. Grok: 데이터 분석관, Base 시나리오 CAGR 예측 + 초안 작성 (web_search)
3. Gemini: 리스크 감사관, Base 시나리오 CAGR 예측 + 감사 (Google Search)
4. OpenAI: 수석 매니저, 세 Base 비교 후 Bear/Bull 반영해 최종 CAGR 확정 및 보고서 완성

사용법:
    python generate_portfolio_report_3ai.py [옵션]

옵션:
    --openai-model MODEL     OpenAI 모델 지정 (기본값: gpt-5.2)
    --grok-model MODEL       Grok 모델 지정 (기본값: grok-4-1-fast-reasoning)
    --gemini-model MODEL     Gemini 모델 지정 (기본값: gemini-3-flash-preview)
    --prompt-file FILE        프롬프트 파일 경로 (기본값: prompts/config.json의 portfolio_prompt_file)
    --output-file FILE        결과 파일 경로 (기본값: 자동 생성)
    --no-grok-web-search     Grok web_search 비활성화
    --test-stock-price       주가 실시간 조회 테스트만 실행
    --debug-step 1|2|3|4|5   1=Grok R1, 2=+Gemini R1, 3=+Grok R2, 4=+Gemini R2, 5=+OpenAI — 실행 후 해당 AI와 추가 질문 (종료: quit 또는 exit 입력)
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
REPORTS_DIR = PROJECT_ROOT / "report"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# 설정·폴백은 모두 prompts/에서 로드 (config.json, fallback_*_system.md)
CONFIG_FILE = PROMPTS_DIR / "config.json"
FALLBACK_FILES = {"grok": "fallback_grok_system.md", "gemini": "fallback_gemini_system.md", "openai": "fallback_openai_system.md"}

def load_prompts_config():
    """prompts/config.json을 읽는다. 없거나 실패 시 빈 dict."""
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}

def get_default_prompt_file():
    """기본 포트폴리오 프롬프트 경로 (config 기준, 프로젝트 루트 기준 상대 경로)."""
    cfg = load_prompts_config()
    name = (cfg.get("portfolio_prompt_file") or "portfolio_prompt.txt").strip()
    if not name:
        name = "portfolio_prompt.txt"
    return "prompts/" + name if not name.startswith("prompts/") else name

def get_us_tickers():
    """미국 주가 조회용 종목 목록 (config 기준)."""
    cfg = load_prompts_config()
    tickers = cfg.get("us_tickers")
    return list(tickers) if isinstance(tickers, list) else []

def get_stock_price_test_prompt():
    """주가 실시간 조회 테스트용 프롬프트 (config 또는 prompts/stock_price_test_prompt.txt)."""
    cfg = load_prompts_config()
    text = cfg.get("stock_price_test_prompt") if isinstance(cfg.get("stock_price_test_prompt"), str) else None
    if text and text.strip():
        return text.strip()
    path = PROMPTS_DIR / "stock_price_test_prompt.txt"
    try:
        if path.exists():
            t = path.read_text(encoding="utf-8").strip()
            if t:
                return t
    except Exception:
        pass
    return "오늘 기준 미국 주가 하나를 USD로 알려줘. 숫자와 USD만 짧게."

def load_fallback_system(step_key):
    """prompts/fallback_*_system.md에서 폴백 시스템 프롬프트를 읽는다. 없으면 최소 문구."""
    fname = FALLBACK_FILES.get(step_key)
    if fname:
        path = PROMPTS_DIR / fname
        try:
            if path.exists():
                t = path.read_text(encoding="utf-8").strip()
                if t:
                    return t
        except Exception:
            pass
    return "You are an analyst. Output valid JSON when requested."

# 시스템 프롬프트 파일명 (prompts/ 폴더 내)
PROMPT_FILE_GROK = "step1_grok_system.md"
PROMPT_FILE_GEMINI = "step2_gemini_system.md"
PROMPT_FILE_OPENAI = "step3_openai_system.md"
USER_TEMPLATE_GROK = "step1_user_template.md"
USER_TEMPLATE_GEMINI = "step2_user_template.md"
USER_TEMPLATE_OPENAI = "step3_user_template.md"
# 2라운드(협상)용
PROMPT_FILE_GROK_R2 = "step2b_grok_system.md"
PROMPT_FILE_GEMINI_R2 = "step2b_gemini_system.md"
USER_TEMPLATE_GROK_R2 = "step2b_grok_user_template.md"
USER_TEMPLATE_GEMINI_R2 = "step2b_gemini_user_template.md"

def load_system_prompt(step_key):
    """prompts/ 폴더의 MD 파일에서 시스템 프롬프트를 읽는다. step_key: 'grok'|'gemini'|'openai'|'grok_r2'|'gemini_r2'. 실패 시 None."""
    name_map = {
        "grok": PROMPT_FILE_GROK, "gemini": PROMPT_FILE_GEMINI, "openai": PROMPT_FILE_OPENAI,
        "grok_r2": PROMPT_FILE_GROK_R2, "gemini_r2": PROMPT_FILE_GEMINI_R2,
    }
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

def load_user_template(step_key):
    """prompts/ 폴더에서 유저 프롬프트 템플릿을 읽는다. step_key: 'grok'|'gemini'|'openai'|'grok_r2'|'gemini_r2'. 실패 시 None."""
    name_map = {
        "grok": USER_TEMPLATE_GROK, "gemini": USER_TEMPLATE_GEMINI, "openai": USER_TEMPLATE_OPENAI,
        "grok_r2": USER_TEMPLATE_GROK_R2, "gemini_r2": USER_TEMPLATE_GEMINI_R2,
    }
    filename = name_map.get(step_key)
    if not filename:
        return None
    path = PROMPTS_DIR / filename
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[WARNING] 유저 템플릿 로드 실패 ({filename}): {e}")
    return None

def fetch_usd_krw_rate():
    """USD/KRW 환율 조회. 1) open.er-api.com(키 없음) 2) exchangerate.host(키 있으면). 실패 시 None."""
    # 1) ExchangeRate-API Open Access (API 키 불필요, 일 1회 갱신)
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("result") == "success":
                rate = data.get("rates", {}).get("KRW")
                if rate is not None:
                    return round(float(rate), 2)
    except Exception as e:
        print(f"[WARNING] 환율(open.er-api.com) 조회 실패: {str(e)}")
    # 2) exchangerate.host (API 키 필요: EXCHANGERATE_HOST_ACCESS_KEY)
    key = os.environ.get("EXCHANGERATE_HOST_ACCESS_KEY")
    if key:
        try:
            url = f"https://api.exchangerate.host/latest?base=USD&symbols=KRW&access_key={key}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("rates"):
                    rate = data.get("rates", {}).get("KRW")
                    if rate is not None:
                        return round(float(rate), 2)
        except Exception as e:
            print(f"[WARNING] 환율(exchangerate.host) 조회 실패: {str(e)}")
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
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
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
    
    tpl = load_user_template("grok")
    if tpl:
        return tpl.replace("{{date_str}}", date_str).replace("{{yesterday_str}}", yesterday_str).replace("{{realtime_data}}", realtime_data).replace("{{portfolio_prompt_content}}", portfolio_prompt_content)
    # 폴백: 템플릿 파일 없을 때
    return f"""[Step 1 - 데이터 분석관용] 아래 포트폴리오 전 종목을 누락 없이 테이블화하고, web_search로 실시간 환율·종가를 반영한 뒤, Base 시나리오 CAGR 예측(출력 하단 JSON 포함)을 수행하라.

작성일: {date_str} (어제 종가 기준: {yesterday_str})
{realtime_data}

---
**포트폴리오 및 운영 지침 (참고)**:
{portfolio_prompt_content}
---

**보고서 초안 구조:** 1) 포트폴리오 운영 목표 2) 어제 기준 마켓 현황 3) 자산 현황표(전 종목) 4) 목표 달성 로드맵 점검 5) 정리 코멘트. **출력 하단에 JSON 포함:** {{"alpha_cagr": 0.0, "current_total_krw": 0, "market_data": {{...}}}}
"""

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

def call_openai_chat(api_key, messages, preferred_model=None):
    """OpenAI Chat Completions로 대화 히스토리 전달. messages = [{"role":"system"|"user"|"assistant", "content": "..."}, ...]. 디버그용."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    models = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    if preferred_model and preferred_model not in models:
        models.insert(0, preferred_model)
    for model_name in models:
        try:
            r = requests.post(url, headers=headers, json={"model": model_name, "messages": messages, "temperature": 0.7, "max_tokens": 8000}, timeout=120)
            if r.status_code == 200 and r.json().get("choices"):
                return r.json()["choices"][0]["message"]["content"], model_name
        except Exception:
            continue
    return None, None

def call_grok_chat(api_key, messages, preferred_model=None):
    """Grok Chat Completions로 대화 히스토리 전달. 디버그용."""
    base_url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    models = ["grok-4-1-fast-reasoning", "grok-4-1-fast-non-reasoning", "grok-3", "grok-3-mini"]
    if preferred_model and preferred_model not in models:
        models.insert(0, preferred_model)
    for model_name in models:
        try:
            r = requests.post(base_url, headers=headers, json={"model": model_name, "messages": messages, "temperature": 0.2, "max_tokens": 8000}, timeout=120)
            if r.status_code == 200 and r.json().get("choices"):
                return r.json()["choices"][0]["message"]["content"], model_name
        except Exception:
            continue
    return None, None

def call_gemini_chat(api_key, messages, preferred_model=None):
    """Gemini generateContent로 대화 히스토리 전달. messages = [{"role":"user"|"assistant", "content": "..."}, ...]. system은 별도. 디버그용."""
    models = ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-pro"]
    if preferred_model and preferred_model not in models:
        models.insert(0, preferred_model)
    system_text = None
    contents = []
    for m in messages:
        role, content = m.get("role"), m.get("content", "")
        if role == "system":
            system_text = content
            continue
        if role == "user":
            contents.append({"role": "user", "parts": [{"text": content}]})
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})
    for model_name in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            data = {"contents": contents, "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8000}}
            if system_text:
                data["systemInstruction"] = {"parts": [{"text": system_text}]}
            r = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=120)
            if r.status_code == 200 and r.json().get("candidates"):
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return text, model_name
        except Exception:
            continue
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
    default_system = load_fallback_system("grok")
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
        system_text = system_content if system_content is not None else load_fallback_system("grok")
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
                        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
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
    """Gemini(리스크 감사관) 전용: 동일 Base 시나리오 기준 CAGR 예측 프롬프트."""
    alpha_str = f"{alpha_cagr}%" if alpha_cagr is not None else "(미제시)"
    portfolio_2000 = (portfolio_prompt_content or "")[:2000]
    tpl = load_user_template("gemini")
    if tpl:
        return tpl.replace("{{alpha_cagr}}", alpha_str).replace("{{draft_report}}", draft_report).replace("{{portfolio_prompt_content}}", portfolio_2000)
    return f"""[Step 2 - 리스크 감사관용] Grok 초안과 Base CAGR({alpha_str}) 참고, 동일 Base 시나리오 기준으로 독립 CAGR 산출. 출력 하단 JSON: {{"beta_cagr": 0.0, "risk_level": "low/mid/high", "audit_notes": "..."}}

**Grok 초안**:
{draft_report}

**포트폴리오 참고**: 
{portfolio_2000}
"""

def create_grok_r2_prompt(gemini_audit_text):
    """2라운드 Grok용: Gemini 감사·비판을 검토하여 수용/반박만 정리."""
    tpl = load_user_template("grok_r2")
    if tpl:
        return tpl.replace("{{gemini_audit_text}}", (gemini_audit_text or "").strip())
    return f"""[2라운드 - Grok] 아래 Gemini 감사·비판을 검토하라. 수용할 부분은 "수용"으로, 반박할 부분만 반박 내용으로 정리하라.

**Gemini 감사·비판 전문:**
{gemini_audit_text or ''}
"""

def create_gemini_r2_prompt(grok_r2_response):
    """2라운드 Gemini용: Grok의 수용·반박을 검토하여 수용/반박만 정리."""
    tpl = load_user_template("gemini_r2")
    if tpl:
        return tpl.replace("{{grok_r2_response}}", (grok_r2_response or "").strip())
    return f"""[2라운드 - Gemini] 아래 Grok의 수용·반박을 검토하라. 수용할 부분은 "수용"으로, 반박할 부분만 반박 내용으로 정리하라.

**Grok 수용·반박 전문:**
{grok_r2_response or ''}
"""

def create_final_prompt(grok_draft, alpha_cagr, gemini_audit_text, beta_cagr, portfolio_prompt_content, grok_r2=None, gemini_r2=None):
    """OpenAI(수석 매니저) 전용: 세 Base CAGR 비교 + 2라운드 합의·대립 + Bear/Bull 반영 후 최종 CAGR 확정."""
    alpha_str = f"{alpha_cagr}%" if alpha_cagr is not None else "(미제시)"
    beta_str = f"{beta_cagr}%" if beta_cagr is not None else "(미제시)"
    grok_r2_text = (grok_r2 or "").strip()
    gemini_r2_text = (gemini_r2 or "").strip()
    if not grok_r2_text:
        grok_r2_text = "(없음)"
    if not gemini_r2_text:
        gemini_r2_text = "(없음)"
    tpl = load_user_template("openai")
    if tpl:
        out = tpl.replace("{{alpha_cagr}}", alpha_str).replace("{{beta_cagr}}", beta_str)
        out = out.replace("{{grok_draft}}", grok_draft).replace("{{gemini_audit_text}}", gemini_audit_text)
        out = out.replace("{{portfolio_prompt_content}}", portfolio_prompt_content or "")
        out = out.replace("{{grok_r2_response}}", grok_r2_text).replace("{{gemini_r2_response}}", gemini_r2_text)
        return out
    return f"""[Step 3 - 수석 매니저용] Grok Base({alpha_str})·Gemini Base({beta_str})와 자신의 Base 예측을 비교한 뒤 Bear/Bull 반영해 최종 CAGR 확정. 전 종목 포함, 복리 저해 효과 경고.

**Grok 초안**: {grok_draft}

**Gemini 감사**: {gemini_audit_text}

**2라운드 Grok 수용·반박**: {grok_r2_text or '(없음)'}

**2라운드 Gemini 수용·반박**: {gemini_r2_text or '(없음)'}

**포트폴리오 참고**: {portfolio_prompt_content or ""}
"""

def format_elapsed(seconds):
    """소요 시간(초)을 '12.3초' 또는 '1분 23.4초' 형식으로 반환."""
    if seconds < 60:
        return f"{seconds:.1f}초"
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m}분 {s:.1f}초"


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
  python generate_portfolio_report_3ai.py --prompt-file <경로> --output-file my_report.md
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
        default=None,
        help='프롬프트 파일 경로 (기본값: prompts/config.json의 portfolio_prompt_file)'
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
    parser.add_argument(
        '--debug-step',
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=None,
        metavar='1|2|3|4|5',
        help='1~5 단계까지 실행 후 해당 AI와 대화. 대화 중 next/다음 입력 시 다음 단계로 진행. 종료: quit 또는 exit 입력'
    )
    
    return parser.parse_args()

# 테스트용 최소 프롬프트 (빠른 응답용)
TEST_PROMPT = "Reply with exactly: OK"

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
    print("\n1. USD/KRW 환율 조회 (open.er-api.com → exchangerate.host)")
    print("-" * 60)
    usd_krw_rate = fetch_usd_krw_rate()
    if usd_krw_rate:
        print(f"✅ 성공: {usd_krw_rate}원")
    else:
        print("❌ 실패: 환율 조회 불가")
    
    # 미국 주가 조회
    print("\n2. 미국 주가 조회 (yfinance)")
    print("-" * 60)
    us_tickers = get_us_tickers()
    if not us_tickers:
        print("  [참고] prompts/config.json에 us_tickers가 없어 미국 주가 조회를 건너뜁니다.")
    else:
        print(f"조회 종목: {', '.join(us_tickers)}")
    print()
    
    if us_tickers:
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
    print("=" * 60)
    return 0

def run_test_stock_price(openai_key, grok_key, gemini_key, args):
    """세 AI에 주가 실시간 조회 테스트 프롬프트를 보내 응답을 출력한다."""
    stock_prompt = get_stock_price_test_prompt()
    print("\n[주가 실시간 조회 테스트] 각 AI 응답 확인\n")
    print("프롬프트:", stock_prompt[:80] + ("..." if len(stock_prompt) > 80 else ""))
    print()
    max_show = 500  # 응답 길이 제한

    # OpenAI
    print("--- OpenAI ---")
    content, actual = call_openai_api(openai_key, stock_prompt, preferred_model=args.openai_model)
    if content:
        show = content.strip()[:max_show] + ("..." if len(content) > max_show else "")
        print(show)
        print(f"  (모델: {actual}, 길이: {len(content)}자)")
    else:
        print("  (응답 없음)")
    print()

    # Grok (web_search 사용 시도)
    print("--- Grok ---")
    content, actual = call_grok_api(grok_key, stock_prompt, preferred_model=args.grok_model, use_web_search=not args.no_grok_web_search)
    if content:
        show = content.strip()[:max_show] + ("..." if len(content) > max_show else "")
        print(show)
        print(f"  (모델: {actual}, 길이: {len(content)}자)")
    else:
        print("  (응답 없음)")
    print()

    # Gemini (Google Search Grounding 사용)
    print("--- Gemini ---")
    content, actual = call_gemini_api(gemini_key, stock_prompt, preferred_model=args.gemini_model)
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

def run_debug_step(openai_key, grok_key, gemini_key, portfolio_prompt, usd_krw_rate, us_stock_prices, args):
    """--debug-step N: 1=Grok R1, 2=+Gemini R1, 3=+Grok R2, 4=+Gemini R2, 5=+OpenAI. 'next'/'다음' 입력 시 다음 단계로 진행."""
    max_step = 5
    target_step = args.debug_step
    print(f"\n[디버그] Step {target_step}/{max_step}까지 실행 후 대화. 다음 단계로: next 또는 다음. 종료: quit 또는 exit 입력\n")

    # 상태 누적 (다음 단계 진행용)
    draft_report = None
    alpha_cagr = None
    audit_comments = ""
    beta_cagr = None
    grok_r2 = ""
    gemini_r2 = ""

    # Step 1
    grok_system = load_system_prompt("grok") or load_fallback_system("grok")
    initial_prompt = create_initial_prompt(portfolio_prompt, usd_krw_rate, us_stock_prices)
    print("[Step 1] Grok R1 호출 중...")
    t_step = time.perf_counter()
    draft_result = call_grok_api(grok_key, initial_prompt, preferred_model=args.grok_model, use_web_search=not args.no_grok_web_search, system_content=grok_system)
    if not draft_result[0]:
        print("[ERROR] Step 1(Grok R1) 실패")
        return 1
    draft_report, _ = draft_result
    alpha_cagr, current_total_krw, market_data = parse_alpha_json(draft_report)
    print(f"[Step 1] 완료 ({len(draft_report)}자). (소요: {format_elapsed(time.perf_counter() - t_step)})\n---\n{draft_report}\n---")
    if alpha_cagr is not None:
        print(f"[Step 1] Base CAGR(Grok) 예측값: {alpha_cagr}%")
        if current_total_krw is not None:
            print(f"[Step 1] current_total_krw: {current_total_krw}")
    else:
        tail = draft_report[-600:] if len(draft_report) > 600 else draft_report
        print(f"[Step 1] Base CAGR 파싱 실패. 출력 끝부분(JSON 확인용):\n---\n{tail}\n---")
    messages = [
        {"role": "system", "content": grok_system or ""},
        {"role": "user", "content": initial_prompt},
        {"role": "assistant", "content": draft_report}
    ]
    chat_fn, chat_key, preferred = call_grok_chat, grok_key, args.grok_model
    current_step = 1

    if target_step >= 2:
        gemini_system = load_system_prompt("gemini") or load_fallback_system("gemini")
        audit_prompt = create_audit_prompt(draft_report, alpha_cagr, portfolio_prompt)
        print("[Step 2] Gemini R1 호출 중...")
        t_step = time.perf_counter()
        audit_result = call_gemini_api(gemini_key, audit_prompt, preferred_model=args.gemini_model, system_content=gemini_system)
        audit_comments = audit_result[0] if audit_result and audit_result[0] else ""
        if not audit_comments:
            print("[ERROR] Step 2(Gemini R1) 실패")
            return 1
        beta_cagr, risk_level, _ = parse_beta_json(audit_comments)
        print(f"[Step 2] 완료 ({len(audit_comments)}자). (소요: {format_elapsed(time.perf_counter() - t_step)})\n---\n{audit_comments}\n---")
        if beta_cagr is not None:
            print(f"[Step 2] Base CAGR(Gemini) 예측값: {beta_cagr}%")
            if risk_level:
                print(f"[Step 2] risk_level: {risk_level}")
        else:
            tail = audit_comments[-600:] if len(audit_comments) > 600 else audit_comments
            print(f"[Step 2] Base CAGR 파싱 실패. 출력 끝부분(JSON 확인용):\n---\n{tail}\n---")
        messages = [
            {"role": "system", "content": gemini_system or ""},
            {"role": "user", "content": audit_prompt},
            {"role": "assistant", "content": audit_comments}
        ]
        chat_fn, chat_key, preferred = call_gemini_chat, gemini_key, args.gemini_model
        current_step = 2

    if target_step >= 3:
        grok_r2_system = load_system_prompt("grok_r2") or load_fallback_system("grok")
        grok_r2_prompt = create_grok_r2_prompt(audit_comments)
        print("[Step 3] Grok R2(수용·반박) 호출 중...")
        t_step = time.perf_counter()
        grok_r2_result = call_grok_api(grok_key, grok_r2_prompt, preferred_model=args.grok_model, use_web_search=False, system_content=grok_r2_system)
        grok_r2 = grok_r2_result[0] if grok_r2_result and grok_r2_result[0] else ""
        if not grok_r2:
            print("[ERROR] Step 3(Grok R2) 실패")
            return 1
        print(f"[Step 3] 완료 ({len(grok_r2)}자). (소요: {format_elapsed(time.perf_counter() - t_step)})\n---\n{grok_r2}\n---")
        messages = [
            {"role": "system", "content": grok_r2_system or ""},
            {"role": "user", "content": grok_r2_prompt},
            {"role": "assistant", "content": grok_r2}
        ]
        chat_fn, chat_key, preferred = call_grok_chat, grok_key, args.grok_model
        current_step = 3

    if target_step >= 4:
        gemini_r2_system = load_system_prompt("gemini_r2") or load_fallback_system("gemini")
        gemini_r2_prompt = create_gemini_r2_prompt(grok_r2)
        print("[Step 4] Gemini R2(수용·반박) 호출 중...")
        t_step = time.perf_counter()
        gemini_r2_result = call_gemini_api(gemini_key, gemini_r2_prompt, preferred_model=args.gemini_model, system_content=gemini_r2_system)
        gemini_r2 = gemini_r2_result[0] if gemini_r2_result and gemini_r2_result[0] else ""
        if not gemini_r2:
            print("[ERROR] Step 4(Gemini R2) 실패")
            return 1
        print(f"[Step 4] 완료 ({len(gemini_r2)}자). (소요: {format_elapsed(time.perf_counter() - t_step)})\n---\n{gemini_r2}\n---")
        messages = [
            {"role": "system", "content": gemini_r2_system or ""},
            {"role": "user", "content": gemini_r2_prompt},
            {"role": "assistant", "content": gemini_r2}
        ]
        chat_fn, chat_key, preferred = call_gemini_chat, gemini_key, args.gemini_model
        current_step = 4

    if target_step >= 5:
        openai_system = load_system_prompt("openai") or load_fallback_system("openai")
        user_prompt = create_final_prompt(draft_report, alpha_cagr, audit_comments, beta_cagr, portfolio_prompt, grok_r2=grok_r2, gemini_r2=gemini_r2)
        print("[Step 5] OpenAI 호출 중...")
        t_step = time.perf_counter()
        content, model = call_openai_api(openai_key, user_prompt, preferred_model=args.openai_model, system_content=openai_system)
        if not content:
            print("[ERROR] Step 5(OpenAI) 실패")
            return 1
        print(f"[Step 5] 완료 ({len(content)}자). 모델: {model}. (소요: {format_elapsed(time.perf_counter() - t_step)})\n---\n{content}\n---")
        messages = [
            {"role": "system", "content": openai_system or ""},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": content}
        ]
        chat_fn, chat_key, preferred = call_openai_chat, openai_key, args.openai_model
        current_step = 5

    print(f"\n[현재 Step {current_step}/{max_step}] 추가 질문 입력. 다음 단계로: next 또는 다음. 종료: quit 또는 exit 입력\n")
    while True:
        try:
            line = input("You> ").strip()
        except EOFError:
            break
        if line.lower() in ("quit", "exit"):
            print("디버그 모드 종료.")
            break
        if not line:
            continue
        # 다음 단계로 진행
        if line.lower() in ("next", "다음", "n") and current_step < max_step:
            next_step = current_step + 1
            if next_step == 2:
                gemini_system = load_system_prompt("gemini") or load_fallback_system("gemini")
                audit_prompt = create_audit_prompt(draft_report, alpha_cagr, portfolio_prompt)
                print("[Step 2] Gemini R1 호출 중...")
                t_step = time.perf_counter()
                audit_result = call_gemini_api(gemini_key, audit_prompt, preferred_model=args.gemini_model, system_content=gemini_system)
                audit_comments = audit_result[0] if audit_result and audit_result[0] else ""
                if not audit_comments:
                    print("[ERROR] Step 2 실패")
                    continue
                beta_cagr, _, _ = parse_beta_json(audit_comments)
                print(f"[Step 2] 완료 ({len(audit_comments)}자). (소요: {format_elapsed(time.perf_counter() - t_step)})\n---\n{audit_comments}\n---")
                messages = [{"role": "system", "content": gemini_system or ""}, {"role": "user", "content": audit_prompt}, {"role": "assistant", "content": audit_comments}]
                chat_fn, chat_key, preferred = call_gemini_chat, gemini_key, args.gemini_model
                current_step = 2
            elif next_step == 3:
                grok_r2_system = load_system_prompt("grok_r2") or load_fallback_system("grok")
                grok_r2_prompt = create_grok_r2_prompt(audit_comments)
                print("[Step 3] Grok R2(수용·반박) 호출 중...")
                t_step = time.perf_counter()
                grok_r2_result = call_grok_api(grok_key, grok_r2_prompt, preferred_model=args.grok_model, use_web_search=False, system_content=grok_r2_system)
                grok_r2 = grok_r2_result[0] if grok_r2_result and grok_r2_result[0] else ""
                if not grok_r2:
                    print("[ERROR] Step 3 실패")
                    continue
                print(f"[Step 3] 완료 ({len(grok_r2)}자). (소요: {format_elapsed(time.perf_counter() - t_step)})\n---\n{grok_r2}\n---")
                messages = [{"role": "system", "content": grok_r2_system or ""}, {"role": "user", "content": grok_r2_prompt}, {"role": "assistant", "content": grok_r2}]
                chat_fn, chat_key, preferred = call_grok_chat, grok_key, args.grok_model
                current_step = 3
            elif next_step == 4:
                gemini_r2_system = load_system_prompt("gemini_r2") or load_fallback_system("gemini")
                gemini_r2_prompt = create_gemini_r2_prompt(grok_r2)
                print("[Step 4] Gemini R2(수용·반박) 호출 중...")
                t_step = time.perf_counter()
                gemini_r2_result = call_gemini_api(gemini_key, gemini_r2_prompt, preferred_model=args.gemini_model, system_content=gemini_r2_system)
                gemini_r2 = gemini_r2_result[0] if gemini_r2_result and gemini_r2_result[0] else ""
                if not gemini_r2:
                    print("[ERROR] Step 4 실패")
                    continue
                print(f"[Step 4] 완료 ({len(gemini_r2)}자). (소요: {format_elapsed(time.perf_counter() - t_step)})\n---\n{gemini_r2}\n---")
                messages = [{"role": "system", "content": gemini_r2_system or ""}, {"role": "user", "content": gemini_r2_prompt}, {"role": "assistant", "content": gemini_r2}]
                chat_fn, chat_key, preferred = call_gemini_chat, gemini_key, args.gemini_model
                current_step = 4
            elif next_step == 5:
                openai_system = load_system_prompt("openai") or load_fallback_system("openai")
                user_prompt = create_final_prompt(draft_report, alpha_cagr, audit_comments, beta_cagr, portfolio_prompt, grok_r2=grok_r2, gemini_r2=gemini_r2)
                print("[Step 5] OpenAI 호출 중...")
                t_step = time.perf_counter()
                content, model = call_openai_api(openai_key, user_prompt, preferred_model=args.openai_model, system_content=openai_system)
                if not content:
                    print("[ERROR] Step 5 실패")
                    continue
                print(f"[Step 5] 완료 ({len(content)}자). 모델: {model}. (소요: {format_elapsed(time.perf_counter() - t_step)})\n---\n{content}\n---")
                messages = [{"role": "system", "content": openai_system or ""}, {"role": "user", "content": user_prompt}, {"role": "assistant", "content": content}]
                chat_fn, chat_key, preferred = call_openai_chat, openai_key, args.openai_model
                current_step = 5
            print(f"[현재 Step {current_step}/{max_step}] 이제 해당 AI와 대화하세요. 다음 단계: next/다음. 종료: quit/exit\n")
            continue
        # 일반 대화
        print(f"[AI에게 전달한 입력]\n{line}\n")
        messages.append({"role": "user", "content": line})
        reply, _ = chat_fn(chat_key, messages, preferred)
        if not reply:
            print("AI> (응답 실패)")
            messages.pop()
            continue
        messages.append({"role": "assistant", "content": reply})
        print(f"AI> {reply}\n")
    return 0

def main():
    """메인 함수"""
    args = parse_arguments()
    if args.prompt_file is None:
        args.prompt_file = get_default_prompt_file()
    
    print("=" * 60)
    print("포트폴리오 보고서 3-AI 협업 생성 스크립트")
    print("(OpenAI + Grok + Gemini) — 총 8단계")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 환경 변수 로드 (먼저 수행)
    print("\n[1/8] 환경 변수 로드 중...")
    t0 = time.perf_counter()
    openai_key, grok_key, gemini_key = load_env()
    print(f"[1/8] 환경 변수 로드 완료. (소요: {format_elapsed(time.perf_counter() - t0)})")
    
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
    print(f"\n[2/8] 프롬프트 파일 읽는 중: {args.prompt_file}")
    t0 = time.perf_counter()
    portfolio_prompt = read_portfolio_prompt(args.prompt_file)
    print(f"[2/8] 프롬프트 파일 읽기 완료. (소요: {format_elapsed(time.perf_counter() - t0)})")
    
    # 실시간 데이터 조회 (환율 + 미국 주가)
    print("\n[3/8] 실시간 데이터 조회 중...")
    t0 = time.perf_counter()
    usd_krw_rate = fetch_usd_krw_rate()
    if usd_krw_rate:
        print(f"  USD/KRW 환율: {usd_krw_rate}원")
    else:
        print("  USD/KRW 환율: 조회 실패 (AI가 검색으로 대체)")
    
    us_tickers = get_us_tickers()
    us_stock_prices = fetch_us_stock_prices(us_tickers) if us_tickers else {}
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
    print(f"[3/8] 실시간 데이터 조회 완료. (소요: {format_elapsed(time.perf_counter() - t0)})")
    
    # --debug-step: 해당 스텝만 실행 후 추가 질문 대화 모드
    if args.debug_step is not None:
        return run_debug_step(openai_key, grok_key, gemini_key, portfolio_prompt, usd_krw_rate, us_stock_prices, args)
    
    # Step 1: Grok 1차 예측 (Base 시나리오 CAGR) + 초안 작성
    grok_system = load_system_prompt("grok") or load_fallback_system("grok")
    print("\n[4/8] Grok(데이터 분석관) 1차 예측·초안 작성 중 (Base 시나리오 CAGR, web_search)...")
    t0 = time.perf_counter()
    initial_prompt = create_initial_prompt(portfolio_prompt, usd_krw_rate, us_stock_prices)
    draft_result = call_grok_api(grok_key, initial_prompt, preferred_model=args.grok_model, use_web_search=not args.no_grok_web_search, system_content=grok_system)
    
    if draft_result[0] is None:
        print("[ERROR] [4/8] 초안 작성 실패")
        return 1
    
    draft_report, grok_model = draft_result
    alpha_cagr, current_total_krw, market_data = parse_alpha_json(draft_report)
    if alpha_cagr is not None:
        print(f"  Base CAGR(Grok): {alpha_cagr}%")
    print(f"[4/8] Grok 1차 예측·초안 완료 ({len(draft_report)} 문자). (소요: {format_elapsed(time.perf_counter() - t0)})")
    
    # Step 2: Gemini 2차 예측 (Base 시나리오 CAGR) + 리스크 감사
    gemini_system = load_system_prompt("gemini") or load_fallback_system("gemini")
    print("\n[5/8] Gemini(리스크 감사관) 2차 예측·감사 중 (Base 시나리오 CAGR, Google Search)...")
    t0 = time.perf_counter()
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
            print(f"  Base CAGR(Gemini): {beta_cagr}%")
        if risk_level:
            print(f"  리스크 수준: {risk_level}")
    
    print(f"[5/8] Gemini 감사 완료 ({len(audit_comments)} 문자). (소요: {format_elapsed(time.perf_counter() - t0)})")
    
    # Round 2: Grok 수용·반박 (Gemini 감사 검토)
    grok_r2 = ""
    gemini_r2 = ""
    print("\n[6/8] 2라운드(수용·반박) 진행 중...")
    t0 = time.perf_counter()
    grok_r2_system = load_system_prompt("grok_r2") or load_fallback_system("grok")
    grok_r2_prompt = create_grok_r2_prompt(audit_comments)
    grok_r2_result = call_grok_api(grok_key, grok_r2_prompt, preferred_model=args.grok_model, use_web_search=False, system_content=grok_r2_system)
    if grok_r2_result and grok_r2_result[0]:
        grok_r2 = grok_r2_result[0]
        print(f"  Grok 2라운드 완료 ({len(grok_r2)} 문자)")
    else:
        print("  [WARNING] Grok 2라운드 실패 - 2라운드 없이 Step 3 진행")
    
    if grok_r2:
        gemini_r2_system = load_system_prompt("gemini_r2") or load_fallback_system("gemini")
        gemini_r2_prompt = create_gemini_r2_prompt(grok_r2)
        gemini_r2_result = call_gemini_api(gemini_key, gemini_r2_prompt, preferred_model=args.gemini_model, system_content=gemini_r2_system)
        if gemini_r2_result and gemini_r2_result[0]:
            gemini_r2 = gemini_r2_result[0]
            print(f"  Gemini 2라운드 완료 ({len(gemini_r2)} 문자)")
        else:
            print("  [WARNING] Gemini 2라운드 실패 - 2라운드 Grok만 반영")
    
    print(f"[6/8] 2라운드(수용·반박) 완료. (소요: {format_elapsed(time.perf_counter() - t0)})")
    
    # Step 3: GPT 최종 결정 (세 Base 비교 + Bear/Bull 반영 후 최종 CAGR 확정)
    openai_system = load_system_prompt("openai") or load_fallback_system("openai")
    print("\n[7/8] OpenAI(수석 매니저) 세 Base 비교·Bear/Bull 반영 후 최종 CAGR 확정·보고서 작성 중...")
    t0 = time.perf_counter()
    final_prompt = create_final_prompt(draft_report, alpha_cagr, audit_comments, beta_cagr, portfolio_prompt, grok_r2=grok_r2, gemini_r2=gemini_r2)
    final_result = call_openai_api(openai_key, final_prompt, preferred_model=args.openai_model, system_content=openai_system)
    
    elapsed_7 = time.perf_counter() - t0
    if final_result[0] is None:
        print(f"[WARNING] 최종 보고서 작성 실패 - 초안을 사용합니다. (소요: {format_elapsed(elapsed_7)})")
        final_report = draft_report
        openai_model_final = "N/A"
    else:
        final_report, openai_model_final = final_result
        print(f"[7/8] OpenAI 최종 보고서 작성 완료 ({len(final_report)} 문자). (소요: {format_elapsed(elapsed_7)})")
    
    # 보고서 파일명 생성
    report_filename, report_path = generate_report_filename(
        openai_model_final, 
        grok_model, 
        gemini_model,
        output_file=args.output_file
    )
    
    print("\n[8/8] 보고서 저장 중...")
    t0 = time.perf_counter()
    if report_path.exists():
        print(f"  [WARNING] {report_filename} 파일이 이미 존재합니다. 기존 파일을 덮어씁니다.")
    
    # 최종 결과만 report/ 에 저장
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 위웨이크 주식회사 포트폴리오 보고서 (3-AI 협업)\n")
        f.write(f"**작성일: {now.strftime('%Y년 %m월 %d일 %H시 %M분')} (어제 종가 기준: {yesterday.strftime('%Y년 %m월 %d일')})**\n\n")
        f.write(f"**실시간 데이터:**\n")
        if usd_krw_rate:
            f.write(f"- USD/KRW 환율: {usd_krw_rate}원 ({yesterday.strftime('%Y-%m-%d')} API 조회)\n")
        if us_stock_prices:
            f.write(f"- 미국 주가: {', '.join(us_stock_prices.keys())} ({yesterday.strftime('%Y-%m-%d')} API 조회)\n")
        f.write(f"\n**성장률:** Base(Grok) {alpha_cagr or 'N/A'}% | Base(Gemini) {beta_cagr or 'N/A'}% → GPT 세 Base 비교 후 Bear/Bull 반영해 최종 확정\n")
        f.write(f"\n**사용 모델:**\n")
        f.write(f"- Grok (1차 예측·초안): `{grok_model or 'N/A'}`\n")
        f.write(f"- Gemini (2차 예측·감사): `{gemini_model or 'N/A'}`\n")
        f.write(f"- OpenAI (최종 결정): `{openai_model_final or 'N/A'}`\n\n")
        f.write("---\n\n")
        f.write("## 최종 보고서\n\n")
        f.write(final_report)
    
    # 중간 데이터: report/ 아래에 날짜+시간 하위 디렉토리 생성 후 각 AI 입력·출력 저장
    parts = report_path.stem.split("_")
    date_time_dirname = f"{parts[2]}_{parts[3]}" if len(parts) >= 4 else now.strftime("%Y%m%d_%H%M")
    intermediate_dir = REPORTS_DIR / date_time_dirname
    intermediate_dir.mkdir(parents=True, exist_ok=True)
    # AI별 프롬프트 + 출력값을 하나의 파일에 저장
    (intermediate_dir / "step1_grok.md").write_text(
        "## 시스템 프롬프트\n\n" + (grok_system or "") + "\n\n---\n\n## 유저 프롬프트\n\n" + (initial_prompt or "") + "\n\n---\n\n## 출력\n\n" + (draft_report or ""),
        encoding="utf-8"
    )
    (intermediate_dir / "step2_gemini.md").write_text(
        "## 시스템 프롬프트\n\n" + (gemini_system or "") + "\n\n---\n\n## 유저 프롬프트\n\n" + (audit_prompt or "") + "\n\n---\n\n## 출력\n\n" + (audit_comments or ""),
        encoding="utf-8"
    )
    if grok_r2:
        grok_r2_sys = load_system_prompt("grok_r2") or load_fallback_system("grok")
        (intermediate_dir / "step2b_grok.md").write_text(
            "## 시스템 프롬프트\n\n" + (grok_r2_sys or "") + "\n\n---\n\n## 유저 프롬프트\n\n" + (grok_r2_prompt or "") + "\n\n---\n\n## 출력\n\n" + (grok_r2 or ""),
            encoding="utf-8"
        )
    if gemini_r2:
        gemini_r2_sys = load_system_prompt("gemini_r2") or load_fallback_system("gemini")
        (intermediate_dir / "step2b_gemini.md").write_text(
            "## 시스템 프롬프트\n\n" + (gemini_r2_sys or "") + "\n\n---\n\n## 유저 프롬프트\n\n" + (gemini_r2_prompt or "") + "\n\n---\n\n## 출력\n\n" + (gemini_r2 or ""),
            encoding="utf-8"
        )
    (intermediate_dir / "step3_openai.md").write_text(
        "## 시스템 프롬프트\n\n" + (openai_system or "") + "\n\n---\n\n## 유저 프롬프트\n\n" + (final_prompt or "") + "\n\n---\n\n## 출력\n\n" + (final_report or ""),
        encoding="utf-8"
    )
    readme_lines = [
        "# 중간 데이터 (각 AI별 프롬프트 + 출력값)\n\n",
        "| 파일 | 내용 |\n|------|------|\n",
        "| step1_grok.md | Grok: 시스템·유저 프롬프트 + 출력(초안) |\n",
        "| step2_gemini.md | Gemini: 시스템·유저 프롬프트 + 출력(감사) |\n",
    ]
    if grok_r2:
        readme_lines.append("| step2b_grok.md | Grok 2라운드: 수용·반박 |\n")
    if gemini_r2:
        readme_lines.append("| step2b_gemini.md | Gemini 2라운드: 수용·반박 |\n")
    readme_lines.append("| step3_openai.md | OpenAI: 시스템·유저 프롬프트 + 출력(최종 보고서 본문) |\n")
    (intermediate_dir / "README.md").write_text("".join(readme_lines), encoding="utf-8")
    print(f"[8/8] 보고서 저장 완료. 최종: report/{report_filename}, 중간: report/{date_time_dirname}/ (소요: {format_elapsed(time.perf_counter() - t0)})")
    
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
    print(f"   Base CAGR(Grok): {alpha_cagr or 'N/A'}% | Base CAGR(Gemini): {beta_cagr or 'N/A'}%")
    print(f"   최종 보고서 크기: {len(final_report)} 문자")
    print(f"   감사 결과 크기: {len(audit_comments)} 문자")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
