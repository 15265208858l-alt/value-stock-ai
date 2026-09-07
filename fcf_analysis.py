"""ValueStock AI 自由现金流分析模块 V1.0

目标：把利润质量进一步转换为“企业真正创造了多少可支配现金”。
原则：
- 只消费主流程已经取得的数据，不自行访问网络。
- 缺失数据明确返回“数据不足”，不猜测。
- 同时观察经营现金流、资本开支和折旧摊销。
- 不把一次性资本开支直接等同于坏事，而是区分轻度关注、压力和危险。
"""
from __future__ import annotations

import pandas as pd


def _num(v):
    try:
        if v is None:
            return None
        s = str(v).strip().replace(",", "").replace("%", "")
        if s in {"", "--", "None", "none", "nan", "NaN", "null", "NULL", "-"}:
            return None
        return float(s)
    except Exception:
        return None


def _find_col(df, candidates):
    if df is None or getattr(df, "empty", True):
        return None
    cols = list(df.columns)
    for name in candidates:
        if name in cols:
            return name
    norm = {
        str(c).strip().replace(" ", "").replace("（", "(").replace("）", ")"): c
        for c in cols
    }
    for name in candidates:
        key = str(name).strip().replace(" ", "").replace("（", "(").replace("）", ")")
        if key in norm:
            return norm[key]
    return None


def _date_series(df):
    if df is None or getattr(df, "empty", True):
        return None
    for c in ["REPORT_DATE", "日期", "报告期", "报告日期", "截止日期", "报表日期"]:
        if c in df.columns:
            return pd.to_datetime(df[c], errors="coerce")
    idx = pd.to_datetime(df.index, errors="coerce")
    if idx.notna().sum() >= max(1, len(df) // 2):
        return idx
    return None


def _annual(df):
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame()
    x = df.copy()
    dates = _date_series(x)
    if dates is None:
        return pd.DataFrame()
    x["_date"] = dates
    x = x.dropna(subset=["_date"]).copy()
    if x.empty:
        return x
    x["_year"] = x["_date"].dt.year
    annual = x[x["_date"].dt.month == 12]
    base = annual if not annual.empty else x
    return (
        base.sort_values("_date")
        .groupby("_year", as_index=False)
        .tail(1)
        .sort_values("_date")
        .reset_index(drop=True)
    )


def _value_series(df, candidates):
    x = _annual(df)
    if x.empty:
        return None
    col = _find_col(x, candidates)
    if col is None:
        return None
    out = pd.DataFrame({"date": x["_date"], "value": x[col].apply(_num)})
    return out.dropna(subset=["value"]).reset_index(drop=True)


def build_fcf_analysis(operating_cashflow, net_profit, capex=None, depreciation=None):
    """基于最新值计算自由现金流质量。capex 按正数表示支出额。"""
    ocf = _num(operating_cashflow)
    profit = _num(net_profit)
    cap = _num(capex)
    dep = abs(_num(depreciation)) if depreciation is not None else None

    result = {
        "available": False,
        "operating_cashflow": ocf,
        "net_profit": profit,
        "capex": cap,
        "depreciation": dep,
        "fcf": None,
        "ocf_to_profit": None,
        "capex_to_ocf": None,
        "capex_to_depreciation": None,
        "score": None,
        "level": "数据不足",
        "hard_veto": False,
        "items": [],
    }

    if ocf is None:
        return result

    result["available"] = True
    if profit is not None and profit != 0:
        result["ocf_to_profit"] = ocf / profit

    if cap is not None:
        cap = max(cap, 0.0)
        result["capex"] = cap
        result["fcf"] = ocf - cap
        if abs(ocf) > 0:
            result["capex_to_ocf"] = cap / abs(ocf)
        if dep is not None and dep > 0:
            result["capex_to_depreciation"] = cap / dep

    # 0最好，风险最高为3；仅在明确有数据时评分。
    score = 0
    if ocf < 0:
        score += 2
        result["items"].append("经营现金流为负，自由现金创造能力需要重点排查。")
        if profit is not None and profit > 0:
            result["hard_veto"] = True
            result["items"].append("净利润为正但经营现金流为负，存在利润现金含量异常。")

    if cap is not None:
        fcf = result["fcf"]
        if fcf is not None and fcf < 0:
            score += 1
            result["items"].append("扣除资本开支后自由现金流为负，需要确认扩张投入是否能带来合理回报。")
        ratio = result["capex_to_ocf"]
        if ratio is not None and ratio >= 1.0 and ocf >= 0:
            score += 1
            result["items"].append("资本开支达到或超过经营现金流，自由现金流承压。")

    score = min(score, 3)
    result["score"] = score
    if result["hard_veto"]:
        result["level"] = "高风险 / 否决"
    elif score >= 3:
        result["level"] = "高风险"
    elif score == 2:
        result["level"] = "需要重点关注"
    elif score == 1:
        result["level"] = "需要关注"
    else:
        result["level"] = "良好"
    return result


def analyze_fcf_from_frames(profit_report=None, cashflow=None):
    """从已加载的利润表、现金流量表提取最新年度自由现金流指标。"""
    profit = _value_series(
        profit_report,
        ["归属于母公司所有者的净利润", "归属于母公司股东的净利润", "净利润", "PARENTNETPROFIT", "五、净利润"],
    )
    ocf = _value_series(
        cashflow,
        ["经营活动产生的现金流量净额", "经营活动现金流量净额", "NETCASH_OPERATE"],
    )
    capex = _value_series(
        cashflow,
        [
            "购建固定资产、无形资产和其他长期资产所支付的现金",
            "购建固定资产、无形资产和其他长期资产支付的现金",
            "CAPEX",
            "资本开支",
        ],
    )
    depreciation = _value_series(
        cashflow,
        ["固定资产折旧", "折旧", "折旧摊销", "固定资产折旧及摊销"],
    )

    def last(s):
        return None if s is None or s.empty else float(s.iloc[-1]["value"])

    return build_fcf_analysis(last(ocf), last(profit), last(capex), last(depreciation))


def fcf_quality_label(result):
    if not result or not result.get("available"):
        return "数据不足"
    if result.get("hard_veto"):
        return "⛔ 自由现金流风险否决"
    return result.get("level", "数据不足")
