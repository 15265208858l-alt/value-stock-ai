"""
ValueStock AI
同行业比较模块 V2.0
"""

from __future__ import annotations

import pandas as pd
from relative_valuation import calculate_relative_valuation

LAST_RELATIVE_VALUATION = {}


def reset_relative_valuation():
    global LAST_RELATIVE_VALUATION
    LAST_RELATIVE_VALUATION = {}


def get_last_relative_valuation():
    return LAST_RELATIVE_VALUATION.copy()


def safe_rank_score(rank, total, max_score):
    if rank is None:
        return 0
    if total <= 1 or rank == 1:
        return max_score
    if rank == 2:
        return max_score * 0.85
    if rank == 3:
        return max_score * 0.70
    if rank <= max(4, total // 2):
        return max_score * 0.50
    return max_score * 0.25


def calculate_peer_rank(df, column, ascending=False):
    if df is None or df.empty or column not in df.columns:
        return None
    valid = df[["代码", column]].dropna(subset=[column]).copy()
    if valid.empty:
        return None
    valid["_排名"] = valid[column].rank(ascending=ascending, method="min")
    return valid


def calculate_peer_score(df, target_code):
    global LAST_RELATIVE_VALUATION

    if df is None or df.empty or "代码" not in df.columns or target_code not in df["代码"].values:
        reset_relative_valuation()
        return {"score": 0, "rating": "数据不足", "details": [], "relative_valuation": {}}

    target = df[df["代码"] == target_code].iloc[0]
    total_score = 0.0
    details = []

    for column, ascending, max_score in [
        ("ROE", False, 30),
        ("营收增长率", False, 20),
        ("净利润增长率", False, 20),
        ("PE", True, 15),
        ("资产负债率", True, 15),
    ]:
        rank_df = calculate_peer_rank(df, column, ascending=ascending)
        if rank_df is None:
            continue
        row = rank_df[rank_df["代码"] == target_code]
        if row.empty:
            continue
        rank = int(row["_排名"].iloc[0])
        score = safe_rank_score(rank, len(rank_df), max_score)
        total_score += score
        details.append({"指标": column, "排名": rank, "得分": round(score, 1)})

    total_score = round(total_score)
    rating = "优秀" if total_score >= 85 else "良好" if total_score >= 70 else "一般" if total_score >= 55 else "偏弱"

    LAST_RELATIVE_VALUATION = calculate_relative_valuation(df, target_code)

    return {"score": total_score, "rating": rating, "details": details, "relative_valuation": LAST_RELATIVE_VALUATION}


def build_peer_summary(df):
    if df is None or df.empty:
        return pd.DataFrame()
    rows = []
    for column in ["ROE", "营收增长率", "净利润增长率", "资产负债率", "PE", "PB"]:
        if column not in df.columns:
            continue
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            continue
        rows.append({"指标": column, "同行平均": round(float(series.mean()), 2), "同行中位": round(float(series.median()), 2)})
    return pd.DataFrame(rows)


def compare_target_with_average(df, target_code):
    result = []
    if df is None or df.empty or "代码" not in df.columns:
        return result
    target_rows = df[df["代码"] == target_code]
    if target_rows.empty:
        return result
    target = target_rows.iloc[0]

    for metric, direction in [
        ("ROE", "higher_better"),
        ("营收增长率", "higher_better"),
        ("净利润增长率", "higher_better"),
        ("资产负债率", "lower_better"),
        ("PE", "lower_better"),
        ("PB", "lower_better"),
    ]:
        if metric not in df.columns:
            continue
        series = pd.to_numeric(df[metric], errors="coerce").dropna()
        target_value = pd.to_numeric(target.get(metric), errors="coerce")
        if series.empty or pd.isna(target_value):
            continue
        avg = float(series.mean())
        median = float(series.median())
        if direction == "higher_better":
            judgment = "高于同行" if target_value > avg else "低于同行" if target_value < avg else "接近同行"
        else:
            judgment = "优于同行" if target_value < avg else "弱于同行" if target_value > avg else "接近同行"
        result.append({"指标": metric, "目标公司": round(float(target_value), 2), "同行平均": round(avg, 2), "同行中位": round(median, 2), "判断": judgment})
    return result
