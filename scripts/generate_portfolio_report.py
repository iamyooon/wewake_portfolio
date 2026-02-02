#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
포트폴리오 보고서 자동 생성 스크립트
매일 아침 8시에 portfolio_prompt.txt 기반으로 보고서를 생성합니다.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import json

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"
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

def read_portfolio_prompt():
    """포트폴리오 프롬프트 파일을 읽어옵니다 (경로는 config.json 기준)."""
    path = get_portfolio_prompt_path()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ 오류: {path} 파일을 찾을 수 없습니다.")
        sys.exit(1)

def generate_report_filename():
    """보고서 파일명을 생성합니다."""
    today = datetime.now()
    date_str = today.strftime("%Y%m%d")
    return f"portfolio_report_{date_str}_auto.md"

def create_cursor_prompt(portfolio_prompt_content):
    """Cursor AI에게 보낼 프롬프트를 생성합니다."""
    today = datetime.now()
    date_str = today.strftime("%Y년 %m월 %d일")
    yesterday_str = (today - timedelta(days=1)).strftime("%Y년 %m월 %d일")
    
    prompt = f"""portfolio_prompt.txt 파일을 기반으로 포트폴리오 보고서를 작성해주세요.

작성일: {date_str} (어제 종가 기준: {yesterday_str})

{portfolio_prompt_content}

위 지침에 따라 보고서를 작성하고, 파일명은 portfolio_report_{datetime.now().strftime('%Y%m%d')}_auto.md로 저장해주세요.
"""
    return prompt

def main():
    """메인 함수"""
    print("=" * 60)
    print("포트폴리오 보고서 자동 생성 스크립트")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    print("\n📖 포트폴리오 프롬프트 파일 읽는 중...")
    portfolio_prompt = read_portfolio_prompt()
    print("✅ 파일 읽기 완료")
    
    # 보고서 파일명 생성
    report_filename = generate_report_filename()
    report_path = REPORTS_DIR / report_filename
    
    # 이미 보고서가 존재하는지 확인
    if report_path.exists():
        print(f"\n⚠️  경고: {report_filename} 파일이 이미 존재합니다.")
        response = input("덮어쓰시겠습니까? (y/n): ")
        if response.lower() != 'y':
            print("❌ 작업을 취소했습니다.")
            sys.exit(0)
    
    print(f"\n📝 보고서 생성 중: {report_filename}")
    print("\n" + "=" * 60)
    print("⚠️  참고: 이 스크립트는 보고서 생성을 위한 프롬프트를 준비합니다.")
    print("실제 보고서 생성은 Cursor AI를 통해 수행해야 합니다.")
    print("=" * 60)
    
    # Cursor용 프롬프트 생성
    cursor_prompt = create_cursor_prompt(portfolio_prompt)
    
    # 프롬프트를 파일로 저장 (참고용)
    prompt_file = REPORTS_DIR / f"report_prompt_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(cursor_prompt)
    
    print(f"\n✅ 프롬프트 파일 생성 완료: {prompt_file.name}")
    print("\n다음 단계:")
    print("1. Cursor에서 이 프롬프트를 사용하여 보고서를 생성하세요")
    print("2. 또는 Cursor API를 사용하여 자동화할 수 있습니다")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
