"""
ValueStock AI
财务风险分析模块

功能：
1. 经营现金流 / 净利润
2. 应收账款 / 营收
3. 存货 / 营收
4. ROE风险
5. 资产负债率风险
6. 综合风险评分
"""


def safe_ratio(a, b):
    """安全计算比例"""

    if a is None:
        return None

    if b is None:
        return None

    if b == 0:
        return None

    return a / b


def analyze_cashflow_quality(
    operating_cashflow,
    net_profit
):
    """
    分析经营现金流与净利润匹配程度
    """

    ratio = safe_ratio(
        operating_cashflow,
        net_profit
    )

    if ratio is None:

        return {
            "ratio": None,
            "score": 0,
            "level": "数据不足",
            "message": "缺少经营现金流或净利润数据。"
        }


    if ratio >= 1:

        return {
            "ratio": ratio,
            "score": 0,
            "level": "优秀",
            "message":
                "经营现金流能够覆盖净利润，利润现金含量较好。"
        }


    if ratio >= 0.7:

        return {
            "ratio": ratio,
            "score": 1,
            "level": "良好",
            "message":
                "经营现金流与净利润基本匹配，需要继续观察。"
        }


    if ratio >= 0:

        return {
            "ratio": ratio,
            "score": 2,
            "level": "需要关注",
            "message":
                "经营现金流明显低于净利润，需要进一步排查利润质量。"
        }


    return {
        "ratio": ratio,
        "score": 3,
        "level": "高风险",
        "message":
            "经营现金流为负，而净利润可能为正，需要重点排查。"
    }


def analyze_receivable(
    receivable,
    revenue
):
    """
    分析应收账款占营业收入比例
    """

    ratio = safe_ratio(
        receivable,
        revenue
    )

    if ratio is None:

        return {
            "ratio": None,
            "score": 0,
            "level": "数据不足",
            "message":
                "缺少应收账款或营业收入数据。"
        }


    if ratio > 0.40:

        return {
            "ratio": ratio,
            "score": 3,
            "level": "高风险信号",
            "message":
                "应收账款占营业收入比例较高，需要重点检查回款能力。"
        }


    if ratio > 0.25:

        return {
            "ratio": ratio,
            "score": 1,
            "level": "需要关注",
            "message":
                "应收账款占比较高，需要结合历史趋势观察。"
        }


    return {
        "ratio": ratio,
        "score": 0,
        "level": "正常",
        "message":
            "应收账款/营业收入比例暂未显示明显异常。"
    }


def analyze_inventory(
    inventory,
    revenue
):
    """
    分析存货占营业收入比例
    """

    ratio = safe_ratio(
        inventory,
        revenue
    )

    if ratio is None:

        return {
            "ratio": None,
            "score": 0,
            "level": "数据不足",
            "message":
                "缺少存货或营业收入数据。"
        }


    if ratio > 0.50:

        return {
            "ratio": ratio,
            "score": 3,
            "level": "高风险信号",
            "message":
                "存货相对营业规模较高，需要检查库存周转和减值风险。"
        }


    if ratio > 0.30:

        return {
            "ratio": ratio,
            "score": 1,
            "level": "需要关注",
            "message":
                "存货占比需要继续观察。"
        }


    return {
        "ratio": ratio,
        "score": 0,
        "level": "正常",
        "message":
            "存货/营业收入比例暂未显示明显异常。"
    }


def analyze_roe(roe):
    """
    分析ROE
    """

    if roe is None:

        return {
            "score": 0,
            "level": "数据不足",
            "message": "缺少ROE数据。"
        }


    if roe >= 15:

        return {
            "score": 0,
            "level": "良好",
            "message":
                f"ROE为{roe:.2f}%，资本回报能力较好。"
        }


    if roe >= 10:

        return {
            "score": 1,
            "level": "一般",
            "message":
                f"ROE为{roe:.2f}%，资本回报能力一般。"
        }


    return {
        "score": 2,
        "level": "偏弱",
        "message":
            f"ROE为{roe:.2f}%，需要进一步研究盈利能力。"
    }


def analyze_debt_ratio(
    debt_ratio
):
    """
    分析资产负债率
    """

    if debt_ratio is None:

        return {
            "score": 0,
            "level": "数据不足",
            "message":
                "缺少资产负债率数据。"
        }


    if debt_ratio < 50:

        return {
            "score": 0,
            "level": "稳健",
            "message":
                f"资产负债率为{debt_ratio:.2f}%，整体较稳健。"
        }


    if debt_ratio < 70:

        return {
            "score": 1,
            "level": "需要关注",
            "message":
                f"资产负债率为{debt_ratio:.2f}%，需要持续观察。"
        }


    return {
        "score": 3,
        "level": "高风险信号",
        "message":
            f"资产负债率为{debt_ratio:.2f}%，杠杆水平较高。"
    }


def analyze_financial_risk(
    operating_cashflow,
    net_profit,
    receivable,
    revenue,
    inventory,
    roe,
    debt_ratio
):
    """
    综合财务风险分析
    """

    cashflow_result = analyze_cashflow_quality(
        operating_cashflow,
        net_profit
    )


    receivable_result = analyze_receivable(
        receivable,
        revenue
    )


    inventory_result = analyze_inventory(
        inventory,
        revenue
    )


    roe_result = analyze_roe(
        roe
    )


    debt_result = analyze_debt_ratio(
        debt_ratio
    )


    total_score = (
        cashflow_result["score"]
        + receivable_result["score"]
        + inventory_result["score"]
        + roe_result["score"]
        + debt_result["score"]
    )


    if total_score == 0:

        level = "低风险"


    elif total_score <= 3:

        level = "风险较低"


    elif total_score <= 6:

        level = "需要关注"


    elif total_score <= 9:

        level = "风险较高"


    else:

        level = "高风险"


    risk_items = []


    results = [
        cashflow_result,
        receivable_result,
        inventory_result,
        roe_result,
        debt_result
    ]


    for result in results:

        if result["score"] > 0:

            risk_items.append(
                result["message"]
            )


    return {

        "score": total_score,

        "level": level,

        "cashflow": cashflow_result,

        "receivable": receivable_result,

        "inventory": inventory_result,

        "roe": roe_result,

        "debt": debt_result,

        "risk_items": risk_items
    }
