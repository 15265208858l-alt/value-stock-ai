"""ValueStock AI 估值计算模块 V19.0

原则：
- 估值数据缺失时安全降级，不让 Streamlit 页面因 None/格式化异常崩溃。
- PE 与 PB 均可用时按模型权重合成；单一路径可用时自动降级到可用路径。
- 输出保守/中性/乐观价值，以及建仓/重仓/高估参考价区间。
- 新增安全边际、估值状态和分层买入计划计算，但保持旧版函数接口兼容。
"""


class UnavailableValuation(float):
    """兼容旧页面格式化逻辑的“暂无”数值占位符。"""

    def __new__(cls):
        return float.__new__(cls, 0.0)

    def __format__(self, spec):
        return "暂无"

    def __repr__(self):
        return "UnavailableValuation()"


UNAVAILABLE_VALUATION = UnavailableValuation()


def _positive(v):
    try:
        value = float(v)
        return value if value > 0 else None
    except Exception:
        return None


def _clamp(v, lo, hi):
    return max(float(lo), min(float(hi), float(v)))


def calculate_pe_value(eps, target_pe):
    eps = _positive(eps)
    target_pe = _positive(target_pe)
    if eps is None or target_pe is None:
        return None
    return eps * target_pe


def calculate_pb_value(bvps, target_pb):
    bvps = _positive(bvps)
    target_pb = _positive(target_pb)
    if bvps is None or target_pb is None:
        return None
    return bvps * target_pb


def calculate_combined_value(pe_value, pb_value, pe_weight=0.6, pb_weight=0.4):
    try:
        pe_weight = max(0.0, float(pe_weight))
        pb_weight = max(0.0, float(pb_weight))
    except Exception:
        return None

    total = pe_weight + pb_weight
    if total <= 0:
        return None
    pe_weight /= total
    pb_weight /= total

    if pe_value is not None and pb_value is not None:
        return float(pe_value) * pe_weight + float(pb_value) * pb_weight
    if pe_value is not None:
        return float(pe_value)
    if pb_value is not None:
        return float(pb_value)
    return None


def calculate_price_zone(normal_value, entry_ratio=0.85, heavy_ratio=0.70, high_ratio=1.15):
    """根据中性合理价值计算安全边际价格带。

    entry_price：约15%安全边际。
    heavy_price：约30%安全边际。
    high_price：中性合理价值上方约15%，作为“明显高估警戒线”。
    """
    normal = _positive(normal_value)
    if normal is None:
        return {
            "entry_price": UNAVAILABLE_VALUATION,
            "heavy_price": UNAVAILABLE_VALUATION,
            "high_price": UNAVAILABLE_VALUATION,
        }

    try:
        entry_ratio = float(entry_ratio)
        heavy_ratio = float(heavy_ratio)
        high_ratio = float(high_ratio)
    except Exception:
        entry_ratio, heavy_ratio, high_ratio = 0.85, 0.70, 1.15

    # 保证区间逻辑正确，防止传入参数导致“重仓价高于建仓价”。
    heavy_ratio = min(heavy_ratio, entry_ratio)
    high_ratio = max(high_ratio, 1.0)

    return {
        "entry_price": normal * entry_ratio,
        "heavy_price": normal * heavy_ratio,
        "high_price": normal * high_ratio,
    }


def calculate_safety_margin(current_price, fair_value):
    """计算当前价格相对合理价值的安全边际百分比。正数=低于合理价值。"""
    try:
        price = float(current_price)
        fair = float(fair_value)
        if price <= 0 or fair <= 0:
            return None
        return (fair - price) / fair
    except Exception:
        return None


def classify_valuation_status(current_price, fair_value, heavy_price=None, entry_price=None, high_price=None):
    """把当前价格映射为可解释的估值状态。"""
    try:
        price = float(current_price)
    except Exception:
        return {"level": "数据不足", "message": "缺少当前价格或估值数据。"}

    fair = _positive(fair_value)
    if fair is None:
        return {"level": "数据不足", "message": "合理价值暂时无法计算。"}

    heavy = _positive(heavy_price)
    entry = _positive(entry_price)
    high = _positive(high_price)

    if heavy is not None and price <= heavy:
        return {"level": "深度价值区", "message": "价格已进入较高安全边际区域，可重点研究分批建仓条件。"}
    if entry is not None and price <= entry:
        return {"level": "价值区", "message": "价格低于建议建仓价，具备一定安全边际。"}
    if price <= fair:
        return {"level": "合理区", "message": "价格处于合理价值附近，可结合企业质量决定是否观察或分批布局。"}
    if high is not None and price >= high:
        return {"level": "高估区", "message": "价格明显高于合理价值，原则上不追高。"}
    return {"level": "偏贵区", "message": "价格高于合理价值，等待更好的安全边际。"}


