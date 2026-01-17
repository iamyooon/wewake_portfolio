"""
2030년 25억 달성 현실성 분석 스크립트

현재 자산에서 2030년 목표 자산 달성에 필요한 CAGR을 계산하고,
다양한 CAGR 시나리오별 예상 자산을 산출합니다.
"""

start = 10.11  # 현재 자산 (억원)
target = 25.0  # 목표 자산 (억원)
years = 4.96   # 투자 기간 (년) - 2026.01 ~ 2030.12

# 필요한 CAGR 계산
required_cagr = (target / start) ** (1 / years) - 1

print("=" * 50)
print("2030년 25억 달성 현실성 분석")
print("=" * 50)
print(f"현재 자산: {start}억")
print(f"목표 자산: {target}억")
print(f"기간: {years}년 (2026.01 ~ 2030.12)")
print(f"필요 CAGR: {required_cagr*100:.2f}%")
print()

print("연도별 예상 (필요 CAGR 적용):")
for i in range(1, 6):
    val = start * (1 + required_cagr) ** i
    print(f"202{5+i}년 말: {val:.2f}억")

print()
print("=" * 50)
print("다양한 CAGR 시나리오별 2030년 예상")
print("=" * 50)

scenarios = [15, 18, 20, 22, 25]
for s in scenarios:
    val = start * (1 + s/100) ** years
    gap = val - target
    status = "달성" if gap >= 0 else "미달"
    print(f"CAGR {s:2d}%: {val:6.2f}억 (목표 대비 {gap:+.2f}억) [{status}]")

print()
print("=" * 50)
print("현실성 평가")
print("=" * 50)
print("S&P 500 장기 평균: 8-10%")
print("연 20%는 매우 도전적이며 높은 리스크 수반")
print("일부 성장 펀드는 단기간 달성했으나 장기 유지는 어려움")
print()
print("현재 포트폴리오 특징:")
print("- 테슬라 64.9% 집중 (고변동성)")
print("- MSTR 딥 바잉 전략 (비트코인 사이클 연동)")
print("- 반도체/성장주 중심")
print()
print("결론:")
if required_cagr * 100 <= 20:
    print(f"필요 CAGR {required_cagr*100:.2f}%는 도전적이지만 현재 포트폴리오 구성상")
    print("가능성은 있습니다. 다만 높은 변동성과 리스크를 감수해야 합니다.")
else:
    print(f"필요 CAGR {required_cagr*100:.2f}%는 매우 높은 수준입니다.")
    print("목표 조정 또는 추가 자본 유입을 고려해야 할 수 있습니다.")
