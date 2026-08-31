"""ValueStock AI - 盈利基础 V18.1
修复季度累计EPS与TTM错配；优先使用东方财富按报告期的基本EPS。
"""
from __future__ import annotations
import pandas as pd

try:
    import akshare as ak
except Exception:
    ak = None


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
    if df is None or df.empty:
        return None
    for n in names:
        if n in df.columns:
            return n
    return None


def _code(df):
    c = _find(df, ["SECURITY_CODE", "股票代码", "代码", "SECUCODE"])
    if c is None:
        return None
    for v in df[c].dropna().astype(str):
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) >= 6:
            return digits[-6:]
    return None


def _refresh(indicators):
    if ak is None or indicators is None or indicators.empty:
        return indicators
    code = _code(indicators)
    if not code:
        return indicators
    suffix = ".SH" if code.startswith(("6", "68")) else ".SZ" if code.startswith(("0", "3")) else ".BJ"
    for symbol in [f"{code}{suffix}", code, f"{suffix[1:]}{code}"]:
        try:
            fn = getattr(ak, "stock_financial_analysis_indicator_em", None)
            if fn is None:
                break
            x = fn(symbol=symbol, indicator="按报告期")
            if x is not None and not x.empty and "REPORT_DATE" in x.columns and any(c in x.columns for c in ["EPSJB", "基本每股收益(元)"]):
                return x.copy()
        except Exception:
            continue
    return indicators


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


def build_earnings_basis(indicators, annual_eps=None, operating_cashflow_ratio=None, profit_growth=None):
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
        r = calculate_earnings_realization_score(operating_cashflow_ratio, profit_growth, "低")
        result.update(realization_score=r["score"], realization_coefficient=r["coefficient"], realization_level=r["level"])
        return result

    df = _refresh(indicators)
    date_col = _find(df, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"])
    eps_col = _find(df, ["EPSJB", "基本每股收益(元)", "基本每股收益", "摊薄每股收益(元)", "摊薄每股收益", "每股收益(元)", "每股收益"])
    if date_col is None or eps_col is None:
        return result

    x = df[[date_col, eps_col]].copy()
    x["_date"] = pd.to_datetime(x[date_col], errors="coerce")
    x["_eps"] = x[eps_col].apply(_safe_float)
    x = x.dropna(subset=["_date", "_eps"]).sort_values("_date").reset_index(drop=True)
    if x.empty:
        return result

    latest = x.iloc[-1]
    latest_date = latest["_date"]
    result["latest_eps"] = _safe_float(latest["_eps"])

    annual = x[x["_date"].dt.month == 12]
    if not annual.empty:
        result["annual_eps"] = _safe_float(annual.iloc[-1]["_eps"])

    annual_eps_value = result["annual_eps"]
    prior = x[(x["_date"].dt.year == latest_date.year - 1) & (x["_date"].dt.month == latest_date.month)]
    if not prior.empty:
        result["prior_same_period_eps"] = _safe_float(prior.iloc[-1]["_eps"])

    prior_eps = result["prior_same_period_eps"]
    if latest_date.month != 12 and annual_eps_value is not None and prior_eps is not None and result["latest_eps"] is not None:
        ttm = annual_eps_value + result["latest_eps"] - prior_eps
        if ttm > 0:
            result["ttm_eps"] = ttm
            result["basis"] = "TTM EPS"
            result["confidence"] = "高"

    if result["latest_eps"] is not None:
        mult = {3: 4.0, 6: 2.0, 9: 4.0 / 3.0, 12: 1.0}.get(int(latest_date.month))
        if mult is not None and result["latest_eps"] > 0:
            result["forward_eps_annualized"] = result["latest_eps"] * mult

    base = result["ttm_eps"] or result["annual_eps"]
    r = calculate_earnings_realization_score(operating_cashflow_ratio, profit_growth, result["confidence"])
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