def build_buying_plan(normal_value, current_price=None, risk_level=None, confidence="中", valuation_quality="正常"):
    """建立实战分层买入计划。

    说明：这是估值层的价格纪律，不替代风险否决层；高风险公司不会因低估值自动变成可买。
    """
    zone = calculate_price_zone(normal_value)
    fair = _positive(normal_value)
    current = _positive(current_price)

    plan = {
        "fair_value": fair,
        "entry_price": None if isinstance(zone["entry_price"], UnavailableValuation) else float(zone["entry_price"]),
        "heavy_price": None if isinstance(zone["heavy_price"], UnavailableValuation) else float(zone["heavy_price"]),
        "high_price": None if isinstance(zone["high_price"], UnavailableValuation) else float(zone["high_price"]),
        "safety_margin": calculate_safety_margin(current, fair) if current is not None and fair is not None else None,
        "status": "数据不足",
        "suggested_position": "0%",
        "discipline": "等待更多数据。",
    }

    if fair is None:
        return plan

    status = classify_valuation_status(current, fair, plan["heavy_price"], plan["entry_price"], plan["high_price"]) if current is not None else {"level": "等待价格", "message": "合理价值已形成，等待当前价格判断。"}
    plan["status"] = status["level"]
    plan["message"] = status["message"]

    risk = str(risk_level or "").strip()
    conf = str(confidence or "中").strip()
    vq = str(valuation_quality or "正常").strip()

    # 风险优先级高于估值：高风险或数据不足不主动给仓位。
    if risk in {"高风险", "高风险 / 否决"}:
        plan["suggested_position"] = "0%"
        plan["discipline"] = "风险否决：不得仅凭低估值建仓。"
        return plan

    if current is None:
        plan["suggested_position"] = "0%"
        plan["discipline"] = "等待市场价格后再判断。"
        return plan

    if conf == "低":
        plan["suggested_position"] = "0%"
        plan["discipline"] = "数据置信度较低，先补齐关键数据。"
        return plan

    if vq in {"异常", "偏弱"}:
        plan["suggested_position"] = "0%"
        plan["discipline"] = "盈利质量存在疑点，价格优势不足以抵消基本面不确定性。"
        return plan

    if plan["heavy_price"] is not None and current <= plan["heavy_price"]:
        plan["suggested_position"] = "30%-50%"
        plan["discipline"] = "深度价值区：前提是风险层未否决，可考虑分批建立较高仓位。"
    elif plan["entry_price"] is not None and current <= plan["entry_price"]:
        plan["suggested_position"] = "10%-30%"
        plan["discipline"] = "价值区：优先小仓试探，再根据基本面验证逐步增加。"
    elif current <= fair:
        plan["suggested_position"] = "0%-10%"
        plan["discipline"] = "合理价值附近：以观察为主，不追求一次性满仓。"
    elif plan["high_price"] is not None and current >= plan["high_price"]:
        plan["suggested_position"] = "0%"
        plan["discipline"] = "高估区：原则上等待估值回落。"
    else:
        plan["suggested_position"] = "0%-5%"
        plan["discipline"] = "偏贵区：等待安全边际。"

    return plan


