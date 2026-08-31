"""ValueStock AI - 财务分析 V18.5
核心原则：原始财务指标优先，东财按报告期作为备用；EPS优先使用利润表按报告期。
重点修复：避免东财刷新接口返回异常/字段变化导致整个财务模块 TypeError；年度EPS错期、季度累计值误当年度值、最近财报EPS口径不一致。
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
    if df is None or getattr(df, "empty", True):
        return None
    for name in names:
        if name in df.columns:
            return name
    return None


def _extract_code(df):
    col = _find(df, ["SECURITY_CODE", "股票代码", "代码", "SECUCODE"])
    if col is None:
        return None
    try:
        for value in df[col].dropna().astype(str):
            digits = "".join(ch for ch in value if ch.isdigit())
            if len(digits) >= 6:
                return digits[-6:]
    except Exception:
        pass
    return None


def _current_stock_code():
    try:
        import adaptive_valuation
        code = str(getattr(adaptive_valuation, "LAST_STOCK_CODE", "") or "").strip()
        if len(code) == 6 and code.isdigit():
            return code
    except Exception:
        pass
    return None


def _symbols(stock_code):
    code = str(stock_code or "").strip()
    if len(code) != 6 or not code.isdigit():
        return []
    if code.startswith(("6", "68")):
        return [f"SH{code}", f"{code}.SH", code]
    if code.startswith(("0", "3")):
        return [f"SZ{code}", f"{code}.SZ", code]
    return [f"BJ{code}", f"{code}.BJ", code]


def _refresh_eastmoney(indicators, stock_code=None):
    """备用刷新东财按报告期财务指标；任何异常均返回原数据。"""
    if ak is None or indicators is None or getattr(indicators, "empty", True):
        return indicators
    code = stock_code or _extract_code(indicators) or _current_stock_code()
    if not code:
        return indicators
    fn = getattr(ak, "stock_financial_analysis_indicator_em", None)
    if fn is None:
        return indicators
    for symbol in _symbols(code):
        try:
            df = fn(symbol=symbol, indicator="按报告期")
            if df is not None and not getattr(df, "empty", True):
                date_col = _find(df, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"])
                if date_col:
                    return df.copy()
        except Exception:
            continue
    return indicators


def _refresh_profit_report(stock_code=None):
    """利润表-按报告期，专门用于EPS；失败时返回None。"""
    if ak is None:
        return None
    code = stock_code or _current_stock_code()
    if not code:
        return None
    fn = getattr(ak, "stock_profit_sheet_by_report_em", None)
    if fn is None:
        return None
    for symbol in _symbols(code):
        try:
            df = fn(symbol=symbol)
            if df is None or getattr(df, "empty", True):
                continue
            date_col = _find(df, ["REPORT_DATE", "报告日期", "报告期", "截止日期", "日期"])
            eps_col = _find(df, [
                "基本每股收益", "基本每股收益(元)", "基本每股收益（元）",
                "每股收益", "每股收益(元)", "每股收益（元）", "EPSJB",
                "基本每股收益（元/股）", "基本每股收益(元/股)"
            ])
            if date_col and eps_col:
                return df.copy()
        except Exception:
            continue
    return None


def _prepare(df):
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    try:
        x = df.copy()
        date_col = _find(x, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"])
        if date_col is None:
            return pd.DataFrame()
        x["_分析日期"] = pd.to_datetime(x[date_col], errors="coerce")
        x = x.dropna(subset=["_分析日期"]).sort_values("_分析日期").reset_index(drop=True)
        return x
    except Exception:
        return pd.DataFrame()


def _value(row, df, candidates):
    try:
        col = _find(df, candidates)
        return safe_float(row[col]) if col else None
    except Exception:
        return None


def _eps_series(df):
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame(columns=["_分析日期", "_EPS"])
    try:
        date_col = _find(df, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"])
        eps_col = _find(df, [
            "基本每股收益", "基本每股收益(元)", "基本每股收益（元）",
            "EPSJB", "每股收益", "每股收益(元)", "每股收益（元）",
            "基本每股收益（元/股）", "基本每股收益(元/股)",
            "摊薄每股收益(元)", "摊薄每股收益"
        ])
        if date_col is None or eps_col is None:
            return pd.DataFrame(columns=["_分析日期", "_EPS"])
        x = df[[date_col, eps_col]].copy()
        x["_分析日期"] = pd.to_datetime(x[date_col], errors="coerce")
        x["_EPS"] = x[eps_col].apply(safe_float)
        x = x.dropna(subset=["_分析日期", "_EPS"]).sort_values("_分析日期")
        return x.drop_duplicates(subset=["_分析日期"], keep="last").reset_index(drop=True)[["_分析日期", "_EPS"]]
    except Exception:
        return pd.DataFrame(columns=["_分析日期", "_EPS"])


def _empty_result():
    return {"latest": {}, "annual": {}, "trend": pd.DataFrame()}


def process_financial_indicators(indicators, stock_code=None):
    """处理财务指标。

    稳定性原则：原始 indicators 可用时绝不强制刷新；东财接口只作备用。
    这样即使AKShare东财接口字段或参数发生变化，也不会让整个页面在第3模块崩溃。
    """
    result = _empty_result()
    if indicators is None or getattr(indicators, "empty", True):
        return result

    try:
        code = stock_code or _extract_code(indicators) or _current_stock_code()

        # 关键修复：先使用 load_stock_data 已成功获取的原始指标。
        # 只有原始指标无法解析日期时，才尝试东财备用接口。
        df = _prepare(indicators)
        if df.empty:
            source = _refresh_eastmoney(indicators, stock_code=code)
            df = _prepare(source)
        else:
            source = indicators

        if df.empty:
            return result

        latest = df.iloc[-1]
        annual_df = df[df["_分析日期"].dt.month == 12].copy()
        annual = annual_df.iloc[-1] if not annual_df.empty else latest

        roe_cols = ["ROEJQ", "加权净资产收益率(%)", "加权净资产收益率", "摊薄净资产收益率(%)", "净资产收益率(%)", "净资产收益率"]
        rev_cols = ["TOTALOPERATEREVETZ", "主营业务收入增长率(%)", "主营业务收入增长率", "营业收入增长率(%)", "营业收入增长率"]
        profit_cols = ["PARENTNETPROFITTZ", "净利润增长率(%)", "净利润增长率", "归属净利润同比增长(%)"]
        debt_cols = ["ZCFZL", "资产负债率(%)", "资产负债率"]
        eps_cols = ["EPSJB", "基本每股收益(元)", "基本每股收益", "基本每股收益（元/股）", "基本每股收益(元/股)", "摊薄每股收益(元)", "摊薄每股收益", "每股收益(元)", "每股收益", "EPSXS"]
        bps_cols = ["BPS", "每股净资产(元)", "每股净资产", "每股净资产_调整后(元)", "每股净资产_调整后", "每股净资产_调整前(元)"]

        # EPS单独使用利润表按报告期；失败则回退到已经获取的 indicators。
        eps_report = _refresh_profit_report(code)
        eps_df = _eps_series(eps_report)
        if eps_df.empty:
            eps_df = _eps_series(indicators)
        if eps_df.empty and source is not indicators:
            eps_df = _eps_series(source)

        latest_eps = None
        annual_eps = None
        if not eps_df.empty:
            latest_eps = safe_float(eps_df.iloc[-1]["_EPS"])
            annual_eps_df = eps_df[eps_df["_分析日期"].dt.month == 12]
            if not annual_eps_df.empty:
                annual_eps = safe_float(annual_eps_df.iloc[-1]["_EPS"])

        result["latest"] = {
            "roe": _value(latest, df, roe_cols),
            "revenue_growth": _value(latest, df, rev_cols),
            "profit_growth": _value(latest, df, profit_cols),
            "debt": _value(latest, df, debt_cols),
            "eps": latest_eps if latest_eps is not None else _value(latest, df, eps_cols),
            "bvps": _value(latest, df, bps_cols),
        }
        result["annual"] = {
            "roe": _value(annual, df, roe_cols),
            "revenue_growth": _value(annual, df, rev_cols),
            "profit_growth": _value(annual, df, profit_cols),
            "debt": _value(annual, df, debt_cols),
            "eps": annual_eps if annual_eps is not None else _value(annual, df, eps_cols),
            "bvps": _value(annual, df, bps_cols),
        }

        if not annual_df.empty:
            trend = annual_df.sort_values("_分析日期").groupby(annual_df["_分析日期"].dt.year).tail(1).tail(5).copy()
        else:
            trend = df.tail(5).copy()

        date_col = _find(source, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"])
        if date_col is None:
            date_col = _find(df, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"])
        if date_col is None:
            return result

        out = pd.DataFrame({"报告期": trend[date_col].astype(str).values})
        for label, cols in [
            ("ROE", roe_cols), ("营收增长率", rev_cols), ("净利润增长率", profit_cols),
            ("资产负债率", debt_cols), ("BPS", bps_cols)
        ]:
            col = _find(trend, cols)
            if col:
                out[label] = pd.to_numeric(trend[col], errors="coerce").values

        if not eps_df.empty:
            annual_eps_trend = eps_df[eps_df["_分析日期"].dt.month == 12].tail(5).copy()
            eps_map = {d.strftime("%Y-%m-%d"): e for d, e in zip(annual_eps_trend["_分析日期"], annual_eps_trend["_EPS"])}
            out_dates = pd.to_datetime(out["报告期"], errors="coerce")
            out["EPS"] = [eps_map.get(d.strftime("%Y-%m-%d")) if not pd.isna(d) else None for d in out_dates]
        else:
            col = _find(trend, eps_cols)
            if col:
                out["EPS"] = pd.to_numeric(trend[col], errors="coerce").values

        result["trend"] = out.reset_index(drop=True)
        return result
    except Exception:
        # 财务模块永不阻断整页；上层仍可显示“数据不足/待恢复”。
        return result


def calculate_financial_quality(trend, cash_profit_ratio=None):
    if trend is None or getattr(trend, "empty", True):
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
