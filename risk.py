"""
ValueStock AI
财务风险分析模块 V2

兼容两种调用方式：
1. 旧版 7 参数调用：
   analyze_financial_risk(operating_cashflow, net_profit, receivable,
                          revenue, inventory, roe, debt_ratio)
2. 当前 app.py 4 参数调用：
   analyze_financial_risk(balance, profit, cashflow, fin)
"""


def safe_ratio(a, b):
    """安全计算比例"""
    try:
        if a is None or b is None or b == 0:
            return None
        return float(a) / float(b)
    except Exception:
        return None


def _safe_float(v):
    try:
        if v is None:
            return None
        s = str(v).strip().replace(",", "").replace("%", "")
        if s in {"", "--", "None", "none", "NaN", "nan", "null", "NULL", "-"}:
            return None
        return float(s)
    except Exception:
        return None


def _latest_value(df, candidates):
    """从财务报表中尽量稳健地取得最新一期字段。"""
    if df is None or getattr(df, "empty", True):
        return None
    try:
        cols = list(df.columns)
        col = None
        for name in candidates:
            if name in cols:
                col = name
                break
        if col is None:
            normalized = {
                str(c).strip().replace(" ", "").replace("（", "(").replace("）", ")"): c
                for c in cols
            }
            for name in candidates:
                key = str(name).strip().replace(" ", "").replace("（", "(").replace("）", ")")
                if key in normalized:
                    col = normalized[key]
                    break
        if col is None:
            return None

        # 报表通常已经按最新日期排在前面；若存在日期列，再按日期取最新值。
        date_cols = ["报告日期", "报告期", "截止日期", "REPORT_DATE", "日期", "date"]
        date_col = next((c for c in date_cols if c in cols), None)
        if date_col is not None:
            import pandas as pd
            x = df.copy()
            x["_risk_date"] = pd.to_datetime(x[date_col], errors="coerce")
            x = x.sort_values("_risk_date").dropna(subset=["_risk_date"])
            if not x.empty:
                return _safe_float(x.iloc[-1][col])
        return _safe_float(df.iloc[0][col])
    except Exception:
        return None


def _extract_current_risk_inputs(balance, profit, cashflow, fin):
    """把当前 app 的四类数据转换成旧风险引擎需要的 7 个指标。"""
    annual = (fin or {}).get("annual") if isinstance(fin, dict) else {}
    annual = annual if isinstance(annual, dict) else {}

    operating_cashflow = _latest_value(
        cashflow,
        [
            "经营活动产生的现金流量净额",
            "经营活动现金流量净额",
            "经营活动产生的现金流量净额(元)",
            "NETCASH_OPERATE",
            "经营现金流",
        ],
    )
    net_profit = _latest_value(
        profit,
        [
            "归属于母公司所有者的净利润",
            "归属于母公司股东的净利润",
            "归母净利润",
            "净利润",
            "NETPROFIT",
            "PARENTNETPROFIT",
        ],
    )
    revenue = _latest_value(
        profit,
        [
            "营业总收入",
            "营业收入",
            "主营业务收入",
            "TOTALOPERATEREVE",
            "TOTAL_OPERATE_INCOME",
        ],
    )
    receivable = _latest_value(
        balance,
        [
            "应收账款",
            "应收帐款",
            "ACCOUNTS_RECE",
            "应收账款净额",
        ],
    )
    inventory = _latest_value(
        balance,
        [
            "存货",
            "INVENTORY",
            "存货净额",
        ],
    )

    roe = _safe_float(annual.get("roe"))
    debt_ratio = _safe_float(annual.get("debt"))

    # 若当前年度财务指标缺失，再从最新指标中兜底。
    if roe is None and isinstance(fin, dict):
        roe = _safe_float((fin.get("latest") or {}).get("roe"))
    if debt_ratio is None and isinstance(fin, dict):
        debt_ratio = _safe_float((fin.get("latest") or {}).get("debt"))

    return (
        operating_cashflow,
        net_profit,
        receivable,
        revenue,
        inventory,
        roe,
        debt_ratio,
    )


def analyze_cashflow_quality(operating_cashflow, net_profit):
    """分析经营现金流与净利润匹配程度。"""
    ratio = safe_ratio(operating_cashflow, net_profit)
    if ratio is None:
        return {
            "ratio": None,
            "score": 0,
            "level": "数据不足",
            "message": "缺少经营现金流或净利润数据。",
        }
    if ratio >= 1:
        return {
            "ratio": ratio,
            "score": 0,
            "level": "优秀",
            "message": "经营现金流能够覆盖净利润，利润现金含量较好。",
        }
    if ratio >= 0.7:
        return {
            "ratio": ratio,
            "score": 1,
            "level": "良好",
            "message": "经营现金流与净利润基本匹配，需要继续观察。",
        }
    if ratio >= 0:
        return {
            "ratio": ratio,
            "score": 2,
            "level": "需要关注",
            "message": "经营现金流明显低于净利润，需要进一步排查利润质量。",
        }
    return {
        "ratio": ratio,
        "score": 3,
        "level": "高风险",
        "message": "经营现金流为负，而净利润可能为正，需要重点排查。",
    }


