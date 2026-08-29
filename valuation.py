"""
ValueStock AI
估值计算模块 V18.0

原则：
1. 主程序直接传入估值用EPS，不重复应用盈利兑现系数。
2. PE/PB两条路径分别计算，再按模型权重综合。
3. 新增“历史盈利情景估值”：只使用已实现EPS序列计算CAGR，
   未来价格只是情景敏感性分析，不作为事实预测。
"""


def calculate_pe_value(eps, target_pe):
    if eps is None or target_pe is None or eps <= 0 or target_pe <= 0:
        return None
    return float(eps) * float(target_pe)


def calculate_pb_value(bvps, target_pb):
    if bvps is None or target_pb is None or bvps <= 0 or target_pb <= 0:
        return None
    return float(bvps) * float(target_pb)


def calculate_combined_value(pe_value, pb_value, pe_weight=0.6, pb_weight=0.4):
    if pe_weight < 0 or pb_weight < 0:
        return None
    total = pe_weight + pb_weight
    if total <= 0:
        return None
    pe_weight /= total
    pb_weight /= total
    if pe_value is not None and pb_value is not None:
        return pe_value * pe_weight + pb_value * pb_weight
    if pe_value is not None:
        return pe_value
    return pb_value


def calculate_price_zone(normal_value, entry_ratio=0.85, heavy_ratio=0.70):
    if normal_value is None or normal_value <= 0:
        return {"entry_price": None, "heavy_price": None}
    return {
        "entry_price": normal_value * entry_ratio,
        "heavy_price": normal_value * heavy_ratio,
    }


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
):
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
    zone = calculate_price_zone(values[1])
    return {
        "conservative": values[0],
        "normal": values[1],
        "optimistic": values[2],
        "entry_price": zone["entry_price"],
        "heavy_price": zone["heavy_price"],
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
    }


def calculate_eps_cagr(trend, years=3):
    """从已经实现的年度EPS序列计算历史CAGR；不足数据时返回None。"""
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
    """构建历史盈利支持下的情景敏感性表。

    增长率优先来自已实现EPS CAGR；保守/乐观只是在历史CAGR上下调整，
    并设上限，避免模型为了抬高科技股估值而无限外推。
    """
    if base_eps is None or base_eps <= 0 or normal_pe is None or normal_pe <= 0:
        return []
    if historical_cagr is None:
        return []

    hist = max(-0.30, min(float(max_growth), float(historical_cagr)))
    if conservative_growth is None:
        conservative_growth = max(-0.20, hist - 0.10)
    if optimistic_growth is None:
        optimistic_growth = min(float(max_growth), hist + 0.10)

    scenarios = [
        ("保守", conservative_growth),
        ("历史趋势", hist),
        ("乐观", optimistic_growth),
    ]
    rows = []
    for label, growth in scenarios:
        eps_future = float(base_eps) * ((1.0 + float(growth)) ** int(years))
        value = eps_future * float(normal_pe)
        rows.append({
            "情景": label,
            "年化EPS增长假设": float(growth),
            "第N年EPS": eps_future,
            "第N年PE": float(normal_pe),
            "第N年情景价值": value,
        })
    return rows
