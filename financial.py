"""ValueStock AI - 财务分析 V20.1
修复：兼容 AKShare 新浪/东财财务指标的横向、纵向两种返回结构，并从利润表兜底构建5年历史趋势。
"""
from __future__ import annotations
import re
import pandas as pd


def safe_float(value):
    try:
        if value is None:
            return None
        text = str(value).strip().replace(",", "").replace("%", "")
        if text in {"", "--", "None", "none", "NaN", "nan", "null", "NULL"}:
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


def _looks_like_date_column(name):
    s = str(name).strip()
    if re.fullmatch(r"20\d{2}[-/]?\d{2}[-/]?\d{2}", s):
        return True
    if re.fullmatch(r"20\d{2}[-/]?\d{2}[-/]?\d{2}.*", s):
        return True
    try:
        dt = pd.to_datetime(s, errors="coerce")
        return bool(pd.notna(dt) and 2000 <= dt.year <= 2100)
    except Exception:
        return False


def _normalize_wide_indicators(df):
    """兼容新浪老接口常见结构：第一列为指标名称，后续列为各年度日期。"""
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    try:
        date_cols = [c for c in df.columns if _looks_like_date_column(c)]
        if len(date_cols) < 2:
            return df
        label_col = next((c for c in ["选取指标", "指标", "项目", "名称"] if c in df.columns), df.columns[0])
        x = df[[label_col] + date_cols].copy()
        x[label_col] = x[label_col].astype(str).str.strip()
        x = x.drop_duplicates(subset=[label_col], keep="last").set_index(label_col)
        t = x[date_cols].T.reset_index().rename(columns={"index": "报告期"})
        t["报告期"] = t["报告期"].astype(str)
        return t
    except Exception:
        return df


def _prepare(df):
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    try:
        x = _normalize_wide_indicators(df.copy())
        date_col = _find(x, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期", "报告日", "报表日期"])
        if date_col is None:
            return pd.DataFrame()
        x["_分析日期"] = pd.to_datetime(x[date_col].astype(str), errors="coerce")
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
        x = _prepare(df)
        if x.empty:
            return pd.DataFrame(columns=["_分析日期", "_EPS"])
        eps_col = _find(x, [
            "EPS", "基本每股收益", "基本每股收益(元)", "基本每股收益（元）",
            "每股收益", "每股收益(元)", "每股收益（元）", "EPSJB",
            "基本每股收益（元/股）", "基本每股收益(元/股)",
            "摊薄每股收益(元)", "摊薄每股收益", "摊薄每股收益(元/股)", "EPSXS"
        ])
        if eps_col is None:
            return pd.DataFrame(columns=["_分析日期", "_EPS"])
        out = x[["_分析日期", eps_col]].copy()
        out["_EPS"] = out[eps_col].apply(safe_float)
        return out.dropna(subset=["_分析日期", "_EPS"]).sort_values("_分析日期").drop_duplicates("_分析日期", keep="last")[["_分析日期", "_EPS"]].reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=["_分析日期", "_EPS"])


def _annual_eps(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=["_分析日期", "_EPS"])
    return df[df["_分析日期"].dt.month == 12].copy()


def _build_profit_trend(profit_report):
    """从新浪利润表直接构建年度EPS/营收/净利润增长趋势，作为财务指标趋势的强兜底。"""
    if profit_report is None or getattr(profit_report, "empty", True):
        return pd.DataFrame()
    try:
        x = _prepare(profit_report)
        if x.empty:
            return pd.DataFrame()
        eps_col = _find(x, ["基本每股收益", "基本每股收益(元)", "基本每股收益（元）", "每股收益", "每股收益(元)", "摊薄每股收益"])
        revenue_col = _find(x, ["营业总收入", "营业收入", "一、营业总收入", "主营业务收入"])
        profit_col = _find(x, ["归属于母公司所有者的净利润", "归属于母公司股东的净利润", "净利润", "五、净利润"])
        annual = x[x["_分析日期"].dt.month == 12].copy()
        if annual.empty:
            annual = x.copy()
        annual["_年份"] = annual["_分析日期"].dt.year
        annual = annual.sort_values("_分析日期").groupby("_年份", as_index=False).tail(1).sort_values("_分析日期").tail(5).copy()
        out = pd.DataFrame({"报告期": annual["_分析日期"].dt.strftime("%Y-%m-%d").values})
        if eps_col:
            out["EPS"] = annual[eps_col].apply(safe_float).values
        if revenue_col:
            rev = annual[revenue_col].apply(safe_float)
            out["营收增长率"] = rev.pct_change() * 100
        if profit_col:
            npv = annual[profit_col].apply(safe_float)
            out["净利润增长率"] = npv.pct_change() * 100
        return out.reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def process_financial_indicators(indicators, stock_code=None, profit_report=None):
    result = {"latest": {}, "annual": {}, "trend": pd.DataFrame()}
    if indicators is None or getattr(indicators, "empty", True):
        result["trend"] = _build_profit_trend(profit_report)
        return result
    try:
        df = _prepare(indicators)
        if df.empty:
            result["trend"] = _build_profit_trend(profit_report)
            return result

        latest = df.iloc[-1]
        annual_df = df[df["_分析日期"].dt.month == 12].copy()
        annual = annual_df.iloc[-1] if not annual_df.empty else latest

        roe_cols = ["ROEJQ", "加权净资产收益率(%)", "加权净资产收益率", "摊薄净资产收益率(%)", "净资产收益率(%)", "净资产收益率", "ROE", "股东权益回报率(%)"]
        rev_cols = ["TOTALOPERATEREVETZ", "主营业务收入增长率(%)", "主营业务收入增长率", "营业收入增长率(%)", "营业收入增长率", "营收增长率", "营业总收入同比"]
        profit_cols = ["PARENTNETPROFITTZ", "净利润增长率(%)", "净利润增长率", "归属净利润同比增长(%)", "净利润同比增长率", "净利润同比"]
        debt_cols = ["ZCFZL", "资产负债率(%)", "资产负债率", "负债率"]
        bps_cols = ["BPS", "每股净资产(元)", "每股净资产", "每股净资产_调整后(元)", "每股净资产_调整后", "每股净资产_调整前(元)", "每股净资产_调整前"]
        eps_cols = ["EPSJB", "基本每股收益(元)", "基本每股收益", "基本每股收益（元）", "基本每股收益(元/股)", "摊薄每股收益(元)", "摊薄每股收益", "每股收益(元)", "每股收益", "EPSXS"]

        profit_eps = _eps_series(profit_report)
        indicator_eps = _eps_series(indicators)
        profit_annual = _annual_eps(profit_eps)
        indicator_annual = _annual_eps(indicator_eps)

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

        fallback = _build_profit_trend(profit_report)
        if not fallback.empty:
            years = pd.to_datetime(fallback["报告期"], errors="coerce").dt.year
            for col in ["EPS", "营收增长率", "净利润增长率"]:
                if col in fallback.columns:
                    fmap = dict(zip(years, fallback[col]))
                    if col not in out.columns:
                        out[col] = trend_base["_年份"].map(fmap)
                    else:
                        out[col] = out[col].where(pd.notna(out[col]), trend_base["_年份"].map(fmap))

        result["trend"] = out.reset_index(drop=True)
        return result
    except Exception:
        fallback = _build_profit_trend(profit_report)
        return {"latest": result.get("latest", {}), "annual": result.get("annual", {}), "trend": fallback}


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
