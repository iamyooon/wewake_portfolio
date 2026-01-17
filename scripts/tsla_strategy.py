"""
테슬라 비중 및 스윙 전략 분석 스크립트

현재 테슬라 포지션을 분석하고, 목표 비중 달성을 위한 매도 전략과
스윙 트레이딩 시나리오를 계산합니다.
"""

# 포트폴리오 현황 (2026.01.16 기준)
corp_tsla = 919  # 법인 계좌 테슬라 보유량
pers_tsla = 99   # 개인 계좌 테슬라 보유량
total_tsla = corp_tsla + pers_tsla

total_asset = 1010.92  # 총 자산 (억원)
tsla_value_corp = 592.56  # 법인 계좌 테슬라 가치 (억원)
tsla_value_pers = 63.83   # 개인 계좌 테슬라 가치 (억원)
tsla_total_value = tsla_value_corp + tsla_value_pers

current_weight = tsla_total_value / total_asset * 100
current_price = 437.50  # 현재 테슬라 주가 (USD)
exchange_rate = 1473.76  # USD/KRW 환율

print("=" * 60)
print("현재 테슬라 포지션 분석")
print("=" * 60)
print(f"총 보유량: {total_tsla}주")
print(f"현재 비중: {current_weight:.1f}%")
print(f"현재가: ${current_price}")
print(f"스윙 물량(10% 룰): {int(total_tsla * 0.1)}주")
print()

print("=" * 60)
print("목표 비중별 시나리오")
print("=" * 60)

scenarios = [50, 55, 60, 65]
for w in scenarios:
    target_value = total_asset * w / 100
    reduction = tsla_total_value - target_value
    reduction_shares = int(reduction / (current_price * exchange_rate / 100000000))
    print(f"목표 비중 {w}%:")
    print(f"  - 테슬라 목표 가치: {target_value:.2f}억")
    print(f"  - 감소 필요: {reduction:.2f}억 ({reduction_shares}주)")
    print()

print("=" * 60)
print("스윙 전략 시나리오")
print("=" * 60)

# 시나리오 1: 100주 매도 (10% 룰)
swing_100 = 100
swing_value_100 = swing_100 * current_price * exchange_rate / 100000000
new_weight_100 = (tsla_total_value - swing_value_100) / total_asset * 100

print(f"시나리오 1: 100주 매도 (현재 10% 룰)")
print(f"  - 매도 물량: {swing_100}주")
print(f"  - 매도 가치: {swing_value_100:.2f}억")
print(f"  - 매도 후 비중: {new_weight_100:.1f}%")
print(f"  - 비중 감소: {current_weight - new_weight_100:.1f}%p")
print()

# 시나리오 2: 150주 매도 (15% 룰)
swing_150 = 150
swing_value_150 = swing_150 * current_price * exchange_rate / 100000000
new_weight_150 = (tsla_total_value - swing_value_150) / total_asset * 100

print(f"시나리오 2: 150주 매도 (15% 룰)")
print(f"  - 매도 물량: {swing_150}주")
print(f"  - 매도 가치: {swing_value_150:.2f}억")
print(f"  - 매도 후 비중: {new_weight_150:.1f}%")
print(f"  - 비중 감소: {current_weight - new_weight_150:.1f}%p")
print()

# 시나리오 3: 200주 매도 (20% 룰)
swing_200 = 200
swing_value_200 = swing_200 * current_price * exchange_rate / 100000000
new_weight_200 = (tsla_total_value - swing_value_200) / total_asset * 100

print(f"시나리오 3: 200주 매도 (20% 룰)")
print(f"  - 매도 물량: {swing_200}주")
print(f"  - 매도 가치: {swing_value_200:.2f}억")
print(f"  - 매도 후 비중: {new_weight_200:.1f}%")
print(f"  - 비중 감소: {current_weight - new_weight_200:.1f}%p")
print()

print("=" * 60)
print("스윙 매수 전략 (재진입)")
print("=" * 60)

buy_back_prices = [380, 400, 420]
for buy_price in buy_back_prices:
    profit_per_share = current_price - buy_price
    profit_100 = profit_per_share * 100 * exchange_rate / 100000000
    print(f"${buy_price} 재매수 시:")
    print(f"  - 주당 수익: ${profit_per_share:.2f}")
    print(f"  - 100주 스윙 수익: {profit_100:.2f}억")
    print()

print("=" * 60)
print("권장 전략")
print("=" * 60)
print("1. 1차 매도: $445~$450에서 100주 매도 (10% 룰)")
print("   -> 비중 64.9% -> 약 58%로 감소")
print("   -> 현금 확보: 약 6.5억")
print()
print("2. 재진입: $380~$400 구간에서 재매수 고려")
print("   -> 스윙 수익: 주당 $45~$65 (약 0.7~1.0억)")
print()
print("3. 최종 목표 비중: 50~55%")
print("   -> 추가 매도 필요: 약 100~150주")
print("   -> 총 매도: 200~250주 (20~25% 룰)")
print()
