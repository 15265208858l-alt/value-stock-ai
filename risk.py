"""
ValueStock AI 财务深度风险分析 V2

核心原则：
- 保留原有 API，避免主程序回归。
- 在现金流、应收、存货、ROE、负债之外，增加趋势异常与硬风险否决。
- 对缺失字段明确标记“数据不足”，不把未知当成安全。
"""
from __future__ import annotations


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


def safe_ratio(a, b):
    a = safe_float(a)
    b = safe_float(b)
    if a is None or b is None or b == 0:
        return None
    return a / b


def _series(df, candidates):
    if df is None or getattr(df, "empty", True):
        return None
    col = None
    cols = list(df.columns)
    for name in candidates:
        if name in cols:
            col = name
            break
    if col is None:
        norm = {str(c).replace(" ", "").replace("（", "(").replace("）", ")"): c for c in cols}
        for name in candidates:
            key = str(name).replace(" ", "").replace("（", "(").replace("）", ")")
            if key in norm:
                col = norm[key]
                break
    if col is None:
        return None
    try:
        return df[col].apply(safe_float).dropna()
    except Exception:
        return None


def _latest(df, candidates):
    s = _series(df, candidates)
    if s is None or s.empty:
        return None
    return safe_float(s.iloc[-1])


def _growth(series):
    if series is None or len(series) < 2:
        return None
    first = float(series.iloc[0])
    last = float(series.iloc[-1])
    if first == 0:
        return None
    return last / first - 1


def analyze_cashflow_quality(operating_cashflow, net_profit):
    ratio = safe_ratio(operating_cashflow, net_profit)
    if ratio is None:
        return {"ratio": None, "score": 0, "level": "数据不足", "message": "缺少经营现金流或净利润数据。"}
    if ratio >= 1:
        return {"ratio": ratio, "score": 0, "level": "优秀", "message": "经营现金流能够覆盖净利润，利润现金含量较好。"}
    if ratio >= 0.7:
        return {"ratio": ratio, "score": 1, "level": "良好", "message": "经营现金流与净利润基本匹配，需要继续观察。"}
    if ratio >= 0:
        return {"ratio": ratio, "score": 2, "level": "需要关注", "message": "经营现金流明显低于净利润，需要进一步排查利润质量。"}
    return {"ratio": ratio, "score": 3, "level": "高风险", "message": "经营现金流为负，而净利润可能为正，需要重点排查。"}


def analyze_receivable(receivable, revenue):
    ratio = safe_ratio(receivable, revenue)
    if ratio is None:
        return {"ratio": None, "score": 0, "level": "数据不足", "message": "缺少应收账款或营业收入数据。"}
    if ratio > 0.40:
        return {"ratio": ratio, "score": 3, "level": "高风险信号", "message": "应收账款占营业收入比例较高，需要重点检查回款能力。"}
    if ratio > 0.25:
        return {"ratio": ratio, "score": 1, "level": "需要关注", "message": "应收账款占比偏高，需要结合历史趋势观察。"}
    return {"ratio": ratio, "score": 0, "level": "正常", "message": "应收账款/营业收入比例暂未显示明显异常。"}


def analyze_inventory(inventory, revenue):
    ratio = safe_ratio(inventory, revenue)
    if ratio is None:
        return {"ratio": None, "score": 0, "level": "数据不足", "message": "缺少存货或营业收入数据。"}
    if ratio > 0.50:
        return {"ratio": ratio, "score": 3, "level": "高风险信号", "message": "存货相对营业规模较高，需要检查库存周转和减值风险。"}
    if ratio > 0.30:
        return {"ratio": ratio, "score": 1, "level": "需要关注", "message": "存货占比需要继续观察。"}
    return {"ratio": ratio, "score": 0, "level": "正常", "message": "存货/营业收入比例暂未显示明显异常。"}


