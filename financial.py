"""ValueStock AI 财务分析 V22

核心原则：
- 优先解析东方财富按报告期结构化字段；新浪老接口仅作备用。
- 不访问网络；只消费主流程已经加载的 DataFrame。
- 5年历史按年份生成，任何单一字段缺失都不影响其它字段。
"""
from __future__ import annotations
import pandas as pd


def safe_float(v):
    try:
        if v is None:
            return None
        s = str(v).strip().replace(",", "").replace("%", "")
        if s in {"", "--", "None", "none", "NaN", "nan", "null", "NULL", "-"}:
            return None
        return float(s)
    except Exception:
        return None


def _find(df, names):
    if df is None or getattr(df, "empty", True):
        return None
    cols = list(df.columns)
    for n in names:
        if n in cols:
            return n
    norm = {str(c).strip().replace("（", "(").replace("）", ")").replace(" ", ""): c for c in cols}
    for n in names:
        k = str(n).strip().replace("（", "(").replace("）", ")").replace(" ", "")
        if k in norm:
            return norm[k]
    return None

DATE_COLS = ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期", "报告日", "报表日期"]
ROE_COLS = ["ROEJQ", "ROE_YEARLY", "ROE_TTM", "加权净资产收益率(%)", "净资产收益率(%)", "加权净资产收益率", "净资产收益率", "净资产收益率(加权)"]
REV_GROWTH_COLS = ["TOTALOPERATEREVETZ", "TOTAL_OPERATE_REVENUE_TZ", "营业总收入同比增长", "主营业务收入增长率(%)", "主营业务收入增长率", "营业收入增长率(%)", "营业收入增长率", "营收增长率", "总营业收入同比增长"]
PROFIT_GROWTH_COLS = ["PARENTNETPROFITTZ", "PARENT_NET_PROFIT_TZ", "归母净利润同比增长", "净利润增长率(%)", "净利润增长率", "归属净利润同比增长(%)", "净利润同比增长率", "净利润同比"]
DEBT_COLS = ["ZCFZL", "资产负债率(%)", "资产负债率", "负债率"]
BPS_COLS = ["BPS", "每股净资产", "每股净资产(元)", "每股净资产_调整后(元)", "每股净资产_调整后", "每股净资产_调整前(元)", "每股净资产_调整前"]
EPS_COLS = ["EPSJB", "BASIC_EPS", "基本每股收益(元)", "基本每股收益（元）", "基本每股收益", "每股收益(基本)", "每股收益(元)", "每股收益", "EPSXS", "摊薄每股收益(元)", "摊薄每股收益"]


