"""
ValueStock AI
投资价值综合评分模块 V2.1

V2.1 校准重点：
1. 缺失同行/历史估值数据不再直接扣0分，避免数据缺失把好公司打成低分。
2. 输出数据完整度与评分置信度。
3. 维持100分结构，但缺失项按“中性分”处理，并提示数据不足。

评分结构：
财务质量       30分
同行竞争力     25分
当前估值       20分
历史估值       15分
风险控制       10分
总分           100分
"""


def _neutral_if_missing(value, full_score, missing_label="数据不足"):
    """缺失数据不直接归零，而按中性50%处理。"""
    if value is None:
        return full_score * 0.50, missing_label, False
    return value, None, True


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


def calculate_investment_score(
    financial_score,
    peer_score,
    valuation_gap,
    risk_score,
    historical_percentile=None
):
    """综合投资价值评分。"""

    # 财务质量：通常必有；缺失时给中性分并降低置信度
    if financial_score is None:
        financial_component = 15.0
        financial_available = False
    else:
        financial_component = max(0, min(30, float(financial_score) * 0.30))
        financial_available = True

    # 同行缺失不再直接记0分
    if peer_score is None:
        peer_component = 12.5
        peer_available = False
    else:
        peer_component = max(0, min(25, float(peer_score) * 0.25))
        peer_available = True

    current_result = score_current_valuation(valuation_gap)
    historical_result = score_historical_valuation(historical_percentile)
    risk_result = score_risk(risk_score)

    total_score = (
        financial_component
        + peer_component
        + current_result["score"]
        + historical_result["score"]
        + risk_result["score"]
    )

    total_score = round(max(0, min(100, total_score)))

    available_count = sum([
        financial_available,
        peer_available,
        current_result["available"],
        historical_result["available"],
        risk_result["available"]
    ])

    confidence = (
        "高" if available_count >= 5
        else "中" if available_count >= 3
        else "低"
    )

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

    return {
        "score": total_score,
        "rating": rating,
        "financial_component": round(financial_component, 1),
        "peer_component": round(peer_component, 1),
        "peer_raw_score": peer_score,
        "valuation_component": round(current_result["score"], 1),
        "valuation_level": current_result["level"],
        "historical_component": round(historical_result["score"], 1),
        "historical_level": historical_result["level"],
        "historical_percentile": historical_percentile,
        "risk_component": round(risk_result["score"], 1),
        "risk_level": risk_result["level"],
        "data_available_count": available_count,
        "data_confidence": confidence,
    }
