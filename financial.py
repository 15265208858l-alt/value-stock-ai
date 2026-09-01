"""ValueStock AI 财务分析 V21.0
修复重点：5年财务质量趋势不再依赖 pandas apply + 列名猜测，改为逐年、逐字段稳健读取；兼容新浪财务指标的实际中文字段，并保留利润表 EPS/增长率兜底。
"""
from __future__ import annotations
import re
import pandas as pd


def safe_float(value):
    try:
        if value is None:
            return None
        s = str(value).strip().replace(",", "").replace("%", "")
        if s in {"", "--", "None", "none", "NaN", "nan", "null", "NULL", "-"}:
            return None
        return float(s)
    except Exception:
        return None


def _find(df, names):
    if df is None or getattr(df, "empty", True):
        return None
    cols = list(df.columns)
    for name in names:
        if name in cols:
            return name
    # 兼容隐藏空格/全角括号等轻微差异
    norm = {str(c).strip().replace("（", "(").replace("）", ")"): c for c in cols}
    for name in names:
        key = str(name).strip().replace("（", "(").replace("）", ")")
        if key in norm:
            return norm[key]
    return None


def _looks_like_date_column(name):
    s = str(name).strip()
    if re.fullmatch(r"20\d{2}[-/]?\d{2}[-/]?\d{2}.*", s):
        return True
    try:
        dt = pd.to_datetime(s, errors="coerce")
        return bool(pd.notna(dt) and 2000 <= dt.year <= 2100)
    except Exception:
        return False


def _normalize_wide_indicators(df):
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
        return x[date_cols].T.reset_index().rename(columns={"index": "报告期"})
    except Exception:
        return df


