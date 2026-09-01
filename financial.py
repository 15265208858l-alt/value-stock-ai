"""ValueStock AI - 财务分析 V19.1
修复：利润表只有季度EPS时，回退财务指标年度EPS，确保历史PE和5年趋势可用。
"""
from __future__ import annotations
import pandas as pd


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


def _prepare(df):
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    try:
        x = df.copy()
        date_col = _find(x, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"])
        if date_col is None:
            return pd.DataFrame()
        x["_分析日期"] = pd.to_datetime(x[date_col], errors="coerce")
        return x.dropna(subset=["_分析日期"]).sort_values("_分析日期").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def _value(row, df, candidates):
    try:
        c = _find(df, candidates)
        return safe_float(row[c]) if c else None
    except Exception:
        return None


def _eps_series(df):
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame(columns=["_分析日期", "_EPS"])
    try:
        date_col = _find(df, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期"])
        eps_col = _find(df, [
            "基本每股收益", "基本每股收益(元)", "基本每股收益（元）", "EPSJB",
            "每股收益", "每股收益(元)", "每股收益（元）",
            "基本每股收益（元/股）", "基本每股收益(元/股)",
            "摊薄每股收益(元)", "摊薄每股收益", "EPSXS"
        ])
        if date_col is None or eps_col is None:
            return pd.DataFrame(columns=["_分析日期", "_EPS"])
        x = df[[date_col, eps_col]].copy()
        x["_分析日期"] = pd.to_datetime(x[date_col], errors="coerce")
        x["_EPS"] = x[eps_col].apply(safe_float)
        return x.dropna(subset=["_分析日期", "_EPS"]).sort_values("_分析日期").drop_duplicates("_分析日期", keep="last").reset_index(drop=True)[["_分析日期", "_EPS"]]
    except Exception:
        return pd.DataFrame(columns=["_分析日期", "_EPS"])


def _annual_eps(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["_分析日期", "_EPS"])
    return df[df["_分析日期"].dt.month == 12].copy()


def process_financial_indicators(indicators, stock_code=None, profit_report=None):
    result = {"latest": {}, "annual": {}, "trend": pd.DataFrame()}
    if indicators is None or getattr(indicators, "empty", True):
        return result
    try:
        df = _prepare(indicators)
        if df.empty:
            return result
        latest = df.iloc[-1]
        annual_df = df[df["_分析日期"].dt.month == 12].copy()
        annual = annual_df.iloc[-1] if not annual_df.empty else latest

        roe_cols = ["ROEJQ", "加权净资产收益率(%)", "加权净资产收益率", "摊薄净资产收益率(%)", "净资产收益率(%)", "净资产收益率", "ROE"]
        rev_cols = ["TOTALOPERATEREVETZ", "主营业务收入增长率(%)", "主营业务收入增长率", "营业收入增长率(%)", "营业收入增长率", "营收增长率"]
        profit_cols = ["PARENTNETPROFITTZ", "净利润增长率(%)", "净利润增长率", "归属净利润同比增长(%)", "净利润同比增长率"]
        debt_cols = ["ZCFZL", "资产负债率(%)", "资产负债率", "负债率"]
        bps_cols = ["BPS", "每股净资产(元)", "每股净资产", "每股净资产_调整后(元)", "每股净资产_调整后", "每股净资产_调整前(元)"]
        eps_cols = ["EPSJB", "基本每股收益(元)", "基本每股收益", "基本每股收益（元）", "基本每股收益(元/股)", "摊薄每股收益(元)", "摊薄每股收益", "每股收益(元)", "每股收益", "EPSXS"]

        profit_eps = _eps_series(profit_report)
        indicator_eps = _eps_series(indicators)
        profit_annual = _annual_eps(profit_eps)
        indicator_annual = _annual_eps(indicator_eps)

        # 关键修复：利润表只要没有年度EPS，就不能继续使用它覆盖历史EPS；
        # 必须切换到财务指标中的年度EPS，否则历史PE会显示“数据不足”。
        if not profit_annual.empty:
            eps_df = profit_eps
            annual_eps_df = profit_annual
        elif not indicator_annual.empty:
            eps_df = indicator_eps
            annual_eps_df = indicator_annual
        elif not profit_eps.empty:
            eps_df = profit_eps
            annual_eps_df = profit_eps
        else:
            eps_df = indicator_eps
            annual_eps_df = indicator_eps

        latest_eps = safe_float(eps_df.iloc[-1]["_EPS"]) if not eps_df.empty else _value(latest, df, eps_cols)
        annual_eps = safe_float(annual_eps_df.iloc[-1]["_EPS"]) if not annual_eps_df.empty else _value(annual, df, eps_cols)

        result["latest"] = {
            "roe": _value(latest, df, roe_cols),
            "revenue_growth": _value(latest, df, rev_cols),
            "profit_growth": _value(latest, df, profit_cols),
            "debt": _value(latest, df, debt_cols),
            "eps": latest_eps,
            "bvps": _value(latest, df, bps_cols),
        }
        result["annual"] = {
            "roe": _value(annual, df, roe_cols),
            "revenue_growth": _value(annual, df, rev_cols),
            "profit_growth": _value(annual, df, profit_cols),
            "debt": _value(annual, df, debt_cols),
            "eps": annual_eps,
            "bvps": _value(annual, df, bps_cols),
        }

        trend_base = annual_df.copy() if not annual_df.empty else df.copy()
        trend_base["_年份"] = trend_base["_分析日期"].dt.year
        trend_base = trend_base.sort_values("_分析日期").groupby("_年份", as_index=False).tail(1).sort_values("_分析日期").tail(5).copy()
        out = pd.DataFrame({"报告期": trend_base["_分析日期"].dt.strftime("%Y-%m-%d").values})
        out["ROE"] = trend_base.apply(lambda r: _value(r, trend_base, roe_cols), axis=1)
        out["营收增长率"] = trend_base.apply(lambda r: _value(r, trend_base, rev_cols), axis=1)
        out["净利润增长率"] = trend_base.apply(lambda r: _value(r, trend_base, profit_cols), axis=1)
        out["资产负债率"] = trend_base.apply(lambda r: _value(r, trend_base, debt_cols), axis=1)
        out["BPS"] = trend_base.apply(lambda r: _value(r, trend_base, bps_cols), axis=1)

        if not annual_eps_df.empty:
            annual_eps_df = annual_eps_df.copy()
            annual_eps_df["_年份"] = annual_eps_df["_分析日期"].dt.year
            eps_map = dict(zip(annual_eps_df["_年份"], annual_eps_df["_EPS"]))
            out["EPS"] = trend_base["_年份"].map(eps_map)

        result["trend"] = out.reset_index(drop=True)
        return result
    except Exception:
        return {"latest": result.get("latest", {}), "annual": result.get("annual", {}), "trend": pd.DataFrame()}


def calculate_financial_quality(trend, cashflow_ratio):
    score = 70
    if trend is not None and not trend.empty:
        try:
            roe = pd.to_numeric(trend.get("ROE"), errors="coerce").dropna() if "ROE" in trend.columns else pd.Series(dtype=float)
            if not roe.empty:
                score += 10 if roe.iloc[-1] >= 15 else 5 if roe.iloc[-1] >= 10 else -5
            debt = pd.to_numeric(trend.get("资产负债率"), errors="coerce").dropna() if "资产负债率" in trend.columns else pd.Series(dtype=float)
            if not debt.empty:
                score += 5 if debt.iloc[-1] < 50 else -5 if debt.iloc[-1] > 70 else 0
        except Exception:
            pass
    if cashflow_ratio is not None:
        score += 10 if cashflow_ratio >= 1 else 5 if cashflow_ratio >= 0.7 else -10
    score = max(0, min(100, int(score)))
    rating = "优秀" if score >= 90 else "良好" if score >= 75 else "一般" if score >= 60 else "较弱"
    return {"score": score, "rating": rating}
