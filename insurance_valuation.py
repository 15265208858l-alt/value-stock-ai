"""
ValueStock AI
保险专用估值模块 V16.6

目标：
1. 优先尝试从已有财务指标/报表中寻找保险行业核心价值数据。
2. 支持：内含价值（EV）、每股内含价值、每股新业务价值（NBV）等字段。
3. 数据不足时，不伪造数据，自动回退到 PB 主导估值。
4. 输出保守/中性/乐观价值区间与数据可信度说明。

说明：
EV/NBV 字段是否存在取决于底层数据源返回的字段。当前模块采用
“能取到就使用、取不到就明确标记”的原则，不用估算出来的假数据冒充
保险公司的披露 EV/NBV。
"""


import math


def _to_float(value):
    """安全转换数值。"""
    try:
        if value is None:
            return None
        text = str(value).strip()
        if text in {"", "--", "None", "none", "NaN", "nan"}:
            return None
        text = text.replace(",", "").replace("%", "")
        return float(text)
    except (TypeError, ValueError):
        return None


def _find_column(df, keywords):
    """在 DataFrame 中按关键词寻找字段，优先精确命中。"""
    if df is None or getattr(df, "empty", True):
        return None

    columns = [str(c) for c in df.columns]

    # 先精确
    for keyword in keywords:
        for column in columns:
            if column == keyword:
                return column

    # 再模糊
    for keyword in keywords:
        for column in columns:
            if keyword in column:
                return column

    return None


def extract_insurance_metrics(indicators=None, profit=None, balance=None):
    """
    尝试从现有数据中提取保险行业核心指标。

    返回：
    {
        "ev_total": 内含价值总额（如能找到）, 
        "ev_per_share": 每股内含价值（如能找到）, 
        "nbv_total": 新业务价值总额（如能找到）,
        "nbv_per_share": 每股新业务价值（如能找到）,
        "source": 字段来源说明
    }
    """

    frames = [
        ("财务指标", indicators),
        ("利润表", profit),
        ("资产负债表", balance),
    ]

    ev_total = None
    ev_per_share = None
    nbv_total = None
    nbv_per_share = None
    source = []

    for frame_name, df in frames:
        if df is None or getattr(df, "empty", True):
            continue

        # 内含价值 / 每股内含价值
        col = _find_column(
            df,
            [
                "每股内含价值",
                "内含价值(每股)",
                "内含价值每股",
                "Embedded Value Per Share",
            ]
        )
        if ev_per_share is None and col is not None:
            values = df[col].tolist()
            if values:
                ev_per_share = _to_float(values[0])
                if ev_per_share is not None:
                    source.append(f"{frame_name}:{col}")

        col = _find_column(
            df,
            [
                "内含价值",
                "寿险内含价值",
                "集团内含价值",
                "Embedded Value",
            ]
        )
        if ev_total is None and col is not None:
            values = df[col].tolist()
            if values:
                ev_total = _to_float(values[0])
                if ev_total is not None:
                    source.append(f"{frame_name}:{col}")

        # 新业务价值 / 每股新业务价值
        col = _find_column(
            df,
            [
                "每股新业务价值",
                "新业务价值(每股)",
                "新业务价值每股",
                "New Business Value Per Share",
            ]
        )
        if nbv_per_share is None and col is not None:
            values = df[col].tolist()
            if values:
                nbv_per_share = _to_float(values[0])
                if nbv_per_share is not None:
                    source.append(f"{frame_name}:{col}")

        col = _find_column(
            df,
            [
                "新业务价值",
                "寿险新业务价值",
                "New Business Value",
            ]
        )
        if nbv_total is None and col is not None:
            values = df[col].tolist()
            if values:
                nbv_total = _to_float(values[0])
                if nbv_total is not None:
                    source.append(f"{frame_name}:{col}")

    return {
        "ev_total": ev_total,
        "ev_per_share": ev_per_share,
        "nbv_total": nbv_total,
        "nbv_per_share": nbv_per_share,
        "source": source,
    }


