"""ValueStock AI 投资价值综合评分模块 V3.0

核心原则：
- 评分必须区分“真实得分”和“数据可信度”，缺失数据不能伪装成高质量研究结果。
- 保留原有接口，兼容主程序；在此基础上增加数据完整性闸门。
- 估值、财务质量、历史估值、风险、同行比较共同决定最终评级。
"""

from peer_compare import get_last_relative_valuation, reset_relative_valuation


def score_current_valuation(valuation_gap):
    if valuation_gap is None:
        return {"score": 10, "level": "数据不足", "available": False}
    if valuation_gap >= 30:
        return {"score": 20, "level": "明显低估", "available": True}
    if valuation_gap >= 20:
        return {"score": 18, "level": "较低估值", "available": True}
    if valuation_gap >= 10:
        return {"score": 16, "level": "偏低估值", "available": True}
    if valuation_gap >= 0:
        return {"score": 13, "level": "合理附近", "available": True}
    if valuation_gap >= -10:
        return {"score": 9, "level": "偏高估值", "available": True}
    if valuation_gap >= -20:
        return {"score": 5, "level": "明显偏高", "available": True}
    return {"score": 2, "level": "高估", "available": True}


def score_historical_valuation(historical_percentile):
    if historical_percentile is None:
        return {"score": 7.5, "level": "数据不足", "available": False}
    if historical_percentile <= 20:
        return {"score": 15, "level": "历史低位", "available": True}
    if historical_percentile <= 40:
        return {"score": 13, "level": "历史中低位", "available": True}
    if historical_percentile <= 60:
        return {"score": 10, "level": "历史中枢", "available": True}
    if historical_percentile <= 80:
        return {"score": 6, "level": "历史中高位", "available": True}
    return {"score": 3, "level": "历史高位", "available": True}


def score_risk(risk_score):
    if risk_score is None:
        return {"score": 5, "level": "数据不足", "available": False}
    if risk_score == 0:
        return {"score": 10, "level": "低风险", "available": True}
    if risk_score <= 3:
        return {"score": 8, "level": "风险较低", "available": True}
    if risk_score <= 6:
        return {"score": 6, "level": "需要关注", "available": True}
    if risk_score <= 9:
        return {"score": 3, "level": "风险较高", "available": True}
    return {"score": 0, "level": "高风险", "available": True}


def _confidence_gate(raw_score, available_count):
    """数据闸门：防止核心模块缺失时仍出现A/B级高置信结论。"""
    if available_count >= 5:
        return raw_score, "高"
    if available_count >= 3:
        return min(raw_score, 79), "中"
    return min(raw_score, 59), "低"


def _research_status(total_score, confidence, valuation_level, risk_level):
    if risk_level == "高风险":
        return "风险否决"
    if confidence == "低":
        return "数据不足"
    if total_score >= 85:
        return "核心候选"
    if total_score >= 75:
        return "优质候选"
    if total_score >= 65:
        return "重点跟踪"
    if valuation_level in {"明显低估", "较低估值"} and total_score >= 60:
        return "估值机会"
    return "观察"


def calculate_investment_score(financial_score, peer_score, valuation_gap, risk_score, historical_percentile=None):
    if peer_score is None:
        reset_relative_valuation()

    financial_available = financial_score is not None
    financial_component = 15.0 if financial_score is None else max(0, min(30, float(financial_score) * 0.30))

    peer_available = peer_score is not None
    peer_component = 12.5 if peer_score is None else max(0, min(25, float(peer_score) * 0.25))

    current_result = score_current_valuation(valuation_gap)
    historical_result = score_historical_valuation(historical_percentile)
    risk_result = score_risk(risk_score)

    relative = get_last_relative_valuation()
    relative_available = peer_score is not None and bool(relative.get("available"))
    relative_score = float(relative.get("score", 10.0)) if relative_available else 10.0

    if relative_available and current_result["available"]:
        combined_valuation = current_result["score"] * 0.70 + relative_score * 0.30
    else:
        combined_valuation = current_result["score"]

    raw_score = max(
        0,
        min(
            100,
            financial_component
            + peer_component
            + combined_valuation
            + historical_result["score"]
            + risk_result["score"],
        ),
    )

    available_count = sum(
        [
            financial_available,
            peer_available,
            current_result["available"],
            historical_result["available"],
            risk_result["available"],
        ]
    )

    total_score, confidence = _confidence_gate(round(raw_score), available_count)

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
        "score": total_score,
        "raw_score": round(raw_score),
        "rating": rating,
        "research_status": status,
        "financial_component": round(financial_component, 1),
        "peer_component": round(peer_component, 1),
        "peer_raw_score": peer_score,
        "valuation_component": round(combined_valuation, 1),
        "absolute_valuation_component": round(current_result["score"], 1),
        "relative_valuation_component": round(relative_score, 1) if relative_available else None,
        "relative_valuation_available": relative_available,
        "relative_valuation_level": relative.get("level", "数据不足"),
        "peer_median_pe": relative.get("peer_median_pe"),
        "peer_median_pb": relative.get("peer_median_pb"),
        "relative_pe_ratio": relative.get("pe_ratio"),
        "relative_pb_ratio": relative.get("pb_ratio"),
        "valuation_level": current_result["level"],
        "historical_component": round(historical_result["score"], 1),
        "historical_level": historical_result["level"],
        "historical_percentile": historical_percentile,
        "risk_component": round(risk_result["score"], 1),
        "risk_level": risk_result["level"],
        "data_available_count": available_count,
        "data_confidence": confidence,
        "data_gate": "通过" if available_count >= 3 else "未通过",
    }
