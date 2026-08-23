"""
ValueStock AI
投资价值综合评分模块 V2.2

升级：
1. 缺失同行/历史估值数据不直接归零。
2. 当前估值分项加入“相对同行估值”校准。
3. 相对估值使用同行PE/PB中位数，避免极端值污染平均数。
4. 保留100分主结构，增加相对估值诊断字段。
"""

from peer_compare import get_last_relative_valuation


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
    historical_percentile=None,
):
    if financial_score is None:
        financial_component = 15.0
        financial_available = False
    else:
        financial_component = max(0, min(30, float(financial_score) * 0.30))
        financial_available = True

    if peer_score is None:
        peer_component = 12.5
        peer_available = False
    else:
        peer_component = max(0, min(25, float(peer_score) * 0.25))
        peer_available = True

    current_result = score_current_valuation(valuation_gap)
    historical_result = score_historical_valuation(historical_percentile)
    risk_result = score_risk(risk_score)

    # V17.0：绝对估值70% + 相对同行估值30%
    relative = get_last_relative_valuation()
    relative_available = bool(relative.get("available"))
    relative_score = float(relative.get("score", 10.0)) if relative_available else 10.0

    if relative_available and current_result["available"]:
        combined_valuation = current_result["score"] * 0.70 + relative_score * 0.30
        valuation_level = current_result["level"]
    else:
        combined_valuation = current_result["score"]
        valuation_level = current_result["level"]

    total_score = round(
        max(
            0,
            min(
                100,
                financial_component
                + peer_component
                + combined_valuation
                + historical_result["score"]
                + risk_result["score"]
            ),
        )
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

    confidence = "高" if available_count >= 5 else "中" if available_count >= 3 else "低"

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
        "valuation_component": round(combined_valuation, 1),
        "absolute_valuation_component": round(current_result["score"], 1),
        "relative_valuation_component": round(relative_score, 1) if relative_available else None,
        "relative_valuation_available": relative_available,
        "relative_valuation_level": relative.get("level", "数据不足"),
        "peer_median_pe": relative.get("peer_median_pe"),
        "peer_median_pb": relative.get("peer_median_pb"),
        "relative_pe_ratio": relative.get("pe_ratio"),
        "relative_pb_ratio": relative.get("pb_ratio"),
        "valuation_level": valuation_level,
        "historical_component": round(historical_result["score"], 1),
        "historical_level": historical_result["level"],
        "historical_percentile": historical_percentile,
        "risk_component": round(risk_result["score"], 1),
        "risk_level": risk_result["level"],
        "data_available_count": available_count,
        "data_confidence": confidence,
    }
