"""ValueStock AI 公司治理与股东结构分析 V1.1

只消费主流程已取得的数据；无法确认的事项返回“数据不足”，不做主观猜测。
兼容新浪主要股东与东方财富十大股东字段。
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


def _latest_date_df(df):
    if df is None or getattr(df, "empty", True):
        return None
    date_col = _find(df, ["截至日期", "报告日期", "报告期", "日期", "公告日期"])
    if date_col is None:
        return df.copy()
    try:
        tmp = df.copy()
        tmp["_gov_date"] = __import__("pandas").to_datetime(tmp[date_col], errors="coerce")
        latest = tmp["_gov_date"].max()
        if __import__("pandas").notna(latest):
            tmp = tmp[tmp["_gov_date"] == latest]
        return tmp.drop(columns=["_gov_date"], errors="ignore").reset_index(drop=True)
    except Exception:
        return df.copy()


def _pct(v):
    x = _num(v)
    if x is None:
        return None
    return x * 100 if x <= 1 else x


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

    # =========================
    # 1. 股东集中度
    # =========================
    sh = _latest_date_df(shareholders)
    if sh is not None and not getattr(sh, "empty", True):
        pct_col = _find(sh, [
            "持股比例(%)",
            "持股比例（%）",
            "持股比例",
            "占总股本持股比例",
            "占总流通股本持股比例",
        ])
        name_col = _find(sh, ["股东名称", "股东", "股东名称(机构)"])
        rank_col = _find(sh, ["名次", "编号", "序号"])

        if pct_col:
            vals = [_pct(v) for v in sh[pct_col].tolist()]
            vals = [v for v in vals if v is not None]
            if vals:
                result["available"] = True
                top1 = max(vals)
                top10 = sum(vals[:10])
                result["metrics"]["top1_holder_pct"] = top1
                result["metrics"]["top10_holder_pct"] = top10

                if top1 >= 50:
                    result["score"] += 1
                    result["items"].append("第一大股东持股高度集中，需关注控制权与中小股东利益平衡。")
                elif top1 >= 30:
                    result["score"] += 0.5
                    result["items"].append("第一大股东持股相对集中，建议持续关注控制权稳定性。")

                if top10 >= 80:
                    result["items"].append("前十大股东持股集中度较高，建议结合股权质押与实际控制权进一步核查。")

        # 新浪“主要股东”通常已经按股东序号排列，可直接识别第一大股东名称。
        if name_col:
            try:
                result["metrics"]["top1_holder_name"] = str(sh.iloc[0][name_col])
            except Exception:
                pass

        if rank_col:
            result["metrics"]["shareholder_rows"] = len(sh)

    # =========================
    # 2. 关联交易
    # =========================
    rp = _latest_date_df(related_party)
    if rp is not None and not getattr(rp, "empty", True):
        amount_col = _find(rp, ["关联交易金额", "关联交易总额", "关联交易金额(元)", "关联交易金额（元）"])
        income_col = _find(rp, ["营业收入", "营业总收入"])
        if amount_col and income_col:
            a, r = _num(rp.iloc[0][amount_col]), _num(rp.iloc[0][income_col])
            ratio = None if a is None or r in {None, 0} else a / r
            if ratio is not None:
                result["available"] = True
                result["metrics"]["related_party_to_revenue"] = ratio
                if ratio >= 0.20:
                    result["score"] += 2
                    result["items"].append("可识别关联交易规模较大，占收入比例较高，建议核查定价公允性与资金往来。")

    # =========================
    # 3. 治理结论
    # =========================
    if result["available"]:
        if result["score"] >= 2:
            result["level"] = "需要关注"
        elif result["score"] >= 1:
            result["level"] = "轻度关注"
        else:
            result["level"] = "暂未见明显异常"
    else:
        result["level"] = "数据不足"

    return result
