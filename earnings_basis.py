"""
ValueStock AI
前瞻盈利基础模块 V16.8

目标：
1. 计算年度 EPS、TTM EPS、年化 EPS。
2. 增加“正常化 EPS”概念，避免高速成长或单期异常利润直接被资本化。
3. 引入盈利兑现系数：经营现金流、利润增长、数据完整性越好，正常化折扣越小。
4. 不把预测 EPS 当成已实现事实；Forward EPS 仅作为观察值。
"""

from __future__ import annotations

import pandas as pd


def _safe_float(value):
    try:
        if value is None:
            return None
        text = str(value).strip().replace(",", "").replace("%", "")
        if text in {"", "--", "None", "none", "NaN", "nan"}:
            return None
        return float(text)
    except Exception:
        return None


def _find_column(df, candidates):
    if df is None or df.empty:
        return None
    for column in candidates:
        if column in df.columns:
            return column
    return None


def calculate_earnings_realization_score(
    operating_cashflow_ratio=None,
    profit_growth=None,
    data_confidence="低",
):
    """计算盈利兑现系数（0.55～0.98）。"""

    score = 70.0
    cash_ratio = _safe_float(operating_cashflow_ratio)
    growth = _safe_float(profit_growth)

    if cash_ratio is not None:
        if cash_ratio >= 1.00:
            score += 18
        elif cash_ratio >= 0.80:
            score += 12
        elif cash_ratio >= 0.60:
            score += 5
        elif cash_ratio >= 0.40:
            score -= 5
        else:
            score -= 15
    else:
        score -= 8

    if growth is not None:
        if growth >= 80:
            score -= 6
        elif growth >= 50:
            score -= 3
        elif growth >= 30:
            score -= 1
        elif growth >= 10:
            score += 2
        elif growth < 0:
            score -= 5

    if data_confidence == "高":
        score += 4
    elif data_confidence == "低":
        score -= 6

    score = max(40.0, min(95.0, score))
    coefficient = 0.55 + (score / 100.0) * 0.43

    if score >= 80:
        level = "高"
    elif score >= 65:
        level = "中"
    else:
        level = "低"

    return {
        "score": round(score),
        "coefficient": round(coefficient, 3),
        "level": level,
    }


def build_earnings_basis(
    indicators,
    annual_eps=None,
    operating_cashflow_ratio=None,
    profit_growth=None,
):
    """构建估值盈利基础。"""

    result = {
        "annual_eps": _safe_float(annual_eps),
        "latest_eps": None,
        "prior_same_period_eps": None,
        "ttm_eps": None,
        "forward_eps_annualized": None,
        "normalized_eps": _safe_float(annual_eps),
        "valuation_eps": _safe_float(annual_eps),
        "basis": "FY年度EPS",
        "confidence": "低",
        "realization_score": None,
        "realization_coefficient": None,
        "realization_level": "低",
        "note": "数据不足，暂使用最近完整年度EPS。",
    }

    if indicators is None or indicators.empty:
        realization = calculate_earnings_realization_score(
            operating_cashflow_ratio,
            profit_growth,
            "低",
        )
        result.update({
            "realization_score": realization["score"],
            "realization_coefficient": realization["coefficient"],
            "realization_level": realization["level"],
        })
        return result

    date_col = _find_column(
        indicators,
        ["日期", "报告期", "报告日期", "截止日期", "REPORT_DATE"],
    )
    eps_col = _find_column(
        indicators,
        [
            "摊薄每股收益(元)",
            "摊薄每股收益",
            "基本每股收益(元)",
            "基本每股收益",
            "每股收益(元)",
            "每股收益",
            "EPSJB",
        ],
    )

    if date_col is None or eps_col is None:
        return result

    df = indicators[[date_col, eps_col]].copy()
    df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["_eps"] = df[eps_col].apply(_safe_float)
    df = df.dropna(subset=["_date", "_eps"]).sort_values("_date").reset_index(drop=True)

    if df.empty:
        return result

    latest = df.iloc[-1]
    latest_date = latest["_date"]
    result["latest_eps"] = _safe_float(latest["_eps"])

    annual_df = df[df["_date"].dt.month == 12].copy()
    if not annual_df.empty:
        annual_latest = annual_df.iloc[-1]
        annual_value = _safe_float(annual_latest["_eps"])
        if annual_value is not None:
            result["annual_eps"] = annual_value

    annual_eps_value = result["annual_eps"]

    prior = df[
        (df["_date"].dt.year == latest_date.year - 1)
        & (df["_date"].dt.month == latest_date.month)
    ]

    if prior.empty:
        prior = df[
            (df["_date"].dt.year == latest_date.year - 1)
            & (abs(df["_date"].dt.month - latest_date.month) <= 1)
        ]

    if not prior.empty:
        result["prior_same_period_eps"] = _safe_float(prior.iloc[-1]["_eps"])

    prior_eps = result["prior_same_period_eps"]

    if (
        annual_eps_value is not None
        and result["latest_eps"] is not None
        and prior_eps is not None
        and latest_date.month != 12
    ):
        ttm_eps = annual_eps_value + result["latest_eps"] - prior_eps
        if ttm_eps > 0:
            result["ttm_eps"] = ttm_eps
            result["basis"] = "TTM EPS"
            result["confidence"] = "高"

    if result["latest_eps"] is not None:
        month = int(latest_date.month)
        multiplier = {3: 4.0, 6: 2.0, 9: 4.0 / 3.0, 12: 1.0}.get(month)
        if multiplier is not None:
            annualized = result["latest_eps"] * multiplier
            if annualized > 0:
                result["forward_eps_annualized"] = annualized

    base_eps = result["ttm_eps"] or result["annual_eps"]

    realization = calculate_earnings_realization_score(
        operating_cashflow_ratio=operating_cashflow_ratio,
        profit_growth=profit_growth,
        data_confidence=result["confidence"],
    )

    result["realization_score"] = realization["score"]
    result["realization_coefficient"] = realization["coefficient"]
    result["realization_level"] = realization["level"]

    if base_eps is not None and base_eps > 0:
        annual_base = result["annual_eps"] or base_eps
        normalized = (
            base_eps * realization["coefficient"]
            + annual_base * (1.0 - realization["coefficient"])
        )
        if normalized > 0:
            result["normalized_eps"] = normalized
            result["valuation_eps"] = normalized
            result["basis"] = "正常化EPS"
            result["note"] = (
                "估值分母采用TTM/年度EPS与盈利兑现系数加权后的正常化EPS；"
                "Forward EPS仅作为观察指标。"
            )

    return result
