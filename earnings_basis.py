"""ValueStock AI - 盈利基础 V19.0

性能原则：build_earnings_basis 只使用页面已经获取的 indicators / profit_report。
绝不在估值阶段再次访问 AkShare，避免第七模块出现长时间等待。
"""
from __future__ import annotations
import pandas as pd


def _safe_float(v):
    try:
        if v is None:
            return None
        s = str(v).strip().replace(",", "").replace("%", "")
        if s in {"", "--", "None", "none", "NaN", "nan"}:
            return None
        return float(s)
    except Exception:
        return None


def _find(df, names):
    if df is None or getattr(df, "empty", True):
        return None
    for n in names:
        if n in df.columns:
            return n
    return None


def _series_from_df(df, date_names, eps_names):
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame(columns=["_date", "_eps"])
    try:
        date_col = _find(df, date_names)
        eps_col = _find(df, eps_names)
        if date_col is None or eps_col is None:
            return pd.DataFrame(columns=["_date", "_eps"])
        x = df[[date_col, eps_col]].copy()
        x["_date"] = pd.to_datetime(x[date_col], errors="coerce")
        x["_eps"] = x[eps_col].apply(_safe_float)
        x = x.dropna(subset=["_date", "_eps"])
        return x.sort_values("_date").drop_duplicates("_date", keep="last").reset_index(drop=True)[["_date", "_eps"]]
    except Exception:
        return pd.DataFrame(columns=["_date", "_eps"])


def calculate_earnings_realization_score(operating_cashflow_ratio=None, profit_growth=None, data_confidence="低"):
    score = 70.0
    cash = _safe_float(operating_cashflow_ratio)
    growth = _safe_float(profit_growth)
    if cash is not None:
        if cash >= 1.0: score += 18
        elif cash >= .8: score += 12
        elif cash >= .6: score += 5
        elif cash >= .4: score -= 5
        else: score -= 15
    else:
        score -= 8
    if growth is not None:
        if growth >= 80: score -= 6
        elif growth >= 50: score -= 3
        elif growth >= 30: score -= 1
        elif growth >= 10: score += 2
        elif growth < 0: score -= 5
    if data_confidence == "高": score += 4
    elif data_confidence == "低": score -= 6
    score = max(40.0, min(95.0, score))
    coeff = 0.55 + score / 100.0 * 0.43
    level = "高" if score >= 80 else "中" if score >= 65 else "低"
    return {"score": round(score), "coefficient": round(coeff, 3), "level": level}


def build_earnings_basis(indicators, annual_eps=None, operating_cashflow_ratio=None, profit_growth=None, stock_code=None, profit_report=None):
    """构建年度EPS、TTM EPS、正常化EPS。

    注意：stock_code 参数仅为兼容旧调用保留，不会触发网络请求。
    """
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
        "eps_source": "财务指标回退",
        "latest_report_date": None,
        "ttm_formula": None,
    }

    # 只使用已经加载的数据：利润表优先，财务指标其次。
    report_series = _series_from_df(
        profit_report,
        ["REPORT_DATE", "报告日期", "报告期", "截止日期", "日期"],
        ["基本每股收益", "基本每股收益(元)", "基本每股收益（元）", "每股收益", "每股收益(元)", "每股收益（元）", "EPSJB", "基本每股收益（元/股）", "基本每股收益(元/股)"],
    )
    indicator_series = _series_from_df(
        indicators,
        ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"],
        ["EPSJB", "基本每股收益(元)", "基本每股收益", "摊薄每股收益(元)", "摊薄每股收益", "每股收益(元)", "每股收益"],
    )

    x = report_series if not report_series.empty else indicator_series
    source_name = "已加载利润表" if not report_series.empty else "已加载财务指标"
    confidence = "高" if not x.empty else "低"

    if x.empty:
        r = calculate_earnings_realization_score(operating_cashflow_ratio, profit_growth, "低")
        result.update(realization_score=r["score"], realization_coefficient=r["coefficient"], realization_level=r["level"])
        return result

    latest = x.iloc[-1]
    latest_date = latest["_date"]
    latest_eps = _safe_float(latest["_eps"])
    result["latest_eps"] = latest_eps
    result["latest_report_date"] = latest_date.strftime("%Y-%m-%d")
    result["eps_source"] = source_name

    annual = x[x["_date"].dt.month == 12]
    if not annual.empty:
        result["annual_eps"] = _safe_float(annual.iloc[-1]["_eps"])

    annual_eps_value = result["annual_eps"]
    if latest_date.month != 12 and latest_eps is not None and annual_eps_value is not None:
        prior = x[(x["_date"].dt.year == latest_date.year - 1) & (x["_date"].dt.month == latest_date.month)]
        if not prior.empty:
            prior_eps = _safe_float(prior.iloc[-1]["_eps"])
            result["prior_same_period_eps"] = prior_eps
            if prior_eps is not None:
                ttm = annual_eps_value + latest_eps - prior_eps
                if ttm > 0:
                    result["ttm_eps"] = ttm
                    result["basis"] = "TTM EPS"
                    result["confidence"] = "高"
                    result["ttm_formula"] = f"{annual_eps_value:.4f} + {latest_eps:.4f} - {prior_eps:.4f}"

    if latest_eps is not None and latest_eps > 0:
        mult = {3: 4.0, 6: 2.0, 9: 4.0 / 3.0, 12: 1.0}.get(int(latest_date.month))
        if mult is not None:
            result["forward_eps_annualized"] = latest_eps * mult

    base = result["ttm_eps"] if result["ttm_eps"] is not None else result["annual_eps"]
    r = calculate_earnings_realization_score(operating_cashflow_ratio, profit_growth, confidence)
    result.update(realization_score=r["score"], realization_coefficient=r["coefficient"], realization_level=r["level"])

    if base is not None and base > 0:
        annual_base = result["annual_eps"] or base
        normalized = base * r["coefficient"] + annual_base * (1.0 - r["coefficient"])
        if normalized > 0:
            result["normalized_eps"] = normalized
            result["valuation_eps"] = normalized
            result["basis"] = "正常化EPS"
            result["note"] = "估值分母采用TTM/年度EPS与盈利兑现系数加权后的正常化EPS；Forward EPS仅作为观察指标。"
    return result
