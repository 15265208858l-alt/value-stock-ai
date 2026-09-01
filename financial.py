"""ValueStock AI - 财务分析 V19.0

设计目标：
1. 财务分析只消费 load_stock_data_fast 已经获取的数据，绝不重复请求远程接口。
2. 单个字段解析失败不能让整个财务模块变空。
3. EPS优先使用已经获取的利润表，其次使用财务指标。
4. 年度数据按12月报告期提取；5年趋势按年份对齐，避免长度不一致导致整段异常。
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
        x = x.dropna(subset=["_分析日期"]).sort_values("_分析日期").reset_index(drop=True)
        return x
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
        x = x.dropna(subset=["_分析日期", "_EPS"])
        return x.sort_values("_分析日期").drop_duplicates("_分析日期", keep="last").reset_index(drop=True)[["_分析日期", "_EPS"]]
    except Exception:
        return pd.DataFrame(columns=["_分析日期", "_EPS"])


def _annual_value(df, candidates):
    if df is None or df.empty:
        return None
    x = _prepare(df)
    if x.empty:
        return None
    annual = x[x["_分析日期"].dt.month == 12]
    row = annual.iloc[-1] if not annual.empty else x.iloc[-1]
    return _value(row, x, candidates)


def process_financial_indicators(indicators, stock_code=None, profit_report=None):
    """处理已加载的财务指标；不会进行任何网络请求。"""
    result = {"latest": {}, "annual": {}, "trend": pd.DataFrame()}
    if indicators is None or getattr(indicators, "empty", True):
        return result

    try:
        df = _prepare(indicators)
        if df.empty:
            # 不因为日期列名称变化而让整个模块报空；尝试常见中文/英文日期列。
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

        eps_df = _eps_series(profit_report)
        if eps_df.empty:
            eps_df = _eps_series(indicators)

        latest_eps = safe_float(eps_df.iloc[-1]["_EPS"]) if not eps_df.empty else _value(latest, df, eps_cols)
        annual_eps = None
        if not eps_df.empty:
            ae = eps_df[eps_df["_分析日期"].dt.month == 12]
            if not ae.empty:
                annual_eps = safe_float(ae.iloc[-1]["_EPS"])
        if annual_eps is None:
            annual_eps = _value(annual, df, eps_cols)

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

        # 5年趋势：先按年份选最后一条，再逐年写入，绝不做不同长度数组的直接赋值。
        trend_base = annual_df.copy() if not annual_df.empty else df.copy()
        trend_base["_年份"] = trend_base["_分析日期"].dt.year
        trend_base = trend_base.sort_values("_分析日期").groupby("_年份", as_index=False).tail(1).sort_values("_分析日期").tail(5).copy()
        out = pd.DataFrame({"报告期": trend_base["_分析日期"].dt.strftime("%Y-%m-%d").values})
        out["ROE"] = trend_base.apply(lambda r: _value(r, trend_base, roe_cols), axis=1)
        out["营收增长率"] = trend_base.apply(lambda r: _value(r, trend_base, rev_cols), axis=1)
        out["净利润增长率"] = trend_base.apply(lambda r: _value(r, trend_base, profit_cols), axis=1)
        out["资产负债率"] = trend_base.apply(lambda r: _value(r, trend_base, debt_cols), axis=1)
        out["BPS"] = trend_base.apply(lambda r: _value(r, trend_base, bps_cols), axis=1)

        # EPS按年份映射，不按位置硬塞，避免报告期样本数量不同导致 ValueError。
        if not eps_df.empty:
            annual_eps_df = eps_df[eps_df["_分析日期"].dt.month == 12].copy()
            annual_eps_df["_年份"] = annual_eps_df["_分析日期"].dt.year
            eps_map = dict(zip(annual_eps_df["_年份"], annual_eps_df["_EPS"]))
            out["EPS"] = trend_base["_年份"].map(eps_map)

        result["trend"] = out.reset_index(drop=True)
        return result
    except Exception:
        # 兜底：即使趋势构建失败，也保留最新/年度指标。
        return {"latest": result.get("latest", {}), "annual": result.get("annual", {}), "trend": pd.DataFrame()}


def calculate_financial_quality(trend, cashflow_ratio):
    """财务质量评分，保持既有评分口径。"""
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