def analyze_roe(roe):
    if roe is None:
        return {"score": 0, "level": "数据不足", "message": "缺少ROE数据。"}
    if roe >= 15:
        return {"score": 0, "level": "良好", "message": f"ROE为{roe:.2f}%，资本回报能力较好。"}
    if roe >= 10:
        return {"score": 1, "level": "一般", "message": f"ROE为{roe:.2f}%，资本回报能力一般。"}
    return {"score": 2, "level": "偏弱", "message": f"ROE为{roe:.2f}%，需要进一步研究盈利能力。"}


def analyze_debt_ratio(debt_ratio):
    if debt_ratio is None:
        return {"score": 0, "level": "数据不足", "message": "缺少资产负债率数据。"}
    if debt_ratio < 50:
        return {"score": 0, "level": "稳健", "message": f"资产负债率为{debt_ratio:.2f}%，整体较稳健。"}
    if debt_ratio < 70:
        return {"score": 1, "level": "需要关注", "message": f"资产负债率为{debt_ratio:.2f}%，需要持续观察。"}
    return {"score": 3, "level": "高风险信号", "message": f"资产负债率为{debt_ratio:.2f}%，杠杆水平较高。"}


def analyze_trend_risk(profit_report=None, balance=None, cashflow=None):
    """尝试识别应收/存货/商誉/资本开支的深度风险。字段缺失时返回数据不足，不强行判断。"""
    meta = {
        "available": False,
        "score": 0,
        "hard_veto": False,
        "items": [],
        "metrics": {}
    }

    revenue = _series(profit_report, ["营业总收入", "营业收入", "TOTALOPERATEREVE", "营业总收入(元)"])
    receivable = _series(balance, ["应收账款", "应收账款净额", "ACCOUNTS_RECE", "应收账款(元)"])
    inventory = _series(balance, ["存货", "存货净额", "INVENTORY", "存货(元)"])
    goodwill = _series(balance, ["商誉", "GOODWILL", "商誉净额", "商誉(元)"])
    assets = _series(balance, ["资产总计", "TOTAL_ASSETS", "总资产"])
    ocf = _series(cashflow, ["经营活动产生的现金流量净额", "NETCASH_OPERATE", "经营活动现金流量净额"])
    capex = _series(cashflow, ["购建固定资产、无形资产和其他长期资产所支付的现金", "购建固定资产、无形资产和其他长期资产支付的现金", "CAPEX", "资本开支"])
    depreciation = _series(cashflow, ["固定资产折旧", "折旧", "折旧摊销", "固定资产折旧及摊销"])

    if revenue is not None and receivable is not None:
        n = min(len(revenue), len(receivable))
        rr = receivable.iloc[-n:].reset_index(drop=True) / revenue.iloc[-n:].reset_index(drop=True).replace(0, float("nan"))
        rr = rr.dropna()
        if len(rr) >= 2:
            start, end = float(rr.iloc[0]), float(rr.iloc[-1])
            meta["available"] = True
            meta["metrics"]["receivable_to_revenue"] = end
            meta["metrics"]["receivable_ratio_change"] = end - start
            if end >= 0.40 or end - start >= 0.10:
                meta["score"] += 2
                meta["items"].append("应收账款/营收比例偏高或上升过快，存在回款与坏账风险。")

    if revenue is not None and inventory is not None:
        n = min(len(revenue), len(inventory))
        ir = inventory.iloc[-n:].reset_index(drop=True) / revenue.iloc[-n:].reset_index(drop=True).replace(0, float("nan"))
        ir = ir.dropna()
        if len(ir) >= 2:
            start, end = float(ir.iloc[0]), float(ir.iloc[-1])
            meta["available"] = True
            meta["metrics"]["inventory_to_revenue"] = end
            meta["metrics"]["inventory_ratio_change"] = end - start
            if end >= 0.50 or end - start >= 0.15:
                meta["score"] += 2
                meta["items"].append("存货/营收比例偏高或上升较快，存在周转放缓和减值风险。")

    if goodwill is not None and assets is not None:
        n = min(len(goodwill), len(assets))
        gr = goodwill.iloc[-n:].reset_index(drop=True) / assets.iloc[-n:].reset_index(drop=True).replace(0, float("nan"))
        gr = gr.dropna()
        if not gr.empty:
            end = float(gr.iloc[-1])
            meta["available"] = True
            meta["metrics"]["goodwill_to_assets"] = end
            if end >= 0.20:
                meta["score"] += 2
                meta["items"].append("商誉占总资产比例较高，需重点防范并购减值风险。")
            elif end >= 0.10:
                meta["score"] += 1
                meta["items"].append("商誉占比较高，建议核查并购标的盈利兑现与减值压力。")

    if ocf is not None and capex is not None and not ocf.empty and not capex.empty:
        o = abs(float(ocf.iloc[-1]))
        c = max(float(capex.iloc[-1]), 0.0)
        if o > 0:
            ratio = c / o
            meta["available"] = True
            meta["metrics"]["capex_to_ocf"] = ratio
            if float(ocf.iloc[-1]) < 0 and c > 0:
                meta["hard_veto"] = True
                meta["score"] += 3
                meta["items"].append("经营现金流为负且仍有资本开支，现金安全垫存在压力。")
            elif ratio >= 1.0:
                meta["score"] += 2
                meta["items"].append("资本开支达到或超过经营现金流，需确认扩产回报与融资来源。")
            elif ratio >= 0.70:
                meta["score"] += 1
                meta["items"].append("资本开支较高，建议继续观察自由现金流。")

    if depreciation is not None and capex is not None and not depreciation.empty and not capex.empty:
        d = abs(float(depreciation.iloc[-1]))
        c = max(float(capex.iloc[-1]), 0.0)
        if d > 0:
            meta["metrics"]["capex_to_depreciation"] = c / d

    if meta["score"] >= 5:
        meta["hard_veto"] = True

    return meta


