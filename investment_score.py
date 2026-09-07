"""ValueStock AI 投资价值综合评分模块 V4.0

设计目标：把长期价值投资的核心逻辑真正落到评分里，同时保持 V3.0 主程序接口兼容。

评分框架（100分）：
- 企业质量 25：财务质量、ROE、盈利能力
- 成长质量 15：营收/利润增长及稳定性
- 现金流质量 15：经营现金流与利润匹配度
- 资产负债表 10：负债率及财务安全
- 营运资本质量 10：应收/存货相对收入的压力
- 当前估值 10：合理价值安全边际
- 历史估值 5：当前估值处于历史什么位置
- 同行竞争力 5：相对行业位置
- 盈利兑现质量 5：正常化盈利的可信度

风险不再简单“加分减分”，而是增加硬闸门：高风险直接否决，数据不足限制最高评级。
"""

from peer_compare import get_last_relative_valuation, reset_relative_valuation


def _num(v):
    try:
        if v is None:
            return None
        x = float(v)
        return x
    except Exception:
        return None


def _clamp(v, lo, hi):
    return max(lo, min(hi, float(v)))


def score_current_valuation(valuation_gap):
    if valuation_gap is None:
        return {"score": 5, "level": "数据不足", "available": False}
    gap = float(valuation_gap)
    if gap >= 40:
        return {"score": 10, "level": "明显低估", "available": True}
    if gap >= 25:
        return {"score": 9, "level": "较低估值", "available": True}
    if gap >= 10:
        return {"score": 8, "level": "偏低估值", "available": True}
    if gap >= -5:
        return {"score": 6, "level": "合理附近", "available": True}
    if gap >= -15:
        return {"score": 4, "level": "偏高估值", "available": True}
    if gap >= -30:
        return {"score": 2, "level": "明显偏高", "available": True}
    return {"score": 0, "level": "高估", "available": True}


def score_historical_valuation(historical_percentile):
    if historical_percentile is None:
        return {"score": 2.5, "level": "数据不足", "available": False}
    p = float(historical_percentile)
    if p <= 20:
        return {"score": 5, "level": "历史低位", "available": True}
    if p <= 40:
        return {"score": 4, "level": "历史中低位", "available": True}
    if p <= 60:
        return {"score": 3, "level": "历史中枢", "available": True}
    if p <= 80:
        return {"score": 1.5, "level": "历史中高位", "available": True}
    return {"score": 0, "level": "历史高位", "available": True}


def score_risk(risk_score):
    if risk_score is None:
        return {"score": 5, "level": "数据不足", "available": False}
    r = float(risk_score)
    if r <= 0:
        return {"score": 10, "level": "低风险", "available": True}
    if r <= 3:
        return {"score": 8, "level": "风险较低", "available": True}
    if r <= 6:
        return {"score": 6, "level": "需要关注", "available": True}
    if r <= 9:
        return {"score": 3, "level": "风险较高", "available": True}
    return {"score": 0, "level": "高风险", "available": True}


def _score_enterprise_quality(financial_score, roe=None):
    # financial_score 本身为 0~100，再压缩到 25 分。
    base = 15.0 if financial_score is None else _clamp(float(financial_score) * 0.25, 0, 25)
    available = financial_score is not None
    if roe is not None:
        r = float(roe)
        if r >= 20:
            base = min(25.0, base + 1.5)
        elif r >= 15:
            base = min(25.0, base + 1.0)
        elif r < 8:
            base = max(0.0, base - 1.5)
        available = True
    return round(base, 1), available


def _score_growth(revenue_growth=None, profit_growth=None):
    vals = [v for v in (_num(revenue_growth), _num(profit_growth)) if v is not None]
    if not vals:
        return 7.5, False
    rg, pg = _num(revenue_growth), _num(profit_growth)
    points = 7.5
    if rg is not None:
        points += 3.5 if rg >= 20 else 2.5 if rg >= 10 else 1.0 if rg >= 5 else -1.0 if rg < 0 else 0
    if pg is not None:
        points += 3.5 if pg >= 20 else 2.5 if pg >= 10 else 1.0 if pg >= 5 else -1.5 if pg < 0 else 0
    return round(_clamp(points, 0, 15), 1), True


def _score_cash(cashflow_ratio):
    r = _num(cashflow_ratio)
    if r is None:
        return 7.5, False
    if r >= 1.2:
        return 15.0, True
    if r >= 1.0:
        return 13.5, True
    if r >= 0.8:
        return 11.0, True
    if r >= 0.5:
        return 7.0, True
    if r >= 0:
        return 3.0, True
    return 0.0, True


def _score_balance(debt_ratio):
    d = _num(debt_ratio)
    if d is None:
        return 5.0, False
    if d < 40:
        return 10.0, True
    if d < 50:
        return 8.5, True
    if d < 60:
        return 7.0, True
    if d < 70:
        return 4.5, True
    return 1.0, True


def _score_working_capital(receivable_to_revenue=None, inventory_to_revenue=None):
    r = _num(receivable_to_revenue)
    i = _num(inventory_to_revenue)
    if r is None and i is None:
        return 5.0, False
    points = 5.0
    if r is not None:
        points += 2.5 if r < 0.10 else 1.5 if r < 0.20 else 0 if r < 0.30 else -1.5
    if i is not None:
        points += 2.5 if i < 0.15 else 1.5 if i < 0.30 else 0 if i < 0.45 else -1.5
    return round(_clamp(points, 0, 10), 1), True


def _score_earnings_realization(realization_score):
    r = _num(realization_score)
    if r is None:
        return 2.5, False
    return round(_clamp(r * 0.05, 0, 5), 1), True


