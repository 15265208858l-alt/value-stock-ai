"""
ValueStock AI
估值计算模块 V18.1

原则：
1. 主程序直接传入估值用EPS，不重复应用盈利兑现系数。
2. PE/PB两条路径分别计算，再按模型权重综合。
3. 新增“历史盈利情景估值”：只使用已实现EPS序列计算CAGR。
4. 当历史EPS CAGR异常偏高时，不直接把历史高增长外推成目标价，
   改用固定的压力测试带宽，防止低基数/业绩跳升把估值无限抬高。
5. 当EPS与BPS均不可用时，估值模块必须安全降级，不能因为格式化None导致整页崩溃。
"""


class UnavailableValuation(float):
    """估值数据缺失时的安全占位值。

    以0作为内部比较值，使上层 `<= 0` 判断可以安全短路；
    展示时统一显示“暂无”，避免 Streamlit 因 `None:.2f` 崩溃。
    """

    def __new__(cls):
        return float.__new__(cls, 0.0)

    def __format__(self, spec):
        return "暂无"

    def __repr__(self):
        return "UnavailableValuation()"


UNAVAILABLE_VALUATION = UnavailableValuation()


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

    # EPS、BPS均缺失时，上层页面仍应完整展示，不能因为 None:.2f 崩溃。
    # 仅把“综合价值”使用安全占位；原始PE/PB路径仍保留None，便于诊断数据缺失。
    if values[1] is None:
        values = [
            UNAVAILABLE_VALUATION,
            UNAVAILABLE_VALUATION,
            UNAVAILABLE_VALUATION,
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
    """从已经实现的年度EPS序列计算CAGR；不足数据时返回None。"""
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
    """构建历史盈利压力测试。

    当历史CAGR处于正常区间（<=30%）时，使用历史趋势上下浮动；
    30%～50%时降低乐观外推幅度；超过50%时视为异常高增长，
    不再把历史CAGR直接当作未来增长，而采用10%/20%/30%的固定压力测试带宽。
    这样保留“增长对估值的敏感性”，同时避免低基数或单次业绩跃升制造虚高估值。
    """
    if base_eps is None or base_eps <= 0 or normal_pe is None or normal_pe <= 0:
        return []
    if historical_cagr is None:
        return []

    hist = float(historical_cagr)
    if hist > 0.50:
        scenarios = [
            ("保守压力", 0.10),
            ("中性压力", 0.20),
            ("乐观压力", 0.30),
        ]
    else:
        hist = max(-0.30, min(float(max_growth), hist))
        if conservative_growth is None:
            conservative_growth = max(-0.20, hist - 0.10)
        if optimistic_growth is None:
            optimistic_growth = min(float(max_growth), hist + (0.05 if hist > 0.30 else 0.10))
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
