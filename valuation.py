"""
ValueStock AI
估值计算模块 V17.2

说明：主程序直接传入“估值用EPS”（正常化EPS/年度EPS），
本模块不再偷偷二次调整EPS，避免盈利兑现系数被重复应用。
V17.2新增：返回PE/PB两条估值路径的中间结果，便于解释最终合理价由什么构成。
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
