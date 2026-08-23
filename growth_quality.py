"""
ValueStock AI
成长质量与动态估值模块 V16.9

原则：
1. 成长PE不再只由ROE决定。
2. 综合营收增长、净利润增长、ROE、经营现金流兑现、TTM盈利动能。
3. 高增长但现金流差的公司必须打折。
4. 历史估值处于极高区域时，对合理PE做适度风险折扣。
"""


def _num(v):
    try:
        if v is None:
            return None
        text = str(v).strip().replace(",", "").replace("%", "")
        if text in {"", "--", "None", "none", "nan", "NaN"}:
            return None
        return float(text)
    except Exception:
        return None


def calculate_growth_quality(
    revenue_growth=None,
    profit_growth=None,
    roe=None,
    cashflow_ratio=None,
    ttm_eps=None,
    annual_eps=None,
    historical_percentile=None,
):
    """返回0-100成长质量评分及分项。"""
    rg = _num(revenue_growth)
    pg = _num(profit_growth)
    ro = _num(roe)
    cf = _num(cashflow_ratio)
    te = _num(ttm_eps)
    ae = _num(annual_eps)
    hp = _num(historical_percentile)

    score = 50.0

    # 营收成长：最多15分
    revenue_points = 0.0
    if rg is not None:
        if rg >= 40:
            revenue_points = 15
        elif rg >= 25:
            revenue_points = 12
        elif rg >= 15:
            revenue_points = 8
        elif rg >= 5:
            revenue_points = 4
        elif rg < 0:
            revenue_points = -6
    score += revenue_points

    # 利润成长：最多15分，但过高增长不无限奖励
    profit_points = 0.0
    if pg is not None:
        if pg >= 80:
            profit_points = 13
        elif pg >= 50:
            profit_points = 11
        elif pg >= 30:
            profit_points = 9
        elif pg >= 15:
            profit_points = 6
        elif pg >= 5:
            profit_points = 2
        elif pg < 0:
            profit_points = -6
    score += profit_points

    # ROE：最多12分
    roe_points = 0.0
    if ro is not None:
        if ro >= 25:
            roe_points = 12
        elif ro >= 20:
            roe_points = 10
        elif ro >= 15:
            roe_points = 7
        elif ro >= 10:
            roe_points = 4
        elif ro < 5:
            roe_points = -3
    score += roe_points

    # 现金流兑现：最多15分，弱现金流会明显压制成长质量
    cash_points = 0.0
    if cf is not None:
        if cf >= 1.0:
            cash_points = 15
        elif cf >= 0.8:
            cash_points = 11
        elif cf >= 0.6:
            cash_points = 7
        elif cf >= 0.4:
            cash_points = 1
        elif cf >= 0:
            cash_points = -8
        else:
            cash_points = -15
    else:
        cash_points = -5
    score += cash_points

    # TTM盈利动能：最多5分
    momentum_points = 0.0
    if te is not None and ae is not None and ae > 0:
        ratio = te / ae
        if ratio >= 1.5:
            momentum_points = 5
        elif ratio >= 1.2:
            momentum_points = 3
        elif ratio >= 1.05:
            momentum_points = 1
        elif ratio < 0.9:
            momentum_points = -3
    score += momentum_points

    # 历史高估只作为风险提示，不直接把优秀成长公司判死刑
    history_penalty = 0.0
    if hp is not None:
        if hp >= 95 and cash_points <= 1:
            history_penalty = -8
        elif hp >= 90:
            history_penalty = -4
    score += history_penalty

    score = int(round(max(0, min(100, score))))

    if score >= 80:
        level = "优秀"
    elif score >= 70:
        level = "较强"
    elif score >= 60:
        level = "中等"
    elif score >= 45:
        level = "偏弱"
    else:
        level = "较弱"

    return {
        "score": score,
        "level": level,
        "revenue_points": revenue_points,
        "profit_points": profit_points,
        "roe_points": roe_points,
        "cash_points": cash_points,
        "momentum_points": momentum_points,
        "history_penalty": history_penalty,
    }


def get_dynamic_growth_pe(growth_quality_score, historical_percentile=None, cashflow_ratio=None):
    """根据成长质量返回保守/中性/乐观PE，并做高估值风险修正。"""
    score = int(growth_quality_score or 0)
    hp = _num(historical_percentile)
    cf = _num(cashflow_ratio)

    if score >= 90:
        pe_c, pe_n, pe_o = 28.0, 34.0, 40.0
    elif score >= 80:
        pe_c, pe_n, pe_o = 25.0, 31.0, 37.0
    elif score >= 70:
        pe_c, pe_n, pe_o = 22.0, 28.0, 34.0
    elif score >= 60:
        pe_c, pe_n, pe_o = 19.0, 24.0, 30.0
    elif score >= 50:
        pe_c, pe_n, pe_o = 17.0, 22.0, 27.0
    else:
        pe_c, pe_n, pe_o = 14.0, 18.0, 23.0

    # 极高历史分位 + 现金兑现一般：估值带宽适度收缩
    if hp is not None and hp >= 95:
        pe_c *= 0.92
        pe_n *= 0.90
        pe_o *= 0.90

    # 现金流为负时进一步限制成长溢价
    if cf is not None and cf < 0:
        pe_c *= 0.95
        pe_n *= 0.92
        pe_o *= 0.92

    return {
        "conservative_pe": round(pe_c, 1),
        "normal_pe": round(pe_n, 1),
        "optimistic_pe": round(pe_o, 1),
    }
