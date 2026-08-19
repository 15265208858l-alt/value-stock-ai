"""
ValueStock AI
投资价值综合评分模块 V2

评分结构：

财务质量       30分
同行竞争力     25分
当前估值       20分
历史估值       15分
风险控制       10分

总分           100分
"""


# =========================================================
# 1. 当前估值评分
# =========================================================

def score_current_valuation(
    valuation_gap
):
    """
    valuation_gap：

    +30 = 当前价格比合理价值低30%
    +10 = 当前价格比合理价值低10%
      0 = 当前价格约等于合理价值
    -10 = 当前价格比合理价值高10%
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


# =========================================================
# 2. 历史估值评分
# =========================================================

def score_historical_valuation(
    historical_percentile
):
    """
    根据当前PE在历史PE中的分位进行评分。

    分位越低：
        历史估值越便宜

    分位越高：
        历史估值越贵

    满分15分
    """

    if historical_percentile is None:

        return {
            "score": 0,
            "level": "数据不足"
        }


    if historical_percentile <= 20:

        return {
            "score": 15,
            "level": "历史低位"
        }


    if historical_percentile <= 40:

        return {
            "score": 13,
            "level": "历史中低位"
        }


    if historical_percentile <= 60:

        return {
            "score": 10,
            "level": "历史中枢"
        }


    if historical_percentile <= 80:

        return {
            "score": 6,
            "level": "历史中高位"
        }


    return {
        "score": 3,
        "level": "历史高位"
    }


# =========================================================
# 3. 风险评分
# =========================================================

def score_risk(
    risk_score
):
    """
    风险越低，得到的分数越高。

    满分10分
    """

    if risk_score is None:

        return {
            "score": 5,
            "level": "数据不足"
        }


    if risk_score == 0:

        return {
            "score": 10,
            "level": "低风险"
        }


    if risk_score <= 3:

        return {
            "score": 8,
            "level": "风险较低"
        }


    if risk_score <= 6:

        return {
            "score": 6,
            "level": "需要关注"
        }


    if risk_score <= 9:

        return {
            "score": 3,
            "level": "风险较高"
        }


    return {
        "score": 0,
        "level": "高风险"
    }


# =========================================================
# 4. 综合投资评分
# =========================================================

def calculate_investment_score(
    financial_score,
    peer_score,
    valuation_gap,
    risk_score,
    historical_percentile=None
):
    """
    综合投资价值评分。

    参数：

    financial_score：
        财务质量 0-100

    peer_score：
        同行竞争力 0-100

    valuation_gap：
        当前价格相对合理价值空间

    risk_score：
        财务风险原始评分

    historical_percentile：
        当前PE历史分位
    """


    # =====================================================
    # A. 财务质量 30分
    # =====================================================

    if financial_score is None:

        financial_component = 0

    else:

        financial_component = (
            financial_score
            * 0.30
        )


    # =====================================================
    # B. 同行竞争力 25分
    # =====================================================

    if peer_score is None:

        peer_component = 0

    else:

        peer_component = (
            peer_score
            * 0.25
        )


    # =====================================================
    # C. 当前估值 20分
    # =====================================================

    current_result = (
        score_current_valuation(
            valuation_gap
        )
    )


    current_valuation_component = (
        current_result[
            "score"
        ]
    )


    # =====================================================
    # D. 历史估值 15分
    # =====================================================

    historical_result = (
        score_historical_valuation(
            historical_percentile
        )
    )


    historical_component = (
        historical_result[
            "score"
        ]
    )


    # =====================================================
    # E. 风险控制 10分
    # =====================================================

    risk_result = (
        score_risk(
            risk_score
        )
    )


    risk_component = (
        risk_result[
            "score"
        ]
    )


    # =====================================================
    # F. 最终总分
    # =====================================================

    total_score = (

        financial_component

        + peer_component

        + current_valuation_component

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
    # G. 综合评级
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

        # -------------------------------------------------
        # 总分
        # -------------------------------------------------

        "score":
            total_score,

        "rating":
            rating,

        # -------------------------------------------------
        # 财务质量
        # -------------------------------------------------

        "financial_component":
            round(
                financial_component,
                1
            ),

        # -------------------------------------------------
        # 同行竞争力
        # -------------------------------------------------

        "peer_component":
            round(
                peer_component,
                1
            ),

        "peer_raw_score":
            peer_score,

        # -------------------------------------------------
        # 当前估值
        # -------------------------------------------------

        "valuation_component":
            current_valuation_component,

        "valuation_level":
            current_result[
                "level"
            ],

        # -------------------------------------------------
        # 历史估值
        # -------------------------------------------------

        "historical_component":
            historical_component,

        "historical_level":
            historical_result[
                "level"
            ],

        "historical_percentile":
            historical_percentile,

        # -------------------------------------------------
        # 风险
        # -------------------------------------------------

        "risk_component":
            risk_component,

        "risk_level":
            risk_result[
                "level"
            ]
    }
