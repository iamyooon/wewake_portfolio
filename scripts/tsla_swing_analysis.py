"""
테슬라 스윙 트레이딩 분석 스크립트
"""

high_3m = 498.83  # 3개월 최고가
current = 437.50  # 현재가
rsi_weekly = 47.56  # 주봉 RSI

# 괴리율 계산
gap = (current - high_3m) / high_3m * 100

# 매매 기준가 계산
buy1 = high_3m * 0.85  # 1차 매수 (-15%)
buy2 = high_3m * 0.80  # 2차 매수 (-20%)
recovery = high_3m * 0.90  # 추세 복귀 (-10%)
sell_threshold = high_3m * 0.98  # 매도 신호 기준 (-2%)

print("=" * 60)
print("테슬라(TSLA) 스윙 트레이딩 분석")
print("=" * 60)
print()
print("팩트 체크:")
print(f"  3개월 최고가: ${high_3m:.2f}")
print(f"  현재가: ${current:.2f}")
print(f"  괴리율: {gap:.1f}%")
print(f"  주봉 RSI: {rsi_weekly:.2f} (중립 구간)")
print(f"  볼린저 밴드: 하단 근처 (50일 이동평균 아래)")
print()
print("매매 가이드라인:")
print(f"  1차 매수 타겟 (-15%): ${buy1:.2f}")
print(f"  2차 매수 타겟 (-20%): ${buy2:.2f}")
print(f"  추세 복귀 지점 (-10%): ${recovery:.2f}")
print(f"  매도 신호 기준 (-2%): ${sell_threshold:.2f}")
print()
print("=" * 60)
print("매매 신호 판독")
print("=" * 60)

# 매도 신호 체크
sell_signal = False
if current >= sell_threshold:
    sell_signal = True
    print("[SELL] 매도 신호")
    print("  조건: 현재가가 3개월 최고가의 -2% 이내")
elif rsi_weekly > 75:
    sell_signal = True
    print("[SELL] 매도 신호")
    print("  조건: 주봉 RSI > 75")
else:
    print("  매도 신호: 없음")

# 매수 신호 체크
buy_signal = None
if current <= buy2:
    buy_signal = "2차매수"
    print("[BUY] 2차 매수 신호")
    print(f"  조건: 현재가 ${current:.2f} <= 2차 매수 타겟 ${buy2:.2f}")
    print("  행동: 남은 현금 50%를 투입하여 2차 매수")
elif current <= buy1:
    buy_signal = "1차매수"
    print("[BUY] 1차 매수 신호")
    print(f"  조건: 현재가 ${current:.2f} <= 1차 매수 타겟 ${buy1:.2f}")
    print("  행동: 확보해둔 현금의 50%를 투입하여 1차 매수")
else:
    buy_signal = None
    print("  매수 신호: 없음")
    if current < recovery:
        print(f"  참고: 현재가 ${current:.2f}는 추세 복귀 지점 ${recovery:.2f} 미만")
        print(f"        복구 신호는 1차 매수 후 반등하여 ${recovery:.2f}를 회복했을 때 발생")

# 최종 결론
print()
print("=" * 60)
print("최종 결론")
print("=" * 60)

if sell_signal:
    print("**매도**")
    print("현재 총 보유량의 10%를 매도하여 현금 확보")
elif buy_signal == "2차매수":
    print("**2차매수**")
    print("남은 현금 50%를 투입하여 2차 매수")
elif buy_signal == "1차매수":
    print("**1차매수**")
    print("확보해둔 현금의 50%를 투입하여 1차 매수")
elif buy_signal == "복구":
    print("**복구**")
    print("남은 현금 전액 시장가 매수하여 물량 복구")
else:
    print("**홀딩**")
    print("현재 하락 조정 중입니다. 기준가 도달 시까지 대기")
    print(f"  -> 1차 매수 타겟 ${buy1:.2f} 도달 대기")
    print(f"  -> 현재 ${current:.2f}에서 ${buy1:.2f}까지 약 ${current - buy1:.2f} 하락 필요")
