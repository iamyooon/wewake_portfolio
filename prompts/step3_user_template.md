[Step 3 - 수석 매니저용] Grok·Gemini와 같이 **Base 시나리오(기본 시나리오)** 기준으로 **너 자신의 CAGR**을 예측한 뒤, **세 Base CAGR을 비교**하고, **최종 정리할 때만 Bear case·Bull case를 고려**하여 **포트폴리오에 명시된 목표** 달성 가능성을 냉정하게 리포트하라. (구체적 목표·숫자는 아래 포트폴리오 프롬프트에서 확인할 것)

**제공된 Base 시나리오 CAGR (아래 전문과 함께 활용):**
- **Grok Base CAGR:** {{alpha_cagr}}
- **Gemini Base CAGR:** {{beta_cagr}}

**지시:** (1) **자신의 Base CAGR 예측:** 초안·감사·포트폴리오만으로 **동일한 Base 시나리오** 전제에서 너만의 CAGR을 예측하라. 숫자(예: 8.5%)와 근거를 명시하라. (2) **2라운드 정리:** Grok·Gemini 2라운드(수용·반박)가 있으면 합의·대립을 요약하라. (3) **세 Base 비교:** **자신의 Base CAGR**, **Grok Base({{alpha_cagr}})**, **Gemini Base({{beta_cagr}})** 를 나란히 비교하고, 차이·이유를 정리하라. (4) **최종 결론 (Bear/Bull 반영):** 여기서만 **Bear case(악재)**와 **Bull case(호재)**를 고려하라. 세 Base 비교 결과를 바탕으로 하방·상방을 반영한 **최종 전략적 CAGR**을 확정하라. 전 종목을 누락 없이 포함하고, 확정한 최종 CAGR로 로드맵을 작성한 뒤, **포트폴리오에 명시된 인출 계획**에 따른 **복리 저해 효과(Compounding Penalty)**를 정밀 계산하여 경고하라.

---

**Grok 초안 전문**:
{{grok_draft}}

---

**Gemini 감사 결과 전문**:
{{gemini_audit_text}}

---

**2라운드 - Grok 수용·반박**:
{{grok_r2_response}}

---

**2라운드 - Gemini 수용·반박**:
{{gemini_r2_response}}

---

**포트폴리오 프롬프트 (참고용)**:
{{portfolio_prompt_content}}