def analyze_receivable(receivable, revenue):
    """分析应收账款占营业收入比例。"""
    ratio = safe_ratio(receivable, revenue)
    if ratio is None:
        return {
            "ratio": None,
            "score": 0,
            "level": "数据不足",
            "message": "缺少应收账款或营业收入数据。",
        }
    if ratio > 0.40:
        return {
            "ratio": ratio,
            "score": 3,
            "level": "高风险信号",
            "message": "应收账款占营业收入比例较高，需要重点检查回款能力。",
        }
    if ratio > 0.25:
        return {
            "ratio": ratio,
            "score": 1,
            "level": "需要关注",
            "message": "应收账款占比较高，需要结合历史趋势观察。",
        }
    return {
        "ratio": ratio,
        "score": 0,
        "level": "正常",
        "message": "应收账款/营业收入比例暂未显示明显异常。",
    }


def analyze_inventory(inventory, revenue):
    """分析存货占营业收入比例。"""
    ratio = safe_ratio(inventory, revenue)
    if ratio is None:
        return {
            "ratio": None,
            "score": 0,
            "level": "数据不足",
            "message": "缺少存货或营业收入数据。",
        }
    if ratio > 0.50:
        return {
            "ratio": ratio,
            "score": 3,
            "level": "高风险信号",
            "message": "存货相对营业规模较高，需要检查库存周转和减值风险。",
        }
    if ratio > 0.30:
        return {
            "ratio": ratio,
            "score": 1,
            "level": "需要关注",
            "message": "存货占比需要继续观察。",
        }
    return {
        "ratio": ratio,
        "score": 0,
        "level": "正常",
        "message": "存货/营业收入比例暂未显示明显异常。",
    }


def analyze_roe(roe):
    """分析 ROE。"""
    if roe is None:
        return {"score": 0, "level": "数据不足", "message": "缺少ROE数据。"}
    if roe >= 15:
        return {"score": 0, "level": "良好", "message": f"ROE为{roe:.2f}%，资本回报能力较好。"}
    if roe >= 10:
        return {"score": 1, "level": "一般", "message": f"ROE为{roe:.2f}%，资本回报能力一般。"}
    return {"score": 2, "level": "偏弱", "message": f"ROE为{roe:.2f}%，需要进一步研究盈利能力。"}


def analyze_debt_ratio(debt_ratio):
    """分析资产负债率。"""
    if debt_ratio is None:
        return {"score": 0, "level": "数据不足", "message": "缺少资产负债率数据。"}
    if debt_ratio < 50:
        return {"score": 0, "level": "稳健", "message": f"资产负债率为{debt_ratio:.2f}%，整体较稳健。"}
    if debt_ratio < 70:
        return {"score": 1, "level": "需要关注", "message": f"资产负债率为{debt_ratio:.2f}%，需要持续观察。"}
    return {"score": 3, "level": "高风险信号", "message": f"资产负债率为{debt_ratio:.2f}%，杠杆水平较高。"}


def analyze_financial_risk(*args, **kwargs):
    """综合财务风险分析，兼容旧版 7 参数和当前 4 参数接口。"""
    if len(args) == 4 and not kwargs:
        operating_cashflow, net_profit, receivable, revenue, inventory, roe, debt_ratio = _extract_current_risk_inputs(*args)
    elif len(args) == 7:
        operating_cashflow, net_profit, receivable, revenue, inventory, roe, debt_ratio = args
    else:
        # 尽可能支持关键字形式，避免不同版本 app.py 再次因签名变化崩溃。
        if len(args) == 0:
            operating_cashflow = kwargs.get("operating_cashflow")
            net_profit = kwargs.get("net_profit")
            receivable = kwargs.get("receivable")
            revenue = kwargs.get("revenue")
            inventory = kwargs.get("inventory")
            roe = kwargs.get("roe")
            debt_ratio = kwargs.get("debt_ratio")
            if any(v is not None for v in (operating_cashflow, net_profit, receivable, revenue, inventory, roe, debt_ratio)):
                pass
            else:
                balance = kwargs.get("balance")
                profit = kwargs.get("profit")
                cashflow = kwargs.get("cashflow")
                fin = kwargs.get("fin")
                if balance is not None or profit is not None or cashflow is not None or fin is not None:
                    operating_cashflow, net_profit, receivable, revenue, inventory, roe, debt_ratio = _extract_current_risk_inputs(balance, profit, cashflow, fin)
                else:
                    raise TypeError("analyze_financial_risk 参数不足")
        else:
            raise TypeError("analyze_financial_risk 参数数量不兼容")

    cashflow_result = analyze_cashflow_quality(operating_cashflow, net_profit)
    receivable_result = analyze_receivable(receivable, revenue)
    inventory_result = analyze_inventory(inventory, revenue)
    roe_result = analyze_roe(roe)
    debt_result = analyze_debt_ratio(debt_ratio)

    total_score = (
        cashflow_result["score"]
        + receivable_result["score"]
        + inventory_result["score"]
        + roe_result["score"]
        + debt_result["score"]
    )

    if total_score == 0:
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

    return {
        "score": total_score,
        "level": level,
        "cashflow": cashflow_result,
        "receivable": receivable_result,
        "inventory": inventory_result,
        "roe": roe_result,
        "debt": debt_result,
        "risk_items": risk_items,
    }
