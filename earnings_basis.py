"""ValueStock AI - 盈利基础 V18.3

核心修复：
1. 按报告期优先读取基本EPS，避免误用累计/季度口径。
2. TTM严格采用：最近完整年度EPS + 最新非年度报告期EPS - 上年同期EPS。
3. 年度EPS与TTM EPS分别展示，正常化EPS只用于估值分母。
4. 对异常EPS、重复报告期、日期排序做稳健处理。
5. 保留Forward EPS为观察指标，不直接进入估值。
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
    if df is None or df.empty:
        return None
    c = _find(df, ["SECURITY_CODE", "股票代码", "代码", "SECUCODE"])
    if c is None:
        return None
    for v in df[c].dropna().astype(str):
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) >= 6:
            return digits[-6:]
    return None


def _current_stock_code():
    """读取本次研究已由adaptive_valuation锁定的股票代码。"""
    try:
        import adaptive_valuation
        code = str(getattr(adaptive_valuation, "LAST_STOCK_CODE", "") or "").strip()
        if len(code) == 6 and code.isdigit():
            return code
    except Exception:
        pass
    return None


def _refresh(indicators, stock_code=None):
    """优先刷新东方财富按报告期数据；失败则安全回退原始indicators。"""
    if ak is None:
        return indicators
    code = stock_code or _code(indicators) or _current_stock_code()
    if not code:
        return indicators
    suffix = ".SH" if code.startswith("6") else ".SZ" if code.startswith(("0", "3")) else ".BJ"
    fn = getattr(ak, "stock_financial_analysis_indicator_em", None)
    if fn is None:
        return indicators

    # EM接口在不同版本可能接受不同symbol格式，依次尝试。
    symbols = [f"{code}{suffix}", code, f"{suffix[1:]}{code}"]
    for symbol in symbols:
        try:
            x = fn(symbol=symbol, indicator="按报告期")
            if x is None or x.empty:
                continue
            date_col = _find(x, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"])
            eps_col = _find(x, ["EPSJB", "基本每股收益(元)", "基本每股收益", "摊薄每股收益(元)", "摊薄每股收益", "每股收益(元)", "每股收益"])
            if date_col and eps_col:
                return x.copy()
        except Exception:
            continue
    return indicators


def calculate_earnings_realization_score(operating_cashflow_ratio=None, profit_growth=None, data_confidence="低"):
    score = 70.0
    cash = _safe_float(operating_cashflow_ratio)
    growth = _safe_float(profit_growth)
    if cash is not None:
        if cash >= 1.0:
            score += 18
        elif cash >= .8:
            score += 12
        elif cash >= .6:
            score += 5
        elif cash >= .4:
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
    coeff = 0.55 + score / 100.0 * 0.43
    level = "高" if score >= 80 else "中" if score >= 65 else "低"
    return {"score": round(score), "coefficient": round(coeff, 3), "level": level}


def build_earnings_basis(indicators, annual_eps=None, operating_cashflow_ratio=None, profit_growth=None, stock_code=None):
    """构建年度EPS、TTM EPS、正常化EPS。

    TTM规则：
        最近完整年度EPS + 最新非年度报告期EPS - 上年同期EPS
    例如：2025FY 0.68 + 2026H1 1.19 - 2025H1 0.31 = 1.56。
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
    }

    if indicators is None or indicators.empty:
        r = calculate_earnings_realization_score(operating_cashflow_ratio, profit_growth, "低")
        result.update(realization_score=r["score"], realization_coefficient=r["coefficient"], realization_level=r["level"])
        return result

    df = _refresh(indicators, stock_code=stock_code)
    date_col = _find(df, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"])
    eps_col = _find(df, ["EPSJB", "基本每股收益(元)", "基本每股收益", "摊薄每股收益(元)", "摊薄每股收益", "每股收益(元)", "每股收益"])
    if date_col is None or eps_col is None:
        r = calculate_earnings_realization_score(operating_cashflow_ratio, profit_growth, "低")
        result.update(realization_score=r["score"], realization_coefficient=r["coefficient"], realization_level=r["level"])
        return result

    x = df[[date_col, eps_col]].copy()
    x["_date"] = pd.to_datetime(x[date_col], errors="coerce")
    x["_eps"] = x[eps_col].apply(_safe_float)
    x = x.dropna(subset=["_date", "_eps"])
    x = x.sort_values("_date").drop_duplicates(subset=["_date"], keep="last").reset_index(drop=True)
    if x.empty:
        return result

    latest = x.iloc[-1]
    latest_date = latest["_date"]
    result["latest_eps"] = _safe_float(latest["_eps"])
    result["latest_report_date"] = latest_date.strftime("%Y-%m-%d")
    result["eps_source"] = "东方财富按报告期基本EPS" if df is not indicators else "财务指标基本EPS"

    # 完整年度只认12月报告期，并取最近一个完整年度。
    annual = x[x["_date"].dt.month == 12]
    if not annual.empty:
        result["annual_eps"] = _safe_float(annual.iloc[-1]["_eps"])

    annual_eps_value = result["annual_eps"]

    # 只有最新报告期不是年度报告时，才计算标准TTM。
    if latest_date.month != 12 and result["latest_eps"] is not None and annual_eps_value is not None:
        prior = x[(x["_date"].dt.year == latest_date.year - 1) & (x["_date"].dt.month == latest_date.month)]
        if not prior.empty:
            prior_eps = _safe_float(prior.iloc[-1]["_eps"])
            result["prior_same_period_eps"] = prior_eps
            if prior_eps is not None:
                ttm = annual_eps_value + result["latest_eps"] - prior_eps
                if ttm > 0:
                    result["ttm_eps"] = ttm
                    result["basis"] = "TTM EPS"
                    result["confidence"] = "高"

    # 年化EPS只作观察指标。
    if result["latest_eps"] is not None:
        mult = {3: 4.0, 6: 2.0, 9: 4.0 / 3.0, 12: 1.0}.get(int(latest_date.month))
        if mult is not None and result["latest_eps"] > 0:
            result["forward_eps_annualized"] = result["latest_eps"] * mult

    base = result["ttm_eps"] if result["ttm_eps"] is not None else result["annual_eps"]
    r = calculate_earnings_realization_score(operating_cashflow_ratio, profit_growth, result["confidence"])
    result.update(realization_score=r["score"], realization_coefficient=r["coefficient"], realization_level=r["level"])

    if base is not None and base > 0:
        annual_base = result["annual_eps"] or base
        normalized = base * r["coefficient"] + annual_base * (1.0 - r["coefficient"])
        if normalized > 0:
            result["normalized_eps"] = normalized
            result["valuation_eps"] = normalized
            result["basis"] = "正常化EPS"
            result["note"] = (
                "估值分母采用TTM/年度EPS与盈利兑现系数加权后的正常化EPS；"
                "Forward EPS仅作为观察指标。"
            )
    return result
