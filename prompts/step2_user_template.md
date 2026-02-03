[Step 2 - 리스크 감사관용] 아래 Grok 초안(Grok의 Base 시나리오 CAGR {{alpha_cagr}} 참고)을 검토하라. **동일한 Base 시나리오(기본 시나리오)** 전제에서, **연단위·다년도 기대수익률**로서 **독립적인 Base 시나리오 CAGR**를 산출하라.

**핵심 임무:**
1. CAGR은 장기 기대치이므로, 거시·리스크는 **기간(예: 5년) 중 예상 궤적**으로 참고하라. 당장의 금리·물가·이번 주 이벤트에 CAGR을 맞추지 말 것.
2. **Base 시나리오 CAGR 예측:** Grok과 **같은 base(기본 시나리오)** 기준으로, 독립적으로 예상 CAGR을 산출하라. 보수/낙관으로 치우치지 말 것.
3. 리스크 섹션은 **장기 관점의 구조적 리스크**를 다루라. 단기 블랙스완 나열보다는, CAGR에 영향을 주는 구조적 요인을 정리하라.

**출력 하단에 반드시 다음 JSON을 포함하라:** {"beta_cagr": 0.0, "risk_level": "low/mid/high", "audit_notes": "..."} (beta_cagr = Base 시나리오 CAGR)

---

**Grok 초안 (Base 시나리오 CAGR 포함)**:
{{draft_report}}

---

**포트폴리오 참고 (앞 2000자)**:
{{portfolio_prompt_content}}