def _confidence_gate(raw_score, available_count):
    if available_count >= 8:
        return round(raw_score), "高"
    if available_count >= 6:
        return min(round(raw_score), 84), "中高"
    if available_count >= 4:
        return min(round(raw_score), 79), "中"
    if available_count >= 2:
        return min(round(raw_score), 69), "低"
    return min(round(raw_score), 59), "低"


def _research_status(total_score, confidence, valuation_level, risk_level):
    if risk_level == "高风险":
        return "风险否决"
    if confidence == "低":
        return "数据不足"
    if total_score >= 85 and confidence in {"高", "中高"}:
        return "核心候选"
    if total_score >= 75:
        return "优质候选"
    if total_score >= 65:
        return "重点跟踪"
    if valuation_level in {"明显低估", "较低估值", "偏低估值"} and total_score >= 58:
        return "估值机会"
    return "观察"


def calculate_investment_score(
    financial_score,
    peer_score,
    valuation_gap,
    risk_score,
    historical_percentile=None,
    **kwargs,
):
    """计算长期价值投资综合评分。

    保留旧版五参数接口；额外指标通过 kwargs 传入，不会破坏旧调用。
    """
    if peer_score is None:
        reset_relative_valuation()

    roe = kwargs.get("roe")
    revenue_growth = kwargs.get("revenue_growth")
    profit_growth = kwargs.get("profit_growth")
    cashflow_ratio = kwargs.get("cashflow_ratio")
    debt_ratio = kwargs.get("debt_ratio")
    receivable_to_revenue = kwargs.get("receivable_to_revenue")
    inventory_to_revenue = kwargs.get("inventory_to_revenue")
    realization_score = kwargs.get("realization_score")

    quality, quality_available = _score_enterprise_quality(financial_score, roe)
    growth, growth_available = _score_growth(revenue_growth, profit_growth)
    cash, cash_available = _score_cash(cashflow_ratio)
    balance, balance_available = _score_balance(debt_ratio)
    working_capital, working_capital_available = _score_working_capital(receivable_to_revenue, inventory_to_revenue)
    earnings, earnings_available = _score_earnings_realization(realization_score)

    current_result = score_current_valuation(valuation_gap)
    historical_result = score_historical_valuation(historical_percentile)
    risk_result = score_risk(risk_score)

    relative = get_last_relative_valuation()
    relative_available = peer_score is not None and bool(relative.get("available"))
    peer_points = 5.0
    if relative_available:
        peer_points = _clamp(float(peer_score) * 0.05, 0, 5)

    # 估值维度 = 当前估值 10 + 历史估值 5。
    valuation_points = current_result["score"] + historical_result["score"]

    # 风险不进入正常“奖励项”，而是用风险折扣 + 否决逻辑控制最终分数。
    risk_discount = 0 if risk_score is None else (0 if risk_score <= 3 else 1.5 if risk_score <= 6 else 4.0 if risk_score <= 9 else 10.0)

    raw_score = _clamp(
        quality + growth + cash + balance + working_capital + valuation_points + peer_points + earnings - risk_discount,
        0,
        100,
    )

    available_count = sum([
        quality_available,
        growth_available,
        cash_available,
        balance_available,
        working_capital_available,
        current_result["available"],
        historical_result["available"],
        peer_available,
        earnings_available,
    ])

    total_score, confidence = _confidence_gate(raw_score, available_count)

    if risk_result["level"] == "高风险":
        total_score = min(total_score, 39)
    elif risk_result["level"] == "风险较高":
        total_score = min(total_score, 64)

    if total_score >= 85:
        rating = "A：优质公司 + 估值有吸引力"
    elif total_score >= 75:
        rating = "B：优质公司 + 估值合理"
    elif total_score >= 65:
        rating = "C：值得跟踪，等待更好价格"
    elif total_score >= 50:
        rating = "D：谨慎观察"
    else:
        rating = "E：风险较高"

    status = _research_status(total_score, confidence, current_result["level"], risk_result["level"])

    return {
        "score": int(total_score),
        "raw_score": round(raw_score),
        "rating": rating,
        "research_status": status,
        "financial_component": quality,
        "growth_component": growth,
        "cashflow_component": cash,
        "balance_component": balance,
        "working_capital_component": working_capital,
        "earnings_realization_component": earnings,
        "peer_component": round(peer_points, 1),
        "peer_raw_score": peer_score,
        "valuation_component": round(valuation_points, 1),
        "absolute_valuation_component": round(current_result["score"], 1),
        "historical_component": round(historical_result["score"], 1),
        "relative_valuation_component": round(_clamp(float(relative.get("score", 0)) * 0.05, 0, 5), 1) if relative_available else None,
        "relative_valuation_available": relative_available,
        "relative_valuation_level": relative.get("level", "数据不足"),
        "peer_median_pe": relative.get("peer_median_pe"),
        "peer_median_pb": relative.get("peer_median_pb"),
        "relative_pe_ratio": relative.get("pe_ratio"),
        "relative_pb_ratio": relative.get("pb_ratio"),
        "valuation_level": current_result["level"],
        "historical_level": historical_result["level"],
        "historical_percentile": historical_percentile,
        "risk_component": risk_result["score"],
        "risk_level": risk_result["level"],
        "risk_discount": risk_discount,
        "data_available_count": available_count,
        "data_confidence": confidence,
        "data_gate": "通过" if available_count >= 4 else "未通过",
        "score_framework": "质量25 + 成长15 + 现金流15 + 资产负债10 + 营运资本10 + 估值15 + 同行5 + 盈利兑现5",
    }