def calculate_valuation_scenarios(
    eps,
    bvps,
    conservative_pe,
    normal_pe,
    optimistic_pe,
    conservative_pb,
    normal_pb,
    optimistic_pb,
    pe_weight=0.6,
    pb_weight=0.4,
    current_price=None,
    risk_level=None,
    data_confidence="中",
):
    """计算三情景综合估值，并返回可直接供 Streamlit 使用的价格带。"""
    pe_values = (
        calculate_pe_value(eps, conservative_pe),
        calculate_pe_value(eps, normal_pe),
        calculate_pe_value(eps, optimistic_pe),
    )
    pb_values = (
        calculate_pb_value(bvps, conservative_pb),
        calculate_pb_value(bvps, normal_pb),
        calculate_pb_value(bvps, optimistic_pb),
    )

    values = [
        calculate_combined_value(pe_values[0], pb_values[0], pe_weight, pb_weight),
        calculate_combined_value(pe_values[1], pb_values[1], pe_weight, pb_weight),
        calculate_combined_value(pe_values[2], pb_values[2], pe_weight, pb_weight),
    ]

    if values[1] is None:
        values = [UNAVAILABLE_VALUATION] * 3

    zone = calculate_price_zone(values[1])
    normal_value = values[1]
    data_path = (
        "PE+PB"
        if pe_values[1] is not None and pb_values[1] is not None
        else "PE"
        if pe_values[1] is not None
        else "PB"
        if pb_values[1] is not None
        else "暂无"
    )

    plan = build_buying_plan(
        normal_value,
        current_price=current_price,
        risk_level=risk_level,
        confidence=data_confidence,
    )

    return {
        "conservative": values[0],
        "normal": normal_value,
        "optimistic": values[2],
        "entry_price": zone["entry_price"],
        "heavy_price": zone["heavy_price"],
        "high_price": zone["high_price"],
        "safety_margin": plan["safety_margin"],
        "valuation_status": plan["status"],
        "valuation_message": plan.get("message"),
        "suggested_position": plan["suggested_position"],
        "buying_discipline": plan["discipline"],
        "pe_values": {
            "conservative": pe_values[0],
            "normal": pe_values[1],
            "optimistic": pe_values[2],
        },
        "pb_values": {
            "conservative": pb_values[0],
            "normal": pb_values[1],
            "optimistic": pb_values[2],
        },
        "pe_weight": float(pe_weight),
        "pb_weight": float(pb_weight),
        "data_path": data_path,
        "data_complete": values[1] is not None,
    }


def calculate_eps_cagr(trend, years=3):
    try:
        if trend is None or trend.empty or "EPS" not in trend.columns:
            return None
        import pandas as pd

        data = trend.copy()
        if "报告期" in data.columns:
            data["_date"] = pd.to_datetime(data["报告期"], errors="coerce")
            data = data.sort_values("_date")
        data["EPS"] = pd.to_numeric(data["EPS"], errors="coerce")
        data = data.dropna(subset=["EPS"])
        data = data[data["EPS"] > 0]
        if len(data) < 2:
            return None
        use_n = min(len(data), int(years) + 1)
        first = float(data.iloc[-use_n]["EPS"])
        last = float(data.iloc[-1]["EPS"])
        actual_years = use_n - 1
        if first <= 0 or last <= 0 or actual_years <= 0:
            return None
        return (last / first) ** (1.0 / actual_years) - 1.0
    except Exception:
        return None


def build_growth_sensitivity(
    base_eps,
    normal_pe,
    years=3,
    historical_cagr=None,
    conservative_growth=None,
    optimistic_growth=None,
    max_growth=0.50,
):
    if base_eps is None or base_eps <= 0 or normal_pe is None or normal_pe <= 0 or historical_cagr is None:
        return []

    hist = float(historical_cagr)
    if hist > 0.50:
        scenarios = [("保守压力", 0.10), ("中性压力", 0.20), ("乐观压力", 0.30)]
    else:
        hist = max(-0.30, min(float(max_growth), hist))
        if conservative_growth is None:
            conservative_growth = max(-0.20, hist - 0.10)
        if optimistic_growth is None:
            optimistic_growth = min(float(max_growth), hist + (0.05 if hist > 0.30 else 0.10))
        scenarios = [("保守", conservative_growth), ("历史趋势", hist), ("乐观", optimistic_growth)]

    rows = []
    for label, growth in scenarios:
        eps_future = float(base_eps) * ((1.0 + float(growth)) ** int(years))
        value = eps_future * float(normal_pe)
        rows.append(
            {
                "情景": label,
                "年化EPS增长假设": float(growth),
                "第N年EPS": eps_future,
                "第N年PE": float(normal_pe),
                "第N年情景价值": value,
            }
        )
    return rows