def calculate_insurance_valuation(
    current_price,
    bvps,
    annual_roe=None,
    ev_per_share=None,
    nbv_per_share=None,
    fallback_normal_pb=0.95,
):
    """
    保险估值第二阶段。

    规则：
    - 若有每股EV：以EV为核心锚定价值，并用PB作为交叉验证。
    - 若没有EV：回退到PB主导模型。
    - NBV不直接当作存量价值乘以估值倍数，避免错误重复计价；
      它用于增强/降低估值可信度提示。
    """

    current_price = _to_float(current_price)
    bvps = _to_float(bvps)
    annual_roe = _to_float(annual_roe)
    ev_per_share = _to_float(ev_per_share)
    nbv_per_share = _to_float(nbv_per_share)
    fallback_normal_pb = _to_float(fallback_normal_pb) or 0.95

    pb_value = None
    if bvps is not None and bvps > 0:
        pb_value = bvps * fallback_normal_pb

    # -----------------------------------------------------
    # 情况A：有每股EV，进入EV+PB模型
    # -----------------------------------------------------
    if ev_per_share is not None and ev_per_share > 0:
        conservative = ev_per_share * 0.85
        normal = ev_per_share
        optimistic = ev_per_share * 1.15

        # PB交叉验证：如果PB价值偏离EV过大，只做温和修正。
        if pb_value is not None and pb_value > 0:
            normal = normal * 0.80 + pb_value * 0.20
            conservative = conservative * 0.85 + pb_value * 0.15
            optimistic = optimistic * 0.85 + pb_value * 0.15

        confidence = "较高" if nbv_per_share is not None else "中等"
        note = (
            "已检测到每股内含价值（EV），采用EV为核心、PB交叉验证；"
            + ("同时检测到每股NBV。" if nbv_per_share is not None else "当前未检测到每股NBV。")
        )

        return {
            "model": "保险EV+PB估值",
            "conservative": round(conservative, 2),
            "normal": round(normal, 2),
            "optimistic": round(optimistic, 2),
            "confidence": confidence,
            "ev_per_share": round(ev_per_share, 4),
            "nbv_per_share": None if nbv_per_share is None else round(nbv_per_share, 4),
            "pb_cross_value": None if pb_value is None else round(pb_value, 2),
            "note": note,
            "source": "底层财务数据自动提取",
        }

    # -----------------------------------------------------
    # 情况B：没有EV，严格回退，不伪造EV
    # -----------------------------------------------------
    if pb_value is None:
        return {
            "model": "保险估值（数据不足）",
            "conservative": None,
            "normal": None,
            "optimistic": None,
            "confidence": "低",
            "ev_per_share": None,
            "nbv_per_share": None if nbv_per_share is None else round(nbv_per_share, 4),
            "pb_cross_value": None,
            "note": "暂未检测到可直接使用的保险EV/每股EV，也缺少有效BPS，因此无法可靠估值。",
            "source": "底层数据不足",
        }

    # 基于ROE做轻微的PB区间调整，但不改变行业模型方向。
    if annual_roe is not None:
        if annual_roe >= 15:
            normal_pb = 1.05
        elif annual_roe >= 10:
            normal_pb = 1.00
        elif annual_roe >= 8:
            normal_pb = 0.95
        else:
            normal_pb = 0.85
    else:
        normal_pb = fallback_normal_pb

    normal = bvps * normal_pb
    conservative = bvps * max(0.70, normal_pb - 0.15)
    optimistic = bvps * min(1.25, normal_pb + 0.20)

    return {
        "model": "保险PB主导估值（EV/NBV未检测到）",
        "conservative": round(conservative, 2),
        "normal": round(normal, 2),
        "optimistic": round(optimistic, 2),
        "confidence": "中低",
        "ev_per_share": None,
        "nbv_per_share": None if nbv_per_share is None else round(nbv_per_share, 4),
        "pb_cross_value": round(pb_value, 2),
        "note": "未检测到可直接使用的EV字段，因此本次不伪造EV/NBV，暂以ROE调整后的PB主导估值。",
        "source": "PB+ROE回退模型",
    }


def build_insurance_price_zone(normal_value):
    """根据中性价值生成保险行业参考价格区间。"""
    normal_value = _to_float(normal_value)
    if normal_value is None or normal_value <= 0:
        return {
            "entry_price": None,
            "heavy_price": None,
        }

    return {
        "entry_price": round(normal_value * 0.85, 2),
        "heavy_price": round(normal_value * 0.70, 2),
    }
