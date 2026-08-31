"""ValueStock AI - 财务分析 V18.1
核心原则：优先使用东方财富“按报告期”结构化指标；旧新浪接口仅作兜底。
重点修复：年度EPS/BPS错期、季度累计值误当年度值、保险/金融股指标异常。
"""
from __future__ import annotations
import pandas as pd

try:
    import akshare as ak
except Exception:
    ak = None


def safe_float(value):
    try:
        if value is None:
            return None
        text = str(value).strip().replace(",", "").replace("%", "")
        if text in {"", "--", "None", "none", "NaN", "nan"}:
            return None
        return float(text)
    except Exception:
        return None


def _find(df, names):
    if df is None or df.empty:
        return None
    for name in names:
        if name in df.columns:
            return name
    return None


def _extract_code(df):
    col = _find(df, ["SECURITY_CODE", "股票代码", "代码", "SECUCODE"])
    if col is None:
        return None
    for value in df[col].dropna().astype(str):
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) >= 6:
            return digits[-6:]
    return None


def _refresh_eastmoney(indicators):
    """刷新为东财按报告期数据。失败则返回原数据。"""
    if ak is None or indicators is None or indicators.empty:
        return indicators
    code = _extract_code(indicators)
    if not code:
        return indicators

    suffix = ".SH" if code.startswith(("6", "68")) else ".SZ" if code.startswith(("0", "3")) else ".BJ"
    candidates = [f"{code}{suffix}", f"{code}", f"{suffix[1:]}{code}"]
    for symbol in candidates:
        try:
            fn = getattr(ak, "stock_financial_analysis_indicator_em", None)
            if fn is None:
                break
            df = fn(symbol=symbol, indicator="按报告期")
            if df is not None and not df.empty and any(c in df.columns for c in ["EPSJB", "BPS", "REPORT_DATE"]):
                return df.copy()
        except Exception:
            continue
    return indicators


def _prepare(df):
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy()
    date_col = _find(x, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"])
    if date_col is None:
        return pd.DataFrame()
    x["_分析日期"] = pd.to_datetime(x[date_col], errors="coerce")
    x = x.dropna(subset=["_分析日期"]).sort_values("_分析日期").reset_index(drop=True)
    return x


def _value(row, df, candidates):
    col = _find(df, candidates)
    return safe_float(row[col]) if col else None


def process_financial_indicators(indicators):
    result = {"latest": {}, "annual": {}, "trend": pd.DataFrame()}
    if indicators is None or indicators.empty:
        return result

    source = _refresh_eastmoney(indicators)
    df = _prepare(source)
    if df.empty:
        return result

    latest = df.iloc[-1]
    annual_df = df[df["_分析日期"].dt.month == 12].copy()
    annual = annual_df.iloc[-1] if not annual_df.empty else latest

    roe_cols = ["ROEJQ", "加权净资产收益率(%)", "加权净资产收益率", "摊薄净资产收益率(%)", "净资产收益率(%)", "净资产收益率"]
    rev_cols = ["TOTALOPERATEREVETZ", "主营业务收入增长率(%)", "主营业务收入增长率", "营业收入增长率(%)", "营业收入增长率"]
    profit_cols = ["PARENTNETPROFITTZ", "净利润增长率(%)", "净利润增长率", "归属净利润同比增长(%)"]
    debt_cols = ["ZCFZL", "资产负债率(%)", "资产负债率"]
    eps_cols = ["EPSJB", "基本每股收益(元)", "基本每股收益", "摊薄每股收益(元)", "摊薄每股收益", "每股收益(元)", "每股收益", "EPSXS"]
    bps_cols = ["BPS", "每股净资产(元)", "每股净资产", "每股净资产_调整后(元)", "每股净资产_调整后", "每股净资产_调整前(元)"]

    result["latest"] = {
        "roe": _value(latest, df, roe_cols),
        "revenue_growth": _value(latest, df, rev_cols),
        "profit_growth": _value(latest, df, profit_cols),
        "debt": _value(latest, df, debt_cols),
        "eps": _value(latest, df, eps_cols),
        "bvps": _value(latest, df, bps_cols),
    }
    result["annual"] = {
        "roe": _value(annual, df, roe_cols),
        "revenue_growth": _value(annual, df, rev_cols),
        "profit_growth": _value(annual, df, profit_cols),
        "debt": _value(annual, df, debt_cols),
        "eps": _value(annual, df, eps_cols),
        "bvps": _value(annual, df, bps_cols),
    }

    if not annual_df.empty:
        trend = annual_df.sort_values("_分析日期").groupby(annual_df["_分析日期"].dt.year).tail(1).tail(5).copy()
    else:
        trend = df.tail(5).copy()

    date_col = _find(source, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"])
    out = pd.DataFrame({"报告期": trend[date_col].astype(str).values})
    for label, cols in [
        ("ROE", roe_cols), ("营收增长率", rev_cols), ("净利润增长率", profit_cols),
        ("资产负债率", debt_cols), ("EPS", eps_cols), ("BPS", bps_cols)
    ]:
        col = _find(trend, cols)
        if col:
            out[label] = pd.to_numeric(trend[col], errors="coerce").values
    result["trend"] = out.reset_index(drop=True)
    return result


def calculate_financial_quality(trend, cash_profit_ratio=None):
    if trend is None or trend.empty:
        return {"score": 50, "rating": "数据不足"}

    def vals(name):
        if name not in trend.columns:
            return []
        return [safe_float(x) for x in trend[name] if safe_float(x) is not None]

    roe, rev, profit, debt = vals("ROE"), vals("营收增长率"), vals("净利润增长率"), vals("资产负债率")
    score = 0

    if roe:
        avg = sum(roe) / len(roe)
        score += 20 if avg >= 20 else 17 if avg >= 15 else 13 if avg >= 10 else 8 if avg >= 5 else 3
    if rev:
        avg = sum(rev) / len(rev); pos = sum(x >= 0 for x in rev)
        score += 20 if avg >= 15 and pos >= 4 else 16 if avg >= 8 and pos >= 4 else 11 if avg >= 0 else 4
    if profit:
        avg = sum(profit) / len(profit); pos = sum(x >= 0 for x in profit)
        score += 20 if avg >= 20 and pos >= 4 else 16 if avg >= 10 and pos >= 4 else 11 if avg >= 0 else 4
    if debt:
        avg = sum(debt) / len(debt)
        score += 20 if avg < 40 else 16 if avg < 50 else 12 if avg < 60 else 8 if avg < 70 else 4
    if cash_profit_ratio is not None:
        score += 20 if cash_profit_ratio >= 1 else 15 if cash_profit_ratio >= .8 else 10 if cash_profit_ratio >= .6 else 5 if cash_profit_ratio >= .4 else 2
    else:
        score += 8

    score = int(max(0, min(100, round(score))))
    rating = "优秀" if score >= 85 else "良好" if score >= 70 else "一般" if score >= 55 else "偏弱"
    return {"score": score, "rating": rating}
