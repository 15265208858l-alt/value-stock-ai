"""ValueStock AI 估值计算模块 V18.3

原则：
- 估值数据缺失时安全降级，不让 Streamlit 页面因 None/格式化异常崩溃。
- PE 与 PB 均可用时按模型权重合成；单一路径可用时自动降级到可用路径。
- 输出保守/中性/乐观价值，以及建仓/重仓/高估参考价区间。
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

    return {
        "entry_price": normal * entry_ratio,
        "heavy_price": normal * heavy_ratio,
        "high_price": normal * high_ratio,
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

    # 中性价值不存在时，不允许页面继续使用一个“假合理价”。
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

    return {
        "conservative": values[0],
        "normal": normal_value,
        "optimistic": values[2],
        "entry_price": zone["entry_price"],
        "heavy_price": zone["heavy_price"],
        "high_price": zone["high_price"],
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
