"""
ValueStock AI
投资价值综合评分模块 V1

功能：
1. 财务质量评分
2. 同行竞争力评分
3. 当前估值评分
4. 财务风险扣分
5. 综合投资价值评分
"""


def score_current_valuation(
    valuation_gap
):
    """
    根据当前价格相对合理价值的差距评分

    valuation_gap:
        例如 +20 表示低于合理价值20%
        -10 表示高于合理价值10%

    满分20分
    """

    if valuation_gap is None:

        return {
            "score": 0,
            "level": "数据不足"
        }


    if valuation_gap >= 30:

        return {
            "score": 20,
            "level": "明显低估"
        }


    if valuation_gap >= 20:

        return {
            "score": 18,
            "level": "较低估值"
        }


    if valuation_gap >= 10:

        return {
            "score": 16,
            "level": "偏低估值"
        }


    if valuation_gap >= 0:

        return {
            "score": 13,
            "level": "合理附近"
        }


    if valuation_gap >= -10:

        return {
            "score": 9,
            "level": "偏高估值"
        }


    if valuation_gap >= -20:

        return {
            "score": 5,
            "level": "明显偏高"
        }


    return {
        "score": 2,
        "level": "高估"
    }


def calculate_investment_score(
    financial_score,
    peer_score,
    valuation_gap,
    risk_score
):
    """
    综合投资价值评分

    财务质量：30分
    同行竞争力：25分
    当前估值：20分
    历史估值预留：15分
    风险控制：10分
    """

    # =====================================================
    # 1. 财务质量
    # =====================================================

    financial_component = 0

    if financial_score is not None:

        financial_component = (
            financial_score
            * 0.30
        )


    # =====================================================
    # 2. 同行竞争力
    # =====================================================

    peer_component = 0

    if peer_score is not None:

        peer_component = (
            peer_score
            * 0.25
        )


    # =====================================================
    # 3. 当前估值
    # =====================================================

    valuation_result = (
        score_current_valuation(
            valuation_gap
        )
    )

    valuation_component = (
        valuation_result["score"]
    )


    # =====================================================
    # 4. 风险评分
    # =====================================================

    risk_component = 10

    if risk_score is None:

        risk_component = 5

    elif risk_score == 0:

        risk_component = 10

    elif risk_score <= 3:

        risk_component = 8

    elif risk_score <= 6:

        risk_component = 6

    elif risk_score <= 9:

        risk_component = 3

    else:

        risk_component = 0


    # =====================================================
    # 5. 历史估值暂不计分
    # =====================================================

    historical_component = 0


    # =====================================================
    # 6. 总分
    # =====================================================

    total_score = (
        financial_component
        + peer_component
        + valuation_component
        + historical_component
        + risk_component
    )


    total_score = round(
        max(
            0,
            min(
                100,
                total_score
            )
        )
    )


    # =====================================================
    # 7. 综合评级
    # =====================================================

    if total_score >= 85:

        rating = (
            "A：优质公司 + 估值有吸引力"
        )


    elif total_score >= 75:

        rating = (
            "B：优质公司 + 估值合理"
        )


    elif total_score >= 65:

        rating = (
            "C：值得跟踪，等待更好价格"
        )


    elif total_score >= 50:

        rating = (
            "D：谨慎观察"
        )


    else:

        rating = (
            "E：风险较高"
        )


    return {

        "score":
            total_score,

        "rating":
            rating,

        "financial_component":
            round(
                financial_component,
                1
            ),

        "peer_component":
            round(
                peer_component,
                1
            ),

        "valuation_component":
            valuation_component,

        "historical_component":
            historical_component,

        "risk_component":
            risk_component,

        "valuation_level":
            valuation_result["level"]
    }
