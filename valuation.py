"""
ValueStock AI
估值计算模块 V16.7

升级：
- 保留原PE/PB计算接口，确保主程序兼容。
- 成长科技模型在调用adaptive_valuation后，优先使用TTM EPS倍数修正估值分母。
"""


def _get_eps_multiplier():
    """读取成长科技模型当前的EPS分母修正系数。"""
    try:
        from adaptive_valuation import LAST_MODEL, LAST_EARNINGS_BASIS
        if LAST_MODEL == "growth_tech":
            annual_eps = LAST_EARNINGS_BASIS.get("annual_eps")
            valuation_eps = LAST_EARNINGS_BASIS.get("valuation_eps")
            if (
                annual_eps is not None
                and valuation_eps is not None
                and annual_eps > 0
                and valuation_eps > 0
            ):
                return max(1.0, min(3.0, float(valuation_eps) / float(annual_eps)))
    except Exception:
        pass
    return 1.0


def calculate_pe_value(eps, target_pe):
    if eps is None or target_pe is None:
        return None
    if eps <= 0 or target_pe <= 0:
        return None

    multiplier = _get_eps_multiplier()
    adjusted_eps = eps * multiplier
    return adjusted_eps * target_pe


def calculate_pb_value(bvps, target_pb):
    if bvps is None or target_pb is None:
        return None
    if bvps <= 0 or target_pb <= 0:
        return None
    return bvps * target_pb


def calculate_combined_value(
    pe_value,
    pb_value,
    pe_weight=0.6,
    pb_weight=0.4
):
    if pe_weight < 0 or pb_weight < 0:
        return None

    total_weight = pe_weight + pb_weight
    if total_weight <= 0:
        return None

    pe_weight = pe_weight / total_weight
    pb_weight = pb_weight / total_weight

    if pe_value is not None and pb_value is not None:
        return pe_value * pe_weight + pb_value * pb_weight
    if pe_value is not None:
        return pe_value
    if pb_value is not None:
        return pb_value
    return None


def calculate_price_zone(normal_value, entry_ratio=0.85, heavy_ratio=0.70):
    result = {"entry_price": None, "heavy_price": None}

    if normal_value is None or normal_value <= 0:
        return result
    if entry_ratio <= 0 or heavy_ratio <= 0:
        return result

    result["entry_price"] = normal_value * entry_ratio
    result["heavy_price"] = normal_value * heavy_ratio
    return result


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
    pb_weight=0.4
):
    pe_conservative = calculate_pe_value(eps, conservative_pe)
    pe_normal = calculate_pe_value(eps, normal_pe)
    pe_optimistic = calculate_pe_value(eps, optimistic_pe)

    pb_conservative = calculate_pb_value(bvps, conservative_pb)
    pb_normal = calculate_pb_value(bvps, normal_pb)
    pb_optimistic = calculate_pb_value(bvps, optimistic_pb)

    conservative_value = calculate_combined_value(
        pe_conservative, pb_conservative, pe_weight, pb_weight
    )
    normal_value = calculate_combined_value(
        pe_normal, pb_normal, pe_weight, pb_weight
    )
    optimistic_value = calculate_combined_value(
        pe_optimistic, pb_optimistic, pe_weight, pb_weight
    )

    price_zone = calculate_price_zone(normal_value)

    return {
        "conservative": conservative_value,
        "normal": normal_value,
        "optimistic": optimistic_value,
        "entry_price": price_zone["entry_price"],
        "heavy_price": price_zone["heavy_price"]
    }