def _prepare(df):
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    try:
        x = _normalize_wide_indicators(df.copy())
        date_col = _find(x, ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期", "报告日", "报表日期", "报告日"])
        if date_col is None:
            # 部分新浪结果把日期放在 index
            idx = pd.to_datetime(x.index, errors="coerce")
            if idx.notna().sum() >= max(1, len(x) // 2):
                x = x.copy()
                x["_分析日期"] = idx
                return x.dropna(subset=["_分析日期"]).sort_values("_分析日期").reset_index(drop=True)
            return pd.DataFrame()
        x["_分析日期"] = pd.to_datetime(x[date_col].astype(str), errors="coerce")
        return x.dropna(subset=["_分析日期"]).sort_values("_分析日期").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def _row_value(row, candidates, df=None):
    try:
        c = _find(df, candidates) if df is not None else None
        if c is None:
            return None
        return safe_float(row.get(c)) if hasattr(row, "get") else safe_float(row[c])
    except Exception:
        return None


ROE_COLS = ["加权净资产收益率(%)", "净资产收益率(%)", "加权净资产收益率", "净资产收益率", "ROEJQ", "ROE", "股东权益回报率(%)"]
REV_GROWTH_COLS = ["主营业务收入增长率(%)", "主营业务收入增长率", "营业收入增长率(%)", "营业收入增长率", "营收增长率", "TOTALOPERATEREVETZ", "营业总收入同比"]
PROFIT_GROWTH_COLS = ["净利润增长率(%)", "净利润增长率", "归属净利润同比增长(%)", "净利润同比增长率", "净利润同比", "PARENTNETPROFITTZ"]
DEBT_COLS = ["资产负债率(%)", "资产负债率", "负债率", "ZCFZL"]
BPS_COLS = ["每股净资产_调整后(元)", "每股净资产_调整前(元)", "每股净资产(元)", "每股净资产", "BPS"]
EPS_COLS = ["摊薄每股收益(元)", "加权每股收益(元)", "每股收益_调整后(元)", "基本每股收益(元)", "基本每股收益", "每股收益(元)", "每股收益", "EPSJB", "EPSXS", "EPS"]


def _annual_rows(df):
    """每年选一条最可靠记录：优先12月年报，否则取该年度最后一条。"""
    x = _prepare(df)
    if x.empty:
        return pd.DataFrame()
    x = x.copy()
    x["_年份"] = x["_分析日期"].dt.year
    annual = x[x["_分析日期"].dt.month == 12].copy()
    base = annual if not annual.empty else x
    return base.sort_values("_分析日期").groupby("_年份", as_index=False).tail(1).sort_values("_分析日期").reset_index(drop=True)


def _eps_series(df):
    x = _prepare(df)
    if x.empty:
        return pd.DataFrame(columns=["_分析日期", "_EPS"])
    c = _find(x, EPS_COLS)
    if c is None:
        return pd.DataFrame(columns=["_分析日期", "_EPS"])
    out = x[["_分析日期", c]].copy()
    out["_EPS"] = out[c].apply(safe_float)
    return out.dropna(subset=["_EPS"])[["_分析日期", "_EPS"]].drop_duplicates("_分析日期", keep="last")


def _build_profit_fallback(profit_report):
    x = _annual_rows(profit_report)
    if x.empty:
        return pd.DataFrame()
    eps_c = _find(x, EPS_COLS + ["基本每股收益"])
    rev_c = _find(x, ["营业总收入", "营业收入", "一、营业总收入", "主营业务收入"])
    np_c = _find(x, ["归属于母公司所有者的净利润", "归属于母公司股东的净利润", "净利润", "五、净利润"])
    out = pd.DataFrame({"报告期": x["_分析日期"].dt.strftime("%Y-%m-%d")})
    if eps_c:
        out["EPS"] = x[eps_c].apply(safe_float).values
    if rev_c:
        rev = x[rev_c].apply(safe_float)
        out["营收增长率"] = rev.pct_change().mul(100).values
    if np_c:
        npv = x[np_c].apply(safe_float)
        out["净利润增长率"] = npv.pct_change().mul(100).values
    return out.tail(5).reset_index(drop=True)


def _build_trend(indicators, profit_report=None):
    """独立构建5年趋势；不使用 DataFrame.apply，避免历史字段全部变 None。"""
    ind = _annual_rows(indicators)
    fallback = _build_profit_fallback(profit_report)
    if ind.empty and fallback.empty:
        return pd.DataFrame(columns=["报告期", "ROE", "营收增长率", "净利润增长率", "资产负债率", "BPS", "EPS"])

    years = set()
    if not ind.empty:
        years.update(ind["_年份"].astype(int).tolist())
    if not fallback.empty:
        years.update(pd.to_datetime(fallback["报告期"], errors="coerce").dt.year.dropna().astype(int).tolist())
    years = sorted(years)[-5:]
    ind_map = {int(r["_年份"]): r for _, r in ind.iterrows()} if not ind.empty else {}
    fb = fallback.copy()
    if not fb.empty:
        fb["_年份"] = pd.to_datetime(fb["报告期"], errors="coerce").dt.year
    fb_map = {int(r["_年份"]): r for _, r in fb.dropna(subset=["_年份"]).iterrows()} if not fb.empty else {}

    rows = []
    for year in years:
        r = ind_map.get(year)
        f = fb_map.get(year)
        get = lambda candidates: _row_value(r, candidates, ind) if r is not None else None
        roe = get(ROE_COLS)
        rev = get(REV_GROWTH_COLS)
        profit = get(PROFIT_GROWTH_COLS)
        debt = get(DEBT_COLS)
        bps = get(BPS_COLS)
        eps = get(EPS_COLS)
        if f is not None:
            if eps is None: eps = safe_float(f.get("EPS"))
            if rev is None: rev = safe_float(f.get("营收增长率"))
            if profit is None: profit = safe_float(f.get("净利润增长率"))
        rows.append({
            "报告期": r["_分析日期"].strftime("%Y-%m-%d") if r is not None else str(f.get("报告期")),
            "ROE": roe,
            "营收增长率": rev,
            "净利润增长率": profit,
            "资产负债率": debt,
            "BPS": bps,
            "EPS": eps,
        })
    return pd.DataFrame(rows)


def process_financial_indicators(indicators, stock_code=None, profit_report=None):
    result = {"latest": {}, "annual": {}, "trend": pd.DataFrame()}
    try:
        df = _prepare(indicators)
        annual_rows = _annual_rows(indicators)
        latest = df.iloc[-1] if not df.empty else None
        annual = annual_rows.iloc[-1] if not annual_rows.empty else latest

        eps = _eps_series(indicators)
        profit_eps = _eps_series(profit_report)
        annual_eps_df = _annual_rows(indicators)
        if not annual_eps_df.empty:
            eps_c = _find(annual_eps_df, EPS_COLS)
            annual_eps = safe_float(annual_eps_df.iloc[-1][eps_c]) if eps_c else None
        elif not profit_eps.empty:
            annual_eps = safe_float(profit_eps.iloc[-1]["_EPS"])
        else:
            annual_eps = None
        latest_eps = safe_float(eps.iloc[-1]["_EPS"]) if not eps.empty else annual_eps

        result["latest"] = {
            "roe": _row_value(latest, ROE_COLS, df) if latest is not None else None,
            "revenue_growth": _row_value(latest, REV_GROWTH_COLS, df) if latest is not None else None,
            "profit_growth": _row_value(latest, PROFIT_GROWTH_COLS, df) if latest is not None else None,
            "debt": _row_value(latest, DEBT_COLS, df) if latest is not None else None,
            "eps": latest_eps,
            "bvps": _row_value(latest, BPS_COLS, df) if latest is not None else None,
        }
        result["annual"] = {
            "roe": _row_value(annual, ROE_COLS, annual_rows) if annual is not None else None,
            "revenue_growth": _row_value(annual, REV_GROWTH_COLS, annual_rows) if annual is not None else None,
            "profit_growth": _row_value(annual, PROFIT_GROWTH_COLS, annual_rows) if annual is not None else None,
            "debt": _row_value(annual, DEBT_COLS, annual_rows) if annual is not None else None,
            "eps": annual_eps,
            "bvps": _row_value(annual, BPS_COLS, annual_rows) if annual is not None else None,
        }
        result["trend"] = _build_trend(indicators, profit_report)
        return result
    except Exception:
        return {"latest": result["latest"], "annual": result["annual"], "trend": _build_profit_fallback(profit_report)}


def calculate_financial_quality(trend, cashflow_ratio):
    score = 70
    if trend is not None and not trend.empty:
        roe = pd.to_numeric(trend.get("ROE"), errors="coerce").dropna()
        debt = pd.to_numeric(trend.get("资产负债率"), errors="coerce").dropna()
        if not roe.empty:
            score += 10 if roe.iloc[-1] >= 15 else 5 if roe.iloc[-1] >= 10 else -5
        if not debt.empty:
            score += 5 if debt.iloc[-1] < 50 else -5 if debt.iloc[-1] > 70 else 0
    if cashflow_ratio is not None:
        score += 10 if cashflow_ratio >= 1 else 5 if cashflow_ratio >= 0.7 else -10
    score = max(0, min(100, int(score)))
    rating = "优秀" if score >= 90 else "良好" if score >= 75 else "一般" if score >= 60 else "较弱"
    return {"score": score, "rating": rating}
