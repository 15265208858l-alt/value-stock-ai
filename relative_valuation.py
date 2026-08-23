"""
ValueStock AI
相对估值模块 V17.0

目标：
1. 不再只看公司自身的绝对估值。
2. 使用同行 PE/PB 中位数，降低极端值对平均数的干扰。
3. 输出相对PE/PB位置与相对估值判断。
4. 只作为绝对估值的校准项，不替代企业内在价值模型。
"""

from __future__ import annotations

import pandas as pd


def _valid_series(df, column, exclude_code=None):
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype=float)

    data = df.copy()
    if exclude_code is not None and "代码" in data.columns:
        data = data[data["代码"] != exclude_code]

    series = pd.to_numeric(data[column], errors="coerce").dropna()
    series = series[series > 0]
    return series


def _ratio_score(ratio):
    if ratio is None:
        return None, "数据不足"
    if ratio <= 0.70:
        return 20.0, "明显低于同行"
    if ratio <= 0.85:
        return 17.0, "低于同行"
    if ratio <= 1.00:
        return 14.0, "略低于同行"
    if ratio <= 1.15:
        return 11.0, "接近同行"
    if ratio <= 1.30:
        return 8.0, "略高于同行"
    if ratio <= 1.50:
        return 5.0, "高于同行"
    return 2.0, "明显高于同行"


def calculate_relative_valuation(df, target_code):
    """计算目标公司相对于同行中位数的估值位置。"""
    if df is None or df.empty or "代码" not in df.columns:
        return {
            "available": False,
            "level": "数据不足",
            "score": 10.0,
            "peer_median_pe": None,
            "peer_median_pb": None,
            "target_pe": None,
            "target_pb": None,
            "pe_ratio": None,
            "pb_ratio": None,
        }

    target_rows = df[df["代码"] == target_code]
    if target_rows.empty:
        return {
            "available": False,
            "level": "数据不足",
            "score": 10.0,
            "peer_median_pe": None,
            "peer_median_pb": None,
            "target_pe": None,
            "target_pb": None,
            "pe_ratio": None,
            "pb_ratio": None,
        }

    target = target_rows.iloc[0]
    target_pe = pd.to_numeric(target.get("PE"), errors="coerce")
    target_pb = pd.to_numeric(target.get("PB"), errors="coerce")

    peer_pe = _valid_series(df, "PE", target_code)
    peer_pb = _valid_series(df, "PB", target_code)

    median_pe = float(peer_pe.median()) if not peer_pe.empty else None
    median_pb = float(peer_pb.median()) if not peer_pb.empty else None

    pe_ratio = (
        float(target_pe) / median_pe
        if pd.notna(target_pe) and median_pe and median_pe > 0
        else None
    )
    pb_ratio = (
        float(target_pb) / median_pb
        if pd.notna(target_pb) and median_pb and median_pb > 0
        else None
    )

    pe_score, pe_level = _ratio_score(pe_ratio)
    pb_score, pb_level = _ratio_score(pb_ratio)

    # PE优先，PB作为辅助。缺失时自动重分配权重。
    if pe_score is not None and pb_score is not None:
        score = pe_score * 0.70 + pb_score * 0.30
    elif pe_score is not None:
        score = pe_score
    elif pb_score is not None:
        score = pb_score
    else:
        score = 10.0

    if score >= 16:
        level = "同行明显便宜"
    elif score >= 13:
        level = "同行相对便宜"
    elif score >= 10:
        level = "同行相对合理"
    elif score >= 6:
        level = "同行相对偏贵"
    else:
        level = "同行明显偏贵"

    return {
        "available": pe_score is not None or pb_score is not None,
        "level": level,
        "score": round(score, 1),
        "peer_median_pe": None if median_pe is None else round(median_pe, 2),
        "peer_median_pb": None if median_pb is None else round(median_pb, 2),
        "target_pe": None if pd.isna(target_pe) else round(float(target_pe), 2),
        "target_pb": None if pd.isna(target_pb) else round(float(target_pb), 2),
        "pe_ratio": None if pe_ratio is None else round(pe_ratio, 3),
        "pb_ratio": None if pb_ratio is None else round(pb_ratio, 3),
        "pe_level": pe_level,
        "pb_level": pb_level,
        "peer_count_pe": int(len(peer_pe)),
        "peer_count_pb": int(len(peer_pb)),
    }
