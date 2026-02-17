#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
보고서 기반 Grok·Gemini·OpenAI 대화 스크립트

생성된 포트폴리오 보고서(report/*.md)를 입력으로 받아 Grok, Gemini, OpenAI와 직접 대화합니다.

사용법:
    python discuss_report.py [옵션]

옵션:
    --report FILE         보고서 파일 경로 (기본값: report/ 내 최신 파일)
    --ai grok|gemini|openai   대화 시작 AI (기본값: openai)
    --openai-model MODEL  OpenAI 모델 (기본값: gpt-5.2)
    --grok-model MODEL    Grok 모델 (기본값: grok-4-1-fast-reasoning)
    --gemini-model MODEL  Gemini 모델 (기본값: gemini-3-flash-preview)

대화 중 명령:
    g, grok     → Grok로 전환
    o, openai   → OpenAI로 전환
    gemini      → Gemini로 전환
    quit, exit  → 종료
"""

import os
import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "report"

# 같은 폴더의 generate_portfolio_report_3ai에서 함수 import
sys.path.insert(0, str(Path(__file__).parent))
from generate_portfolio_report_3ai import (
    load_env,
    call_openai_chat,
    call_grok_chat,
    call_gemini_chat,
    ENV_FILE,
)


def find_latest_report():
    """report/ 폴더에서 최신 portfolio_report_*.md 파일 경로 반환."""
    reports = list(REPORTS_DIR.glob("portfolio_report_*.md"))
    if not reports:
        return None
    reports.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[0]


def load_report(report_path):
    """보고서 파일 내용 로드."""
    path = Path(report_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def build_system_prompt(report_content):
    """보고서를 컨텍스트로 한 시스템 프롬프트."""
    return f"""당신은 포트폴리오 분석 전문가입니다. 아래에 3-AI 협업으로 생성된 포트폴리오 보고서가 있습니다.
이 보고서 내용을 바탕으로 사용자의 질문에 답변해 주세요. 수치, CAGR, 시나리오, 리스크 등 보고서에 있는 정보를 인용할 수 있습니다.

=== 포트폴리오 보고서 ===
{report_content}
=== 보고서 끝 ===
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="보고서 기반 Grok·Gemini·OpenAI 대화",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
대화 예시:
  You> Bear 시나리오에서 TSLA 비중이 왜 조정되나요?
  [OpenAI] ...
  You> g
  [Grok로 전환]
  You> 같은 질문에 대해 다른 관점으로 설명해줘
  [Grok] ...
        """
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="보고서 파일 경로 (기본값: report/ 내 최신 portfolio_report_*.md)"
    )
    parser.add_argument(
        "--ai",
        type=str,
        choices=["grok", "gemini", "openai"],
        default="openai",
        help="대화 시작 AI (기본값: openai)"
    )
    parser.add_argument("--openai-model", type=str, default="gpt-5.2")
    parser.add_argument("--grok-model", type=str, default="grok-4-1-fast-reasoning")
    parser.add_argument("--gemini-model", type=str, default="gemini-3-flash-preview")
    return parser.parse_args()


def run_chat(args):
    """대화 루프."""
    openai_key, grok_key, gemini_key = load_env()

    # 보고서 로드
    report_path = args.report
    if not report_path:
        report_path = find_latest_report()
        if not report_path:
            print("[ERROR] report/ 폴더에 portfolio_report_*.md 파일이 없습니다.")
            sys.exit(1)
        print(f"[INFO] 최신 보고서 사용: {report_path.name}")
    else:
        report_path = Path(report_path)
        if not report_path.exists():
            report_path = PROJECT_ROOT / report_path
        if not report_path.exists():
            print(f"[ERROR] 보고서 파일을 찾을 수 없습니다: {args.report}")
            sys.exit(1)

    report_content = load_report(report_path)
    if not report_content:
        print("[ERROR] 보고서 읽기 실패")
        sys.exit(1)

    system_prompt = build_system_prompt(report_content)

    # AI별 호출 함수·키·모델
    ai_map = {
        "openai": (call_openai_chat, openai_key, args.openai_model),
        "grok": (call_grok_chat, grok_key, args.grok_model),
        "gemini": (call_gemini_chat, gemini_key, args.gemini_model),
    }

    current_ai = args.ai
    chat_fn, chat_key, preferred_model = ai_map[current_ai]

    # 초기 메시지 (시스템 + 첫 사용자 메시지 없음, 대화 시작 대기)
    messages = [{"role": "system", "content": system_prompt}]

    print("=" * 60)
    print("보고서 기반 AI 대화 (Grok · Gemini · OpenAI)")
    print(f"보고서: {report_path.name}")
    print(f"현재 AI: {current_ai} ({preferred_model})")
    print("=" * 60)
    print("\n명령: g/grok → Grok, o/openai → OpenAI, gemini → Gemini | quit/exit → 종료\n")

    while True:
        try:
            line = input(f"[{current_ai}] You> ").strip()
        except EOFError:
            break

        if not line:
            continue

        low = line.lower()

        # 종료
        if low in ("quit", "exit"):
            print("종료합니다.")
            break

        # AI 전환
        if low in ("g", "grok"):
            current_ai = "grok"
            chat_fn, chat_key, preferred_model = ai_map[current_ai]
            print(f"[전환] Grok ({preferred_model})\n")
            continue
        if low in ("o", "openai"):
            current_ai = "openai"
            chat_fn, chat_key, preferred_model = ai_map[current_ai]
            print(f"[전환] OpenAI ({preferred_model})\n")
            continue
        if low == "gemini":
            current_ai = "gemini"
            chat_fn, chat_key, preferred_model = ai_map[current_ai]
            print(f"[전환] Gemini ({preferred_model})\n")
            continue

        # 대화
        messages.append({"role": "user", "content": line})
        reply, model_used = chat_fn(chat_key, messages, preferred_model)

        if reply is None:
            print(f"[ERROR] {current_ai} API 호출 실패\n")
            messages.pop()  # 실패 시 user 메시지 제거
            continue

        messages.append({"role": "assistant", "content": reply})
        print(f"\n[{current_ai} ({model_used})]\n{reply}\n")


def main():
    args = parse_args()
    run_chat(args)


if __name__ == "__main__":
    main()
