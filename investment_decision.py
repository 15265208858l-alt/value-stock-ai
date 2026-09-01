"""最终投资决策：保持估值模型不变，只让评分结果映射更清晰。"""
from peer_compare import get_last_relative_valuation

def make_investment_decision(investment_score,valuation_level,historical_level,risk_level):
    try: score=float(investment_score)
    except (TypeError,ValueError): score=0.0
    val=str(valuation_level or "数据不足"); hist=str(historical_level or "数据不足"); risk=str(risk_level or "数据不足")
    rel=get_last_relative_valuation(); rel_level=rel.get("level","数据不足")

    # 硬风险优先，不能被估值便宜抵消。
    if risk=="高风险":
        return {"decision":"🔴 原则上回避","action":"暂不买入","position":"0%","reason":"存在较高财务风险，同行相对估值不能抵消核心风险。"}

    low_val=["明显低估","较低估值","偏低估值"]
    fair_val=["合理附近"]
    high_val=["偏高估值","明显偏高","高估"]
    safe_risk=["低风险","风险较低","需要关注","数据不足"]

    # 低估/合理：质量分高时给出真正可执行的分批建仓建议。
    if score>=78 and val in low_val+fair_val and hist!="历史高位" and risk in safe_risk:
        return {"decision":"🟢 可以分批建仓","action":"分批买入，控制节奏","position":"10%—25%","reason":"综合质量较高，当前估值处于低估或合理区间，具备一定安全边际。"}
    if score>=74 and val in low_val+fair_val and risk in safe_risk:
        return {"decision":"🟢 小仓试探","action":"先建立小仓，继续观察","position":"5%—10%","reason":"公司质量与估值匹配度较好，但安全边际仍需继续验证。"}
    if score>=68 and val=="合理附近" and hist not in ["历史高位"] and risk in safe_risk:
        return {"decision":"🟡 小仓关注","action":"建立观察仓","position":"3%—5%","reason":"公司具备一定质量，估值接近合理区间，可小仓观察，不追高。"}

    # 高估：即使公司优秀也不强行给买入；区分“等待”和“谨慎观察”。
    if score>=65 and val in high_val:
        if rel_level in ["同行明显便宜","同行相对便宜"] and risk in safe_risk:
            return {"decision":"🟡 高成长高估值，等待","action":"不追高，加入重点观察名单","position":"0%—5%","reason":"绝对估值偏高，但相对同行仍有一定优势；等待盈利增长或价格回落后再评估。"}
        return {"decision":"🟡 等待更好价格","action":"不追高，加入观察名单","position":"0%—5%","reason":"企业质量未必差，但当前价格缺乏足够安全边际，等待估值回落。"}

    # 中间区域：不再把所有结果笼统写成“谨慎观察”。
    if score>=62 and risk not in ["高风险","风险较高"]:
        return {"decision":"🟠 继续观察","action":"跟踪业绩、现金流与估值变化","position":"0%—3%","reason":"综合评分处于中间区域，尚不足以形成明确买入信号，优先等待关键指标改善或价格回落。"}

    if risk=="风险较高":
        return {"decision":"🟠 风险观察","action":"暂不买入，重点跟踪风险变化","position":"0%","reason":"财务风险偏高，即使估值存在吸引力，也需要先确认风险是否改善。"}

    return {"decision":"🔴 暂不考虑","action":"暂不买入","position":"0%","reason":"当前综合质量或风险收益比尚未达到长期价值投资的优先标准。"}