def analyze_financial_risk(
    operating_cashflow,
    net_profit,
    receivable,
    revenue,
    inventory,
    roe,
    debt_ratio,
    **kwargs
):
    cashflow_result = analyze_cashflow_quality(operating_cashflow, net_profit)
    receivable_result = analyze_receivable(receivable, revenue)
    inventory_result = analyze_inventory(inventory, revenue)
    roe_result = analyze_roe(roe)
    debt_result = analyze_debt_ratio(debt_ratio)

    deep = analyze_trend_risk(
        profit_report=kwargs.get("profit_report"),
        balance=kwargs.get("balance"),
        cashflow=kwargs.get("cashflow"),
    )

    total_score = (
        cashflow_result["score"]
        + receivable_result["score"]
        + inventory_result["score"]
        + roe_result["score"]
        + debt_result["score"]
        + deep["score"]
    )

    hard_veto = bool(deep.get("hard_veto"))
    if cashflow_result["score"] >= 3 and safe_float(net_profit) is not None and safe_float(net_profit) > 0:
        hard_veto = True

    if hard_veto:
        level = "高风险 / 否决"
    elif total_score == 0:
        level = "低风险"
    elif total_score <= 3:
        level = "风险较低"
    elif total_score <= 6:
        level = "需要关注"
    elif total_score <= 9:
        level = "风险较高"
    else:
        level = "高风险"

    risk_items = []
    for result in [cashflow_result, receivable_result, inventory_result, roe_result, debt_result]:
        if result["score"] > 0:
            risk_items.append(result["message"])
    risk_items.extend(deep.get("items", []))

    return {
        "score": total_score,
        "level": level,
        "hard_veto": hard_veto,
        "cashflow": cashflow_result,
        "receivable": receivable_result,
        "inventory": inventory_result,
        "roe": roe_result,
        "debt": debt_result,
        "deep_risk": deep,
        "risk_items": risk_items,
    }