def _prepare(df):
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    x = df.copy()
    dc = _find(x, DATE_COLS)
    if dc is None:
        # 有些老版接口把日期放在 index。
        idx = pd.to_datetime(x.index, errors="coerce")
        if idx.notna().sum() >= max(1, len(x) // 2):
            x["_分析日期"] = idx
        else:
            return pd.DataFrame()
    else:
        x["_分析日期"] = pd.to_datetime(x[dc], errors="coerce")
    x = x.dropna(subset=["_分析日期"]).sort_values("_分析日期").reset_index(drop=True)
    return x


def _get(row, df, candidates):
    if row is None:
        return None
    c = _find(df, candidates)
    if c is None:
        return None
    try:
        return safe_float(row.get(c))
    except Exception:
        return safe_float(row[c])


def _annual_rows(df):
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
    ec = _find(x, EPS_COLS)
    if ec is None:
        return pd.DataFrame(columns=["_分析日期", "_EPS"])
    y = x[["_分析日期", ec]].copy()
    y["_EPS"] = y[ec].apply(safe_float)
    return y.dropna(subset=["_EPS"])[["_分析日期", "_EPS"]].drop_duplicates("_分析日期", keep="last").reset_index(drop=True)


def _build_profit_fallback(profit_report):
    x = _annual_rows(profit_report)
    if x.empty:
        return pd.DataFrame()
    eps_c = _find(x, EPS_COLS)
    rev_c = _find(x, ["营业总收入", "TOTALOPERATEREVE", "TOTAL_OPERATE_INCOME", "营业收入", "一、营业总收入", "主营业务收入"])
    np_c = _find(x, ["归属于母公司所有者的净利润", "PARENTNETPROFIT", "归属于母公司股东的净利润", "净利润", "五、净利润", "归母净利润"])
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
    ind = _annual_rows(indicators)
    fallback = _build_profit_fallback(profit_report)
    years = set()
    if not ind.empty:
        years.update(ind["_年份"].astype(int).tolist())
    if not fallback.empty:
        years.update(pd.to_datetime(fallback["报告期"], errors="coerce").dt.year.dropna().astype(int).tolist())
    years = sorted(years)[-5:]
    if not years:
        return pd.DataFrame(columns=["报告期", "ROE", "营收增长率", "净利润增长率", "资产负债率", "BPS", "EPS"])
    ind_map = {int(r["_年份"]): r for _, r in ind.iterrows()} if not ind.empty else {}
    fb = fallback.copy()
    if not fb.empty:
        fb["_年份"] = pd.to_datetime(fb["报告期"], errors="coerce").dt.year
    fb_map = {int(r["_年份"]): r for _, r in fb.dropna(subset=["_年份"]).iterrows()} if not fb.empty else {}

    rows = []
    for year in years:
        r = ind_map.get(year)
        f = fb_map.get(year)
        rows.append({
            "报告期": r["_分析日期"].strftime("%Y-%m-%d") if r is not None else str(f["报告期"]),
            "ROE": _get(r, ind, ROE_COLS),
            "营收增长率": _get(r, ind, REV_GROWTH_COLS),
            "净利润增长率": _get(r, ind, PROFIT_GROWTH_COLS),
            "资产负债率": _get(r, ind, DEBT_COLS),
            "BPS": _get(r, ind, BPS_COLS),
            "EPS": _get(r, ind, EPS_COLS),
        })
        row = rows[-1]
        if f is not None:
            for c in ("EPS", "营收增长率", "净利润增长率"):
                if row[c] is None and c in f.index:
                    row[c] = safe_float(f[c])
    return pd.DataFrame(rows)


def process_financial_indicators(indicators, stock_code=None, profit_report=None):
    result = {"latest": {}, "annual": {}, "trend": pd.DataFrame()}
    df = _prepare(indicators)
    annual_df = _annual_rows(indicators)
    latest = df.iloc[-1] if not df.empty else None
    annual = annual_df.iloc[-1] if not annual_df.empty else latest

    # 对EM结构化指标，直接读取统一英文列；对新浪接口读取中文别名。
    profit_eps = _eps_series(profit_report)
    ind_eps = _eps_series(indicators)
    annual_eps = None
    if not annual_df.empty:
        annual_eps = _get(annual, ind, EPS_COLS) if False else _get(annual, annual_df, EPS_COLS)
    if annual_eps is None and not profit_eps.empty:
        ae = profit_eps[profit_eps["_分析日期"].dt.month == 12]
        if not ae.empty:
            annual_eps = safe_float(ae.iloc[-1]["_EPS"])
    latest_eps = safe_float(ind_eps.iloc[-1]["_EPS"]) if not ind_eps.empty else (safe_float(profit_eps.iloc[-1]["_EPS"]) if not profit_eps.empty else annual_eps)

    if latest is not None:
        result["latest"] = {
            "roe": _get(latest, df, ROE_COLS),
            "revenue_growth": _get(latest, df, REV_GROWTH_COLS),
            "profit_growth": _get(latest, df, PROFIT_GROWTH_COLS),
            "debt": _get(latest, df, DEBT_COLS),
            "eps": latest_eps,
            "bvps": _get(latest, df, BPS_COLS),
        }
    if annual is not None:
        result["annual"] = {
            "roe": _get(annual, annual_df, ROE_COLS),
            "revenue_growth": _get(annual, annual_df, REV_GROWTH_COLS),
            "profit_growth": _get(annual, annual_df, PROFIT_GROWTH_COLS),
            "debt": _get(annual, annual_df, DEBT_COLS),
            "eps": annual_eps,
            "bvps": _get(annual, annual_df, BPS_COLS),
        }
    result["trend"] = _build_trend(indicators, profit_report)
    return result


def calculate_financial_quality(trend, cashflow_ratio):
    score = 70
    if trend is not None and not trend.empty:
        roe = pd.to_numeric(trend.get("ROE"), errors="coerce").dropna() if "ROE" in trend.columns else pd.Series(dtype=float)
        debt = pd.to_numeric(trend.get("资产负债率"), errors="coerce").dropna() if "资产负债率" in trend.columns else pd.Series(dtype=float)
        if not roe.empty: score += 10 if roe.iloc[-1] >= 15 else 5 if roe.iloc[-1] >= 10 else -5
        if not debt.empty: score += 5 if debt.iloc[-1] < 50 else -5 if debt.iloc[-1] > 70 else 0
    if cashflow_ratio is not None: score += 10 if cashflow_ratio >= 1 else 5 if cashflow_ratio >= .7 else -10
    score = max(0, min(100, int(score)))
    rating = "优秀" if score >= 90 else "良好" if score >= 75 else "一般" if score >= 60 else "较弱"
    return {"score": score, "rating": rating}
