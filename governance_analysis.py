"""ValueStock AI 公司治理与股东结构分析 V1.0

只消费主流程已取得的数据；无法确认的事项返回“数据不足”，不做主观猜测。
"""
from __future__ import annotations


def _num(v):
    try:
        if v is None:
            return None
        return float(str(v).strip().replace(",", "").replace("%", ""))
    except Exception:
        return None


def _find(df, names):
    if df is None or getattr(df, "empty", True):
        return None
    cols = list(df.columns)
    for name in names:
        if name in cols:
            return name
    norm = {str(c).replace(" ", "").replace("（", "(").replace("）", ")"): c for c in cols}
    for name in names:
        key = str(name).replace(" ", "").replace("（", "(").replace("）", ")")
        if key in norm:
            return norm[key]
    return None


def analyze_governance(balance=None, shareholders=None, related_party=None):
    """分析可识别的治理/股东/关联交易风险。"""
    result = {
        "available": False,
        "score": 0,
        "hard_veto": False,
        "level": "数据不足",
        "items": [],
        "metrics": {},
    }

    # 股东集中度：兼容常见第一大股东/前十大股东持股比例字段。
    if shareholders is not None and not getattr(shareholders, "empty", True):
        c1 = _find(shareholders, ["第一大股东持股比例", "第一大股东持股", "控股股东持股比例", "持股比例"])
        c10 = _find(shareholders, ["前十大股东持股比例", "十大股东持股比例"])
        if c1:
            v = _num(shareholders.iloc[0][c1])
            if v is not None:
                if v <= 1:
                    v *= 100
                result["available"] = True
                result["metrics"]["top1_holder_pct"] = v
                if v >= 50:
                    result["score"] += 1
                    result["items"].append("第一大股东持股高度集中，需关注控制权与中小股东利益平衡。")
        if c10:
            v = _num(shareholders.iloc[0][c10])
            if v is not None:
                if v <= 1:
                    v *= 100
                result["available"] = True
                result["metrics"]["top10_holder_pct"] = v

    # 关联交易：若已有结构化字段，重点识别关联交易占收入/采购或金额快速增加。
    if related_party is not None and not getattr(related_party, "empty", True):
        amount_col = _find(related_party, ["关联交易金额", "关联交易总额", "关联交易金额(元)"])
        income_col = _find(related_party, ["营业收入", "营业总收入"])
        if amount_col and income_col:
            a, r = _num(related_party.iloc[0][amount_col]), _num(related_party.iloc[0][income_col])
            ratio = None if a is None or r in {None, 0} else a / r
            if ratio is not None:
                result["available"] = True
                result["metrics"]["related_party_to_revenue"] = ratio
                if ratio >= 0.20:
                    result["score"] += 2
                    result["items"].append("可识别关联交易规模较大，占收入比例较高，建议核查定价公允性与资金往来。")

    # 当前数据没有可可靠治理数据时，不把未知当坏，也不把未知当好。
    if result["available"]:
        if result["score"] >= 2:
            result["level"] = "需要关注"
        elif result["score"] == 1:
            result["level"] = "轻度关注"
        else:
            result["level"] = "暂未见明显异常"
    return result
