"""
ValueStock AI
前瞻盈利基础模块 V16.7

目标：
1. 从已有财务指标中提取年度EPS、最新报告期EPS。
2. 在数据足够时计算TTM EPS：
   TTM EPS = 最近完整年度EPS + 最新报告期EPS - 上年同期EPS
3. 对成长科技公司优先使用TTM EPS作为估值分母，减少历史年度EPS滞后造成的系统性高估PE。
4. 不直接伪造未来利润预测；Forward EPS只作为观察指标，并标注为“年化推算”。
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


def build_earnings_basis(indicators, annual_eps=None):
    """从原始财务指标构建估值盈利基础。"""

    result = {
        "annual_eps": _safe_float(annual_eps),
        "latest_eps": None,
        "prior_same_period_eps": None,
        "ttm_eps": None,
        "forward_eps_annualized": None,
        "valuation_eps": _safe_float(annual_eps),
        "basis": "FY年度EPS",
        "confidence": "低",
        "note": "数据不足，暂使用最近完整年度EPS。",
    }

    if indicators is None or indicators.empty:
        return result

    date_col = _find_column(
        indicators,
        ["日期", "报告期", "报告日期", "截止日期", "REPORT_DATE"]
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
        ]
    )

    if date_col is None or eps_col is None:
        return result

    df = indicators[[date_col, eps_col]].copy()
    df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["_eps"] = df[eps_col].apply(_safe_float)
    df = df.dropna(subset=["_date"]).sort_values("_date").reset_index(drop=True)

    if df.empty:
        return result

    latest = df.iloc[-1]
    latest_date = latest["_date"]
    latest_eps = _safe_float(latest["_eps"])
    result["latest_eps"] = latest_eps

    # 年度EPS：优先取最近12月报告期。
    annual_df = df[df["_date"].dt.month == 12].copy()
    if not annual_df.empty:
        annual_latest = annual_df.iloc[-1]
        annual_eps_value = _safe_float(annual_latest["_eps"])
        if annual_eps_value is not None:
            result["annual_eps"] = annual_eps_value

    annual_eps_value = result["annual_eps"]

    # 上年同期：同月份优先；找不到时允许按季度附近匹配。
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
        and latest_eps is not None
        and prior_eps is not None
        and latest_date.month != 12
    ):
        ttm_eps = annual_eps_value + latest_eps - prior_eps
        if ttm_eps > 0:
            result["ttm_eps"] = ttm_eps
            result["valuation_eps"] = ttm_eps
            result["basis"] = "TTM EPS"
            result["confidence"] = "高"
            result["note"] = "已使用最近12个月TTM EPS作为估值分母，降低年度EPS滞后影响。"

    # 年化推算只用于观察，不直接作为主估值分母。
    if latest_eps is not None:
        month = int(latest_date.month)
        multiplier_map = {3: 4.0, 6: 2.0, 9: 4.0 / 3.0, 12: 1.0}
        multiplier = multiplier_map.get(month)
        if multiplier is not None:
            annualized = latest_eps * multiplier
            if annualized > 0:
                result["forward_eps_annualized"] = annualized

    return result
